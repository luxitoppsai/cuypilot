"""Lectura del catálogo de piezas empaquetado en el wheel."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CATALOG_DIR = Path(__file__).parent / "catalog"

#: Ruta de cada tipo de pieza, relativa a ``catalog/`` y también a ``.github/`` del workspace.
#: Si Copilot cambia sus rutas, este es el único lugar que hay que tocar.
PATHS = {
    "skill": "skills/{name}",
    "agent": "agents/{name}.agent.md",
    "instruction": "instructions/{name}.instructions.md",
}


@dataclass(frozen=True)
class Item:
    """Una pieza del catálogo (skill, agent o instruction).

    :param name: Identificador único de la pieza.
    :param type: ``skill``, ``agent`` o ``instruction``.
    :param version: Versión semántica propia de la pieza.
    :param description: Descripción corta para humanos.
    :param owner: Dueño de la pieza (opcional).
    :param requires: Nombres de otras piezas que se instalan junto con esta.
    """

    name: str
    type: str
    version: str
    description: str
    owner: str = ""
    requires: tuple[str, ...] = ()

    @property
    def relpath(self) -> str:
        """Ruta de la pieza relativa a ``catalog/`` y a ``.github/``."""
        return PATHS[self.type].format(name=self.name)

    def files(self, root: Path = CATALOG_DIR) -> dict[str, bytes]:
        """Devuelve el contenido de la pieza.

        :param root: Carpeta raíz del catálogo.
        :returns: Mapa de ruta relativa (estilo POSIX, relativa a ``root``) a bytes.
        """
        source = root / self.relpath
        paths = sorted(p for p in source.rglob("*") if p.is_file()) if source.is_dir() else [source]
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in paths}


def load_catalog(root: Path = CATALOG_DIR) -> dict[str, Item]:
    """Carga ``catalog.toml``.

    :param root: Carpeta raíz del catálogo.
    :returns: Piezas indexadas por nombre.
    """
    data = tomllib.loads((root / "catalog.toml").read_text(encoding="utf-8"))
    return {
        name: Item(name=name, **{**fields, "requires": tuple(fields.get("requires", ()))})
        for name, fields in data["items"].items()
    }


def resolve(catalog: dict[str, Item], names: list[str]) -> list[Item]:
    """Expande ``names`` con sus dependencias (``requires``), dependencias primero.

    :param catalog: Catálogo cargado.
    :param names: Nombres pedidos por el usuario.
    :returns: Piezas a instalar, sin duplicados.
    :raises KeyError: Si algún nombre no existe en el catálogo.
    """
    ordered: dict[str, Item] = {}

    def visit(name: str) -> None:
        if name in ordered:
            return
        if name not in catalog:
            raise KeyError(name)
        for dep in catalog[name].requires:
            visit(dep)
        ordered[name] = catalog[name]

    for name in names:
        visit(name)
    return list(ordered.values())
