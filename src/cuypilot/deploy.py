"""Despliegue explícito de archivos Genie mediante la CLI oficial de Databricks."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from cuypilot.workspace import CuypilotError, Workspace, _sha, run_command


class GenieDeployment:
    """Sincroniza exclusivamente archivos registrados, conservando contenido ajeno.

    :param workspace: Instalación local del destino Genie.
    :param destination: Carpeta absoluta de Databricks Workspace.
    :param profile: Perfil existente de la CLI, opcional.
    :param run: Ejecutor de comandos, reemplazable en pruebas.
    """

    def __init__(self, workspace: Workspace, destination: str, profile: str | None = None, run=run_command):
        path = PurePosixPath(destination)
        if (
            workspace.target.name != "genie"
            or not destination.startswith("/")
            or path.as_posix() != destination
            or ".." in path.parts
            or "\\" in destination
            or any(ord(c) < 32 for c in destination)
            or len(path.parts) < 3
            or destination in ("/Workspace/Users", "/Workspace/Shared")
        ):
            raise CuypilotError(
                "deploy requiere --target genie y una carpeta absoluta específica del workspace."
            )
        self.workspace = workspace
        self.destination = destination
        self.profile = profile
        self.run = run

    def _command(self, *args):
        return ("databricks", "workspace", *args, *(("--profile", self.profile) if self.profile else ()))

    def _call(self, *args):
        code, output = self.run(self._command(*args), self.workspace.root)
        if code:
            raise CuypilotError(f"Databricks: falló {args[0]} en {args[1]}: {output[-1000:]}")
        return output

    def _fetch(self, relative: str, root: Path) -> bytes | None:
        # Todas las rutas han pasado la validación del lock antes de construir rutas remotas.
        remote = f"{self.destination}/{relative}"
        code, output = self.run(self._command("get-status", remote, "--output", "json"), self.workspace.root)
        if code:
            if "RESOURCE_DOES_NOT_EXIST" in output or output.strip() in (
                f"Error: Path ({remote}) doesn't exist.",
                f"Error: Path ({remote}) doesn't exist",
            ):
                return None
            raise CuypilotError(f"Databricks: no se pudo consultar {remote}: {output[-1000:]}")
        try:
            status = json.loads(output)
        except ValueError as exc:
            raise CuypilotError("Databricks devolvió un estado que no es JSON válido.") from exc
        if not isinstance(status, dict) or status.get("object_type") != "FILE":
            raise CuypilotError(f"El destino remoto no es un archivo: {remote}")
        local = root / relative
        local.parent.mkdir(parents=True, exist_ok=True)
        self._call("export", remote, "--format", "RAW", "--file", str(local))
        return local.read_bytes()

    def deploy(self, dry_run: bool = False, force: bool = False) -> list[str]:
        """Valida cambios locales y remotos, muestra el plan y despliega tras confirmación.

        :param dry_run: Consulta y muestra cambios sin escribir en Databricks.
        :param force: Permite sobrescribir conflictos o ediciones remotas de archivos gestionados.
        :returns: Rutas remotas modificadas.
        :raises CuypilotError: Si hay conflictos, falta autenticación o falla un comando.
        """
        ws = self.workspace
        if any(entry["type"] == "tool" for entry in ws.lock.values()):
            raise CuypilotError("Genie no despliega paquetes de herramientas locales.")
        if ws.managed_hash is not None and ws.managed_hash != ws._block_digest():
            raise CuypilotError("Bloque local modificado; ejecuta update --force antes de desplegar.")
        files = {
            relative: digest for entry in ws.lock.values() for relative, digest in entry["files"].items()
        }
        desired = {}
        for relative, digest in files.items():
            path = ws._safe_path(relative)
            if not path.is_file() or _sha(path.read_bytes()) != digest:
                raise CuypilotError(f"Archivo local modificado o faltante: {relative}")
            desired[relative] = path.read_bytes()
        local_block = None
        if ws.lock:
            text = ws._safe_path(ws.instructions_path).read_text(encoding="utf-8")
            local_block = ws.block_pattern.search(text)
            if local_block is None:
                raise CuypilotError("Falta el bloque local de instrucciones Genie.")

        with TemporaryDirectory(prefix="cuypilot-deploy-") as directory:
            root = Path(directory)
            remote_lock = self._fetch(ws.lock_path, root)
            remote_ws = Workspace(root, ws.catalog, ws.version, ws.catalog_dir, target="genie")
            old_files = {p: h for entry in remote_ws.lock.values() for p, h in entry["files"].items()}
            current = {
                relative: self._fetch(relative, root) for relative in sorted(set(old_files) | set(desired))
            }
            instructions = self._fetch(ws.instructions_path, root)
            text = instructions.decode("utf-8") if instructions is not None else ""
            start, end = ws.start, ws.end
            if (
                text.count(start) != text.count(end)
                or text.count(start) > 1
                or (start in text and text.index(start) > text.index(end))
            ):
                raise CuypilotError("Bloque remoto de instrucciones mal formado.")
            old_block = ws.block_pattern.search(text)
            old_digest = _sha(old_block[0].encode("utf-8")) if old_block else None
            if remote_ws.managed_hash is not None and remote_ws.managed_hash != old_digest and not force:
                raise CuypilotError("Bloque remoto modificado; usa --force para sobrescribirlo.")
            if old_block and remote_lock is None and not force:
                raise CuypilotError("Bloque remoto ajeno sin lockfile; usa --force para adoptarlo.")
            for relative, data in current.items():
                if relative in old_files:
                    conflict = data is None or _sha(data) != old_files[relative]
                else:
                    conflict = data is not None
                if conflict and not force:
                    raise CuypilotError(f"Archivo remoto ajeno o modificado: {relative}; usa --force.")
            replacement = local_block[0] if local_block else ""
            if old_block:
                text = ws.block_pattern.sub(lambda _: replacement, text)
            elif replacement:
                text = text.rstrip("\n") + ("\n\n" if text else "") + replacement + "\n"
            desired[ws.instructions_path] = text.encode("utf-8") if text.strip() else None
            desired.update(dict.fromkeys(set(old_files) - set(files)))
            payload = {
                "cuypilot_version": ws.version,
                "target": "genie",
                "items": ws.lock,
                "managed_hash": _sha(replacement.encode("utf-8")) if replacement else None,
            }
            desired[ws.lock_path] = (
                (json.dumps(payload, indent=2) + "\n").encode("utf-8") if ws.lock else None
            )
            current[ws.instructions_path] = instructions
            current[ws.lock_path] = remote_lock
            # El lock se publica al final: una interrupción queda detectable, nunca se declara completada.
            changed = [p for p in sorted(desired) if desired[p] != current.get(p) and p != ws.lock_path]
            if desired[ws.lock_path] != remote_lock:
                changed.append(ws.lock_path)
            commands = []
            for relative in changed:
                remote = f"{self.destination}/{relative}"
                if desired[relative] is None:
                    commands.append(self._command("delete", remote))
                else:
                    local = root / "upload" / relative
                    local.parent.mkdir(parents=True, exist_ok=True)
                    local.write_bytes(desired[relative])
                    commands.extend(
                        [
                            self._command("mkdirs", str(PurePosixPath(remote).parent)),
                            self._command(
                                "import", remote, "--format", "RAW", "--file", str(local), "--overwrite"
                            ),
                        ]
                    )
            for relative in changed:
                print(
                    f"  {'quitar' if desired[relative] is None else 'publicar'}: "
                    f"{self.destination}/{relative}"
                )
            if dry_run or not commands:
                return changed
            if not ws.confirm(commands):
                raise CuypilotError("Cancelado: no se escribió en Databricks.")
            for command in commands:
                code, output = self.run(command, ws.root)
                if code:
                    raise CuypilotError(
                        f"Despliegue parcial: falló {command[2]}. "
                        f"Revisa y vuelve a desplegar: {output[-1000:]}"
                    )
            print(f"  Registra {self.destination}/.assistant/skills en Settings de Genie Code una vez.")
            return changed
