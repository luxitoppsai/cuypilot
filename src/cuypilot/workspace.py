"""Instalación de piezas del catálogo en el workspace de un proyecto."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from cuypilot.catalog import CATALOG_DIR, Item, resolve

LOCK_PATH = ".github/cuypilot.lock.json"
INSTRUCTIONS_PATH = ".github/copilot-instructions.md"
START, END = "<!-- cuypilot:start -->", "<!-- cuypilot:end -->"
_BLOCK = re.compile(rf"{re.escape(START)}.*?{re.escape(END)}", re.DOTALL)

OK, OUTDATED, MODIFIED, RETIRED = "ok", "desactualizada", "modificada", "retirada"


class CuypilotError(Exception):
    """Error de uso que la CLI muestra al usuario sin traceback."""


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


@dataclass
class Report:
    """Resultado de una operación, para que la CLI lo muestre.

    :param done: Piezas instaladas, actualizadas o quitadas.
    :param skipped: Piezas omitidas, con el motivo.
    """

    done: list[str] = field(default_factory=list)
    skipped: dict[str, str] = field(default_factory=dict)


class Workspace:
    """Workspace consumidor: aplica piezas del catálogo y mantiene el lockfile.

    :param root: Raíz del proyecto (donde vive ``.github/``).
    :param catalog: Catálogo cargado con :func:`cuypilot.catalog.load_catalog`.
    :param version: Versión de cuypilot que se registra en el lockfile.
    :param catalog_dir: Carpeta del catálogo (se cambia en tests).
    """

    def __init__(
        self, root: Path, catalog: dict[str, Item], version: str, catalog_dir: Path = CATALOG_DIR
    ) -> None:
        self.root = root
        self.catalog = catalog
        self.version = version
        self.catalog_dir = catalog_dir
        lock_file = root / LOCK_PATH
        self.lock: dict[str, dict] = (
            json.loads(lock_file.read_text(encoding="utf-8"))["items"] if lock_file.exists() else {}
        )

    # --- operaciones públicas -------------------------------------------------

    def add(self, names: list[str], force: bool = False) -> Report:
        """Instala piezas y sus dependencias.

        :param names: Piezas pedidas.
        :param force: Sobrescribir archivos existentes que no son de cuypilot.
        :returns: Qué se instaló y qué se omitió.
        :raises CuypilotError: Si una pieza no existe o hay archivos ajenos en el destino.
        """
        report = Report()
        new = []
        for item in self._resolve(names):
            if item.name in self.lock:
                report.skipped[item.name] = "ya instalada (usa `cuypilot update`)"
            else:
                new.append(item)
        owned = {path for entry in self.lock.values() for path in entry["files"]}
        conflicts = [
            path
            for item in new
            for path in self._targets(item)
            if (self.root / path).exists() and path not in owned
        ]
        if conflicts and not force:
            raise CuypilotError(
                "Estos archivos ya existen y no son de cuypilot (usa --force para sobrescribir):\n  "
                + "\n  ".join(conflicts)
            )
        for item in new:
            self._install(item)
            report.done.append(item.name)
        self._save()
        return report

    def remove(self, names: list[str]) -> Report:
        """Quita piezas instaladas.

        :param names: Piezas a quitar.
        :returns: Qué se quitó.
        :raises CuypilotError: Si una pieza no está instalada o otra instalada depende de ella.
        """
        missing = [n for n in names if n not in self.lock]
        if missing:
            raise CuypilotError(f"No están instaladas: {', '.join(missing)}")
        remaining = set(self.lock) - set(names)
        for other in sorted(remaining):
            deps = set(self.catalog[other].requires if other in self.catalog else ()) & set(names)
            if deps:
                raise CuypilotError(
                    f"`{other}` depende de {', '.join(sorted(deps))}; quítala también o déjalas."
                )
        report = Report()
        for name in names:
            self._uninstall(name)
            report.done.append(name)
        self._save()
        return report

    def status(self) -> dict[str, str]:
        """Estado de cada pieza instalada.

        :returns: Nombre → ``ok``, ``desactualizada``, ``modificada`` o ``retirada``.
        """
        return {name: self._status(name) for name in sorted(self.lock)}

    def update(self, names: list[str] | None = None, force: bool = False) -> Report:
        """Actualiza piezas instaladas al contenido del wheel actual.

        :param names: Piezas a actualizar; ``None`` = todas las instaladas.
        :param force: Pisar también piezas modificadas localmente.
        :returns: Qué se actualizó y qué se omitió.
        :raises CuypilotError: Si una pieza pedida no está instalada.
        """
        names = sorted(self.lock) if names is None else names
        missing = [n for n in names if n not in self.lock]
        if missing:
            raise CuypilotError(f"No están instaladas: {', '.join(missing)}")
        report = Report()
        for name in names:
            state = self._status(name)
            if state == RETIRED:
                report.skipped[name] = "ya no existe en el catálogo (quítala con `cuypilot remove`)"
            elif state == MODIFIED and not force:
                report.skipped[name] = "modificada localmente (usa --force para pisarla)"
            elif state == OK:
                report.skipped[name] = "ya está al día"
            else:
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
            return resolve(self.catalog, names)
        except KeyError as exc:
            raise CuypilotError(f"No existe en el catálogo: {exc.args[0]}") from None

    def _targets(self, item: Item) -> dict[str, bytes]:
        return {f".github/{rel}": data for rel, data in item.files(self.catalog_dir).items()}

    def _install(self, item: Item) -> None:
        files = self._targets(item)
        for path, data in files.items():
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        self.lock[item.name] = {
            "type": item.type,
            "version": item.version,
            "files": {path: _sha(data) for path, data in files.items()},
        }

    def _uninstall(self, name: str) -> None:
        for path in self.lock.pop(name)["files"]:
            target = self.root / path
            target.unlink(missing_ok=True)
            parent = target.parent
            while parent != self.root / ".github" and parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
                parent = parent.parent

    def _status(self, name: str) -> str:
        entry = self.lock[name]
        for path, digest in entry["files"].items():
            target = self.root / path
            if not target.exists() or _sha(target.read_bytes()) != digest:
                return MODIFIED
        if name not in self.catalog:
            return RETIRED
        current = {path: _sha(data) for path, data in self._targets(self.catalog[name]).items()}
        return OK if current == entry["files"] else OUTDATED

    def _save(self) -> None:
        """Escribe el lockfile y el bloque base; si no queda nada instalado, los limpia."""
        lock_file = self.root / LOCK_PATH
        self._write_block(bool(self.lock))
        if not self.lock:
            lock_file.unlink(missing_ok=True)
            return
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {"cuypilot_version": self.version, "items": dict(sorted(self.lock.items()))}
        lock_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _write_block(self, present: bool) -> None:
        """Escribe, refresca o quita el bloque gestionado; el resto del archivo no se toca."""
        path = self.root / INSTRUCTIONS_PATH
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if present:
            base = (self.catalog_dir / "base" / "copilot-instructions.md").read_text(encoding="utf-8")
            block = f"{START}\n{base.strip()}\n{END}"
            if _BLOCK.search(text):
                text = _BLOCK.sub(lambda _: block, text)
            else:
                if text and not text.endswith("\n"):
                    text += "\n"
                text += ("\n" if text else "") + block + "\n"
        else:
            text = re.sub(rf"\n?{_BLOCK.pattern}\n?", "", text, flags=re.DOTALL)
        if text.strip():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        elif path.exists():
            path.unlink()
