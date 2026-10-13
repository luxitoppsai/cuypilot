"""Instalación de piezas del catálogo en el workspace de un proyecto."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from pathlib import Path

from cuypilot.catalog import CATALOG_DIR, Item, Tool, resolve
from cuypilot.targets import TARGETS

LOCK_PATH = ".github/cuypilot.lock.json"
INSTRUCTIONS_PATH = ".github/copilot-instructions.md"
START, END = "<!-- cuypilot:start -->", "<!-- cuypilot:end -->"
#: El marcador de inicio va en la misma línea que un encabezado H2: otras herramientas (p. ej.
#: graphify) consideran que su sección termina en el siguiente encabezado ``##``; así nunca se
#: llevan el marcador consigo.
HEADING = "## Team conventions (managed by cuypilot — edit outside this block)"

OK, OUTDATED, MODIFIED, RETIRED = "ok", "desactualizada", "modificada", "retirada"
NOT_INSTALLED = "no instalada"

Command = tuple[str, ...]
Runner = Callable[[Command, Path], tuple[int, str]]
Confirm = Callable[[list[Command]], bool]


class CuypilotError(Exception):
    """Error de uso que la CLI muestra al usuario sin traceback."""


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def pip_install(package: str) -> Command:
    """Comando que instala ``package`` en el mismo entorno de Python que ejecuta cuypilot."""
    return (sys.executable, "-m", "pip", "install", package)


def run_command(cmd: Command, cwd: Path) -> tuple[int, str]:
    """Ejecuta un comando del catálogo sin shell.

    El programa se busca primero junto al Python actual y después en ``PATH``
    (así funciona aunque el entorno virtual no esté activado).

    :param cmd: Programa y argumentos.
    :param cwd: Directorio de trabajo.
    :returns: Código de salida y salida combinada (stdout + stderr).
    """
    program = shutil.which(cmd[0], path=str(Path(sys.executable).parent)) or shutil.which(cmd[0])
    if program is None:
        return 127, f"comando no encontrado: {cmd[0]}"
    result = subprocess.run([program, *cmd[1:]], cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


@dataclass
class Report:
    """Resultado de una operación, para que la CLI lo muestre.

    :param done: Piezas instaladas, actualizadas o quitadas.
    :param skipped: Piezas omitidas, con el motivo.
    :param notes: Avisos para el usuario.
    """

    done: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _transactional(method):
    """Restaura archivos gestionados si una operación falla."""

    @wraps(method)
    def wrapped(self, *args, **kwargs):
        names = args[0] if args else kwargs.get("names")
        names = list(self.lock) if names is None else names
        items = (
            []
            if method.__name__ == "remove"
            else self._resolve([name for name in names if name in self.catalog])
        )
        with self._transaction(items, force=kwargs.get("force", args[1] if len(args) > 1 else False)):
            return method(self, *args, **kwargs)

    return wrapped


class Workspace:
    """Workspace consumidor: aplica piezas del catálogo y mantiene el lockfile.

    :param root: Raíz del proyecto (donde vive ``.github/``).
    :param catalog: Catálogo cargado con :func:`cuypilot.catalog.load_catalog`.
    :param version: Versión de cuypilot que se registra en el lockfile.
    :param catalog_dir: Carpeta del catálogo (se cambia en tests).
    :param run: Ejecuta comandos de herramientas (se cambia en tests).
    :param confirm: Pide permiso antes de ejecutar comandos; por defecto, lo niega.
    :param target: Asistente destino (copilot, opencode o genie).
    """

    def __init__(
        self,
        root: Path,
        catalog: dict[str, Item],
        version: str,
        catalog_dir: Path = CATALOG_DIR,
        run: Runner = run_command,
        confirm: Confirm = lambda commands: False,
        target: str = "copilot",
    ) -> None:
        if target not in TARGETS:
            raise CuypilotError(f"Destino desconocido: {target}")
        self.target = TARGETS[target]
        self.lock_path = self.target.lock_path
        self.instructions_path = self.target.instructions_path
        self.start, self.end = self.target.markers
        self.block_pattern = re.compile(
            rf"(?:^##[^\n]*?)?{re.escape(self.start)}.*?{re.escape(self.end)}", re.DOTALL | re.MULTILINE
        )
        self.root = root.resolve()
        self.catalog = catalog
        self.version = version
        self.catalog_dir = catalog_dir
        self.run = run
        self.confirm = confirm
        lock_file = self._safe_path(self.lock_path)
        self.lock: dict[str, dict] = {}
        self.managed_hash: str | None = None
        if lock_file.exists():
            try:
                payload = json.loads(lock_file.read_text(encoding="utf-8"))
            except (ValueError, UnicodeError) as exc:
                raise CuypilotError(f"Lockfile inválido: {exc}") from exc
            self.lock = self._validate_lock(payload)
            digest = payload.get("managed_hash")
            if digest is not None and (
                not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
            ):
                raise CuypilotError("Lockfile inválido: hash del bloque gestionado.")
            self.managed_hash = digest

    def _safe_path(self, relative: str) -> Path:
        """Rechaza rutas externas y enlaces en cualquier componente del destino."""
        path = Path(relative)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in relative
            or path.as_posix() != relative
            or any(ord(char) < 32 for char in relative)
        ):
            raise CuypilotError(f"Ruta no permitida: {relative}")
        target = self.root
        for part in path.parts:
            if target.exists() and not target.is_dir():
                raise CuypilotError(f"Directorio inválido en ruta: {relative}")
            target = target / part
            if target.is_symlink():
                raise CuypilotError(f"Enlace simbólico no permitido: {relative}")
        return target

    def _validate_lock(self, payload: object) -> dict[str, dict]:
        """Valida el formato y la propiedad de cada archivo registrado."""
        if not isinstance(payload, dict) or not isinstance(payload.get("cuypilot_version"), str):
            raise CuypilotError("Lockfile inválido: falta cuypilot_version.")
        if payload.get("target", "copilot") != self.target.name:
            raise CuypilotError("Lockfile inválido: pertenece a otro destino.")
        items = payload.get("items")
        if not isinstance(items, dict):
            raise CuypilotError("Lockfile inválido: items debe ser un objeto.")
        for name, entry in items.items():
            if not re.fullmatch(r"[a-z0-9-]{1,64}", name) or not isinstance(entry, dict):
                raise CuypilotError("Lockfile inválido: pieza mal formada.")
            kind = entry.get("type")
            if kind not in ("skill", "agent", "instruction", "tool"):
                raise CuypilotError(f"Lockfile inválido: tipo de {name}.")
            if not isinstance(entry.get("version"), str) or not re.fullmatch(
                r"\d+\.\d+\.\d+", entry["version"]
            ):
                raise CuypilotError(f"Lockfile inválido: versión de {name}.")
            if name in self.catalog and kind != self.catalog[name].type:
                raise CuypilotError(f"Lockfile inválido: tipo incompatible de {name}.")
            files = entry.get("files")
            if not isinstance(files, dict) or (kind == "tool" and files):
                raise CuypilotError(f"Lockfile inválido: archivos de {name}.")
            integration_hash = entry.get("integration_hash")
            if integration_hash is not None and (
                not isinstance(integration_hash, str)
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", integration_hash)
            ):
                raise CuypilotError(f"Lockfile inválido: hash de integración de {name}.")
            requires = entry.get("requires", [])
            if not isinstance(requires, list) or not all(
                isinstance(dep, str) and re.fullmatch(r"[a-z0-9-]{1,64}", dep) for dep in requires
            ):
                raise CuypilotError(f"Lockfile inválido: dependencias de {name}.")
            if kind != "tool" and not files:
                raise CuypilotError(f"Lockfile inválido: archivos vacíos de {name}.")
            for relative, digest in files.items():
                target = self._safe_path(relative)
                owned = self.target.owns(name, kind, relative)
                if (
                    not owned
                    or not isinstance(digest, str)
                    or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest)
                ):
                    raise CuypilotError(f"Lockfile inválido: archivo de {name}: {relative}")
                if target.exists() and not target.is_file():
                    raise CuypilotError(f"Destino no es archivo: {relative}")
        return items

    @contextmanager
    def _transaction(self, items, force=False):
        relatives = {self.lock_path, self.instructions_path, ".gitignore"}
        relatives.update(path for entry in self.lock.values() for path in entry["files"])
        relatives.update(path for item in items for path in self._targets(item))
        paths = [self._safe_path(path) for path in sorted(relatives)]
        snapshot = {}
        absent_dirs = set()
        for path in paths:
            if path.exists() and not path.is_file():
                raise CuypilotError(f"Destino no es archivo: {path.relative_to(self.root)}")
            if path == self.root / self.instructions_path and path.exists():
                text = path.read_text(encoding="utf-8")
                if text.count(self.start) != text.count(self.end) or text.count(self.start) > 1:
                    raise CuypilotError("Bloque gestionado inválido: revisa los marcadores de cuypilot.")
                if self.start in text and text.index(self.start) > text.index(self.end):
                    raise CuypilotError("Bloque gestionado inválido: marcadores invertidos.")
            snapshot[path] = (path.read_bytes(), path.stat().st_mode) if path.exists() else None
            for parent in path.parents:
                if parent == self.root:
                    break
                if not parent.exists():
                    absent_dirs.add(parent)
        if self.managed_hash is not None and self.managed_hash != self._block_digest() and not force:
            raise CuypilotError(
                "Bloque gestionado modificado localmente; usa update --force para restaurarlo."
            )
        old_hash = self.managed_hash
        old_lock = copy.deepcopy(self.lock)
        try:
            yield
        except (OSError, CuypilotError, KeyboardInterrupt):
            self.lock = old_lock
            self.managed_hash = old_hash
            for path, saved in snapshot.items():
                self._safe_path(path.relative_to(self.root).as_posix())
                if saved is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(saved[0])
                    path.chmod(saved[1])
            for directory in sorted(absent_dirs, key=lambda p: len(p.parts), reverse=True):
                if directory.exists() and not any(directory.iterdir()):
                    directory.rmdir()
            raise

    # --- operaciones públicas -------------------------------------------------

    def plan_add(self, names: list[str]) -> tuple[list[Item], list[Command]]:
        """Calcula qué haría :meth:`add`, sin cambiar nada.

        :param names: Piezas pedidas.
        :returns: Piezas nuevas a instalar y comandos de herramientas a ejecutar.
        :raises CuypilotError: Si una pieza no existe.
        """
        new = [item for item in self._resolve(names) if item.name not in self.lock]
        commands = [cmd for item in new if isinstance(item, Tool) for cmd in self._tool_commands(item)]
        return new, commands

    @_transactional
    def add(self, names: list[str], force: bool = False) -> Report:
        """Instala piezas y sus dependencias; las herramientas, con confirmación.

        :param names: Piezas pedidas.
        :param force: Sobrescribir archivos existentes que no son de cuypilot.
        :returns: Qué se instaló y qué se omitió.
        :raises CuypilotError: Si una pieza no existe, hay archivos ajenos en el destino, el usuario
            cancela o falla un comando.
        """
        new, commands = self.plan_add(names)
        installed = [i.name for i in self._resolve(names) if i.name in self.lock]
        report = Report(skipped=dict.fromkeys(installed, "ya instalada (usa `cuypilot update`)"))
        owned = {path for entry in self.lock.values() for path in entry["files"]}
        conflicts = [
            path
            for item in new
            for path in self._targets(item)
            if self._safe_path(path).exists() and path not in owned
        ]
        if conflicts and not force:
            raise CuypilotError(
                "Estos archivos ya existen y no son de cuypilot (usa --force para sobrescribir):\n  "
                + "\n  ".join(conflicts)
            )
        self._execute(commands)
        for item in new:
            self._install(item)
            report.done.append(item.name)
        self._save()
        return report

    @_transactional
    def remove(self, names: list[str], force: bool = False) -> Report:
        """Quita piezas instaladas.

        :param names: Piezas a quitar.
        :param force: Eliminar también archivos modificados localmente.
        :returns: Qué se quitó.
        :raises CuypilotError: Si una pieza no está instalada o otra instalada depende de ella.
        """
        names = list(dict.fromkeys(names))
        missing = [n for n in names if n not in self.lock]
        if missing:
            raise CuypilotError(f"No están instaladas: {', '.join(missing)}")
        modified = [
            path
            for name in names
            for path, digest in self.lock[name]["files"].items()
            if self._safe_path(path).exists() and _sha(self._safe_path(path).read_bytes()) != digest
        ]
        if modified and not force:
            raise CuypilotError(
                "Archivos modificados localmente; revisa antes de eliminar con --force: "
                + ", ".join(modified)
            )
        remaining = set(self.lock) - set(names)
        for other in sorted(remaining):
            recorded = self.lock[other].get("requires")
            requires = (
                recorded
                if recorded is not None
                else (self.catalog[other].requires if other in self.catalog else ())
            )
            deps = set(requires) & set(names)
            if deps:
                raise CuypilotError(
                    f"`{other}` depende de {', '.join(sorted(deps))}; quítala también o déjalas."
                )
        tools = [self.catalog[n] for n in names if isinstance(self.catalog.get(n), Tool)]
        self._execute([cmd for tool in tools for cmd in tool.disconnection(self.target.name)])
        report = Report()
        for name in names:
            self._uninstall(name)
            report.done.append(name)
        for tool in tools:
            report.notes.append(
                f"{tool.name}: se quitó del proyecto; el programa `{tool.check[0]}` sigue instalado."
            )
        self._save()
        return report

    def status(self) -> dict[str, str]:
        """Estado de cada pieza instalada.

        :returns: Nombre → ``ok``, ``desactualizada``, ``modificada``, ``retirada`` o ``no instalada``.
        """
        return {name: self._status(name) for name in sorted(self.lock)}

    @_transactional
    def update(self, names: list[str] | None = None, force: bool = False) -> Report:
        """Actualiza piezas instaladas al contenido del wheel actual.

        :param names: Piezas a actualizar; ``None`` = todas las instaladas.
        :param force: Pisar también piezas modificadas localmente.
        :returns: Qué se actualizó y qué se omitió.
        :raises CuypilotError: Si una pieza pedida no está instalada.
        """
        names = sorted(self.lock) if names is None else names
        names = list(dict.fromkeys(names))
        missing = [n for n in names if n not in self.lock]
        if missing:
            raise CuypilotError(f"No están instaladas: {', '.join(missing)}")
        report = Report()
        pending = []
        for name in names:
            state = self._status(name)
            if state == RETIRED:
                report.skipped[name] = "ya no existe en el catálogo (quítala con `cuypilot remove`)"
            elif state == MODIFIED and not force:
                report.skipped[name] = "modificada localmente (usa --force para pisarla)"
            elif state == OK:
                report.skipped[name] = "ya está al día"
            else:
                pending.append(name)
        additions = {
            item.name: item
            for name in pending
            for item in self._resolve([name])
            if item.name not in self.lock
        }
        owned = {path for entry in self.lock.values() for path in entry["files"]}
        conflicts = [
            path
            for item in [*(self.catalog[name] for name in pending), *additions.values()]
            for path in self._targets(item)
            if self._safe_path(path).exists() and path not in owned
        ]
        if conflicts and not force:
            raise CuypilotError(
                "Archivos ajenos en piezas actualizadas o dependencias nuevas (usa --force): "
                + ", ".join(conflicts)
            )
        tools = [
            item
            for item in {**{n: self.catalog[n] for n in pending}, **additions}.values()
            if isinstance(item, Tool)
        ]
        self._execute([cmd for tool in tools for cmd in self._tool_commands(tool)])
        for name in pending:
            self._uninstall(name)
            for item in self._resolve([name]):  # incluye requires nuevos
                if item.name not in self.lock:
                    self._install(item)
                    report.done.append(item.name)
        self._save()
        return report

    # --- internos -------------------------------------------------------------

    def _resolve(self, names: list[str]) -> list[Item]:
        try:
            items = resolve(self.catalog, names)
        except KeyError as exc:
            raise CuypilotError(f"No existe en el catálogo: {exc.args[0]}") from None
        incompatible = [item.name for item in items if not self.target.supports(item)]
        if incompatible:
            raise CuypilotError(f"No compatible con {self.target.label}: {', '.join(incompatible)}")
        return items

    def _targets(self, item: Item) -> dict[str, bytes]:
        return self.target.render(item, self.catalog_dir)

    def _tool_version(self, tool: Tool) -> str | None:
        """Versión instalada de la herramienta, según su comando ``check``."""
        code, out = self.run(tool.check, self.root)
        match = re.search(r"\d+\.\d+\.\d+", out) if code == 0 else None
        return match.group(0) if match else None

    def _integration_digest(self, tool: Tool) -> str:
        configuration = {
            "configure": tool.configuration(self.target.name),
            "uninstall": tool.disconnection(self.target.name),
            "instructions": tool.instructions,
            "gitignore": tool.gitignore,
            "requires": tool.requires,
        }
        return _sha(json.dumps(configuration, sort_keys=True).encode("utf-8"))

    def _tool_commands(self, tool: Tool) -> list[Command]:
        install = [] if self._tool_version(tool) == tool.version else [pip_install(tool.package)]
        return install + list(tool.configuration(self.target.name))

    def _execute(self, commands: list[Command]) -> None:
        """Pide confirmación y ejecuta los comandos en orden; se detiene en el primero que falle."""
        if not commands:
            return
        if not self.confirm(commands):
            raise CuypilotError("Cancelado: no se ejecutó ningún comando ni se cambió nada.")
        for cmd in commands:
            code, out = self.run(cmd, self.root)
            if code != 0:
                raise CuypilotError(f"Falló `{' '.join(cmd)}` (código {code}):\n{out.strip()[-2000:]}")

    def _add_gitignore(self, lines: tuple[str, ...]) -> None:
        path = self._safe_path(".gitignore")
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        missing = [line for line in lines if line not in text.splitlines()]
        if missing:
            prefix = "\n" if text and not text.endswith("\n") else ""
            path.write_text(text + prefix + "\n".join(missing) + "\n", encoding="utf-8")

    def _install(self, item: Item) -> None:
        if isinstance(item, Tool):
            self._add_gitignore(item.gitignore)
        files = self._targets(item)
        for path, data in files.items():
            target = self._safe_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.lock[item.name] = {
            "type": item.type,
            "version": item.version,
            "files": {path: _sha(data) for path, data in files.items()},
            "requires": list(item.requires),
        }

        if isinstance(item, Tool):
            self.lock[item.name]["integration_hash"] = self._integration_digest(item)

    def _uninstall(self, name: str) -> None:
        for path in self.lock.pop(name)["files"]:
            target = self._safe_path(path)
            target.unlink(missing_ok=True)
            parent = target.parent
            while (
                parent != self.root / self.target.directory and parent.exists() and not any(parent.iterdir())
            ):
                parent.rmdir()
                parent = parent.parent

    def _block_digest(self) -> str | None:
        path = self._safe_path(self.instructions_path)
        match = self.block_pattern.search(path.read_text(encoding="utf-8")) if path.exists() else None
        return _sha(match[0].encode("utf-8")) if match else None

    def _status(self, name: str) -> str:
        if self.managed_hash is not None and self.managed_hash != self._block_digest():
            return MODIFIED
        entry = self.lock[name]
        if entry["type"] == "tool":
            if name not in self.catalog:
                return RETIRED
            installed = self._tool_version(self.catalog[name])
            if installed is None:
                return NOT_INSTALLED
            tool = self.catalog[name]
            return (
                OK
                if (
                    installed == entry["version"] == tool.version
                    and entry.get("integration_hash") == self._integration_digest(tool)
                )
                else OUTDATED
            )
        for path, digest in entry["files"].items():
            target = self._safe_path(path)
            if not target.exists() or _sha(target.read_bytes()) != digest:
                return MODIFIED
        if name not in self.catalog:
            return RETIRED
        current = {path: _sha(data) for path, data in self._targets(self.catalog[name]).items()}
        return (
            OK
            if (
                current == entry["files"]
                and entry["version"] == self.catalog[name].version
                and tuple(entry.get("requires", self.catalog[name].requires)) == self.catalog[name].requires
            )
            else OUTDATED
        )

    def _save(self) -> None:
        """Escribe el lockfile y el bloque base; si no queda nada instalado, los limpia."""
        lock_file = self._safe_path(self.lock_path)
        self._write_block(bool(self.lock))
        self.managed_hash = self._block_digest()
        if not self.lock:
            lock_file.unlink(missing_ok=True)
            return
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cuypilot_version": self.version,
            "target": self.target.name,
            "managed_hash": self.managed_hash,
            "items": dict(sorted(self.lock.items())),
        }
        lock_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _write_block(self, present: bool) -> None:
        """Escribe, refresca o quita el bloque gestionado; el resto del archivo no se toca."""
        path = self._safe_path(self.instructions_path)
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if present:
            base = (self.catalog_dir / "base" / "copilot-instructions.md").read_text(encoding="utf-8")
            rules = [
                item.instructions.strip()
                for name in sorted(self.lock)
                if isinstance(item := self.catalog.get(name), Tool) and item.instructions
            ]
            if self.target.name != "copilot":
                for _name, entry in sorted(self.lock.items()):
                    if entry["type"] == "instruction":
                        for relative in entry["files"]:
                            rules.append(self._safe_path(relative).read_text(encoding="utf-8").strip())
            body = "\n\n".join([base.strip(), *rules])
            block = f"{HEADING} {self.start}\n{body}\n{self.end}"
            if self.block_pattern.search(text):
                text = self.block_pattern.sub(lambda _: block, text)
            else:
                if text and not text.endswith("\n"):
                    text += "\n"
                text += ("\n" if text else "") + block + "\n"
        else:
            text = re.sub(rf"\n?{self.block_pattern.pattern}\n?", "", text, flags=re.DOTALL | re.MULTILINE)
        if text.strip():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        elif path.exists():
            path.unlink()
