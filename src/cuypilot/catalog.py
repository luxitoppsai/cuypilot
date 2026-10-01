"""Lectura del catálogo de piezas empaquetado en el wheel."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
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
    :param upstream: Origen de una pieza de terceros (``repo``, ``ref``, ``path``, ``license``, ``adapted``).
    """

    name: str
    type: str
    version: str
    description: str
    owner: str = ""
    requires: tuple[str, ...] = ()
    upstream: dict | None = field(default=None, compare=False)

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
        if source.is_dir():
            # pip compila bytecode al instalar: __pycache__ nunca se copia al repo del usuario.
            paths = sorted(p for p in source.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        else:
            paths = [source]
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in paths}


@dataclass(frozen=True)
class Tool(Item):
    """Herramienta externa que se instala con su instalador oficial (RFC-002 §4.3).

    Los comandos son listas de argumentos: se ejecutan sin shell.

    :param license: Licencia de la herramienta.
    :param package: Paquete de PyPI fijado a la versión aprobada (``nombre==versión``); se instala con pip.
    :param configure: Comandos que la conectan al workspace.
    :param uninstall: Comandos que la desconectan del workspace.
    :param check: Comando cuya salida contiene la versión instalada.
    :param gitignore: Líneas a agregar a ``.gitignore``.
    :param instructions: Regla que se agrega al bloque gestionado mientras esté instalada.
    """

    license: str = ""
    package: str = ""
    configure: tuple[tuple[str, ...], ...] = ()
    uninstall: tuple[tuple[str, ...], ...] = ()
    check: tuple[str, ...] = ()
    gitignore: tuple[str, ...] = ()
    instructions: str = ""

    def files(self, root: Path = CATALOG_DIR) -> dict[str, bytes]:
        """Una herramienta no copia archivos: los gestiona su propio instalador."""
        return {}


def _freeze(value):
    """Convierte listas (anidadas) de TOML en tuplas, para dataclasses inmutables."""
    return tuple(_freeze(v) for v in value) if isinstance(value, list) else value


def load_catalog(root: Path = CATALOG_DIR) -> dict[str, Item]:
    """Carga ``catalog.toml``.

    :param root: Carpeta raíz del catálogo.
    :returns: Piezas indexadas por nombre.
    """
    data = tomllib.loads((root / "catalog.toml").read_text(encoding="utf-8"))
    return {
        name: (Tool if fields["type"] == "tool" else Item)(
            name=name, **{key: _freeze(value) for key, value in fields.items()}
        )
        for name, fields in data["items"].items()
    }


def load_roles(root: Path = CATALOG_DIR) -> dict[str, dict]:
    """Carga las combinaciones sugeridas por rol (``[roles]`` de ``catalog.toml``).

    :param root: Carpeta raíz del catálogo.
    :returns: Rol → ``{"label": str, "items": list[str]}``.
    """
    return tomllib.loads((root / "catalog.toml").read_text(encoding="utf-8")).get("roles", {})


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
