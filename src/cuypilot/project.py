"""Operaciones declarativas y transacciones locales entre destinos del consumidor."""

from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import replace

from cuypilot.catalog import Tool
from cuypilot.manifest import MANIFEST, Manifest
from cuypilot.targets import TARGETS
from cuypilot.workspace import OK, OUTDATED, CuypilotError, Workspace, _sha


def detect_targets(root) -> list[str]:
    """Detecta locks o carpetas de asistentes; una .github genérica no basta."""
    return [
        name
        for name, target in TARGETS.items()
        if (root / target.lock_path).exists()
        or (root / target.directory).is_symlink()
        or (name != "copilot" and (root / target.directory).is_dir())
        or (
            name == "copilot"
            and (root / target.instructions_path).is_file()
            and target.markers[0].encode() in (root / target.instructions_path).read_bytes()
        )
    ]


class Project:
    """Coordina el manifiesto y los workspaces sin duplicar el motor de instalación.

    :param workspace: Workspace con catálogo, versión y ejecutores del entorno actual.
    :param target: Destino explícito de la CLI, si lo hay.
    """

    def __init__(self, workspace: Workspace, target: str | None = None):
        self.ws = workspace
        self.path = workspace._safe_path(MANIFEST)
        self.manifest = Manifest.read(self.path, workspace.version) if self.path.exists() else None
        declared = self.manifest.targets if self.manifest else ()
        if target and declared and target not in declared:
            raise CuypilotError(f"{target} no figura en targets del manifiesto.")
        self.targets = (
            list(declared) or ([target] if target else detect_targets(workspace.root)) or ["copilot"]
        )
        # Un destino retirado del manifiesto sigue teniendo archivos gestionados que reconciliar.
        installed = [
            name
            for name, destination in TARGETS.items()
            if self.manifest
            and (workspace.root / destination.lock_path).exists()
            and name not in self.targets
        ]
        self.workspaces = {
            name: workspace
            if workspace.target.name == name
            else Workspace(
                workspace.root,
                workspace.catalog,
                workspace.version,
                workspace.catalog_dir,
                run=workspace.run,
                confirm=workspace.confirm,
                target=name,
            )
            for name in [*self.targets, *installed]
        }

    def migrate(self) -> Manifest:
        """Deduce un manifiesto solo si los destinos instalados comparten selección."""
        selections = [set(ws.lock) for ws in self.workspaces.values()]
        if any(selection != selections[0] for selection in selections):
            raise CuypilotError(
                "Los destinos tienen selecciones diferentes; escribe cuypilot.toml explícitamente."
            )
        names = sorted(selections[0])
        kinds = next(iter(self.workspaces.values())).lock
        major, minor, _patch = self.ws.version.split(".")
        return Manifest(
            f">={major}.{minor},<{major}.{int(minor) + 1}",
            tuple(self.targets),
            tuple(name for name in names if kinds[name]["type"] != "tool"),
            tuple(name for name in names if kinds[name]["type"] == "tool"),
        )

    def desired(self, manifest: Manifest) -> dict[str, list]:
        """Valida nombres, tipos, dependencias y compatibilidad antes de mutar."""
        for name in manifest.names:
            item = self.ws.catalog.get(name)
            if item is None:
                raise CuypilotError(f"No existe en el catálogo: {name}")
            if isinstance(item, Tool) != (name in manifest.tools):
                raise CuypilotError(f"Tipo incorrecto en el manifiesto: {name}")
        return {
            name: ws._resolve(list(manifest.names)) if name in self.targets else []
            for name, ws in self.workspaces.items()
        }

    @contextmanager
    def transaction(self, desired, force=False):
        """Respalda todos los destinos y el manifiesto antes de la primera escritura."""
        with ExitStack() as stack:
            for name, ws in self.workspaces.items():
                stack.enter_context(ws._transaction(desired[name], force=force, extra_paths=(MANIFEST,)))
            yield

    def install(self, manifest: Manifest | None = None, force: bool = False) -> dict:
        """Reconcilia la selección exacta; revierte archivos locales ante errores."""
        manifest = manifest or self.manifest or self.migrate()
        desired = self.desired(manifest)
        reports = {}
        with self.transaction(desired, force):
            # Prevalidar todos los destinos antes de ejecutar comandos de herramientas.
            for name, ws in self.workspaces.items():
                required = {item.name for item in desired[name]}
                ws.plan_update(sorted(set(ws.lock) & required), force=force)
                for installed in ws.lock:
                    if ws._status(installed) == "modificada" and not force:
                        raise CuypilotError(f"{name}: {installed} modificada; revisa antes de usar --force.")
                for item in desired[name]:
                    if item.name not in ws.lock:
                        for relative in ws._targets(item):
                            if ws._safe_path(relative).exists() and not force:
                                raise CuypilotError(f"Archivo ajeno: {relative}; usa --force para adoptarlo.")
            for name, ws in self.workspaces.items():
                required = {item.name for item in desired[name]}
                extra = sorted(set(ws.lock) - required)
                # Actualizar dependencias registradas antes de retirar las que ya no se requieren.
                report = ws.update(sorted(set(ws.lock) & required), force=force)
                added = ws.add(list(manifest.names) if name in self.targets else [], force=force)
                report.done.extend(added.done)
                report.notes.extend(added.notes)
                if extra:
                    removed = ws.remove(extra, force=force)
                    report.notes.extend(f"Retirada: {piece}" for piece in removed.done)
                    report.notes.extend(removed.notes)
                reports[name] = report
            manifest = replace(manifest, targets=tuple(self.targets))
            manifest.write(self.path)
        self.manifest = manifest
        return reports

    def change(self, names: list[str], remove=False, force=False) -> dict:
        """Edita la selección común y reconcilia todos los destinos declarados."""
        return self.install(self.changed_manifest(names, remove), force)

    def changed_manifest(self, names: list[str], remove=False) -> Manifest:
        """Calcula la nueva intención sin escribir; compartido por aplicación y dry-run."""
        if self.manifest is None:
            raise CuypilotError("Esta operación declarativa requiere cuypilot.toml.")
        selected = set(self.manifest.names)
        if remove:
            absent = set(names) - selected
            if absent:
                raise CuypilotError(f"No están declaradas explícitamente: {', '.join(sorted(absent))}")
            selected.difference_update(names)
        else:
            selected.update(names)
        for name in selected:
            if name not in self.ws.catalog:
                raise CuypilotError(f"No existe en el catálogo: {name}")
        manifest = replace(
            self.manifest,
            pieces=tuple(sorted(name for name in selected if not isinstance(self.ws.catalog[name], Tool))),
            tools=tuple(sorted(name for name in selected if isinstance(self.ws.catalog[name], Tool))),
        )
        if remove:
            desired = self.desired(manifest)
            still_required = set(names) & {item.name for items in desired.values() for item in items}
            if still_required:
                raise CuypilotError(f"Otras piezas dependen de {', '.join(sorted(still_required))}.")
        return manifest

    def differences(self, frozen: bool = False) -> list[str]:
        """Lista inconsistencias de archivos, bloques, dependencias y manifiesto; no escribe."""
        if frozen and self.manifest is None:
            return ["Falta cuypilot.toml; ejecuta install para migrar primero."]
        desired = self.desired(self.manifest) if self.manifest else None
        differences = []
        for target, ws in self.workspaces.items():
            prefix = f"{target}: "
            if self.manifest and target not in self.targets and ws._safe_path(ws.lock_path).exists():
                differences.append(prefix + "destino instalado no declarado")
            if desired is not None:
                expected = {item.name for item in desired[target]}
                for name in sorted(expected - set(ws.lock)):
                    differences.append(prefix + f"falta pieza {name}")
                for name in sorted(set(ws.lock) - expected):
                    differences.append(prefix + f"pieza no declarada {name}")
            for name, entry in ws.lock.items():
                item = ws.catalog.get(name)
                for relative, digest in entry["files"].items():
                    path = ws._safe_path(relative)
                    if not path.is_file() or _sha(path.read_bytes()) != digest:
                        differences.append(prefix + f"archivo modificado o faltante {relative}")
                for dep in entry.get("requires", item.requires if item else ()):
                    if dep not in ws.lock:
                        differences.append(prefix + f"{name} requiere {dep}, que falta")
                if item is not None:
                    files = ws._targets(item)
                    recorded = set(entry["files"])
                    # Solo el directorio de esta pieza; archivos ajenos fuera de él se conservan.
                    if item.type == "skill" or (item.type == "agent" and target == "genie"):
                        directory = ws._safe_path(f"{ws.target.directory}/skills/{name}")
                        for path in directory.rglob("*"):
                            relative = path.relative_to(ws.root).as_posix()
                            if path.is_symlink():
                                ws._safe_path(relative)
                            if (
                                path.is_file()
                                and relative not in recorded
                                and "__pycache__" not in path.parts
                            ):
                                differences.append(prefix + f"archivo no registrado {relative}")
                    if frozen:
                        expected_files = {p: _sha(data) for p, data in files.items()}
                        if (
                            entry["version"] != item.version
                            or expected_files != entry["files"]
                            or tuple(entry.get("requires", ())) != item.requires
                            or (
                                isinstance(item, Tool)
                                and entry.get("integration_hash") != ws._integration_digest(item)
                            )
                        ):
                            differences.append(prefix + f"{name} no coincide con el wheel actual")
                elif frozen:
                    differences.append(prefix + f"pieza retirada del catálogo: {name}")
            path = ws._safe_path(ws.instructions_path)
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            if (
                text.count(ws.start) != text.count(ws.end)
                or text.count(ws.start) > 1
                or (ws.start in text and text.index(ws.start) > text.index(ws.end))
            ):
                differences.append(prefix + "marcadores del bloque compartido inválidos")
            if not ws.lock and ws.start in text:
                differences.append(prefix + "bloque compartido sin lockfile")
            try:
                block = ws.block_status()
            except (OSError, UnicodeError) as exc:
                differences.append(prefix + f"no se puede comprobar el bloque compartido: {exc}")
                continue
            if block != OK and (frozen or block != OUTDATED):
                differences.append(prefix + f"bloque compartido {block}")
            elif ws.lock and ws._block_digest() is None:
                differences.append(prefix + "falta bloque compartido")
        return differences
