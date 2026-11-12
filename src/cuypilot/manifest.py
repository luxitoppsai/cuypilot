"""Manifiesto declarativo del consumidor (RFC-008), sin dependencias de runtime."""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from cuypilot.targets import TARGETS
from cuypilot.workspace import CuypilotError

MANIFEST = "cuypilot.toml"
NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
BOUND = re.compile(r"(>=|<=|==|!=|>|<)\s*(\d+(?:\.\d+){0,2})")


def check_version(requirement: str, version: str) -> None:
    """Valida comparadores numéricos y exige que el wheel satisfaga todos.

    :raises CuypilotError: Si el rango es inválido o el wheel no lo cumple.
    """
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise CuypilotError(f"Versión del wheel no soportada por el manifiesto: {version}")
    current = tuple(map(int, version.split(".")))
    for term in requirement.split(","):
        match = BOUND.fullmatch(term.strip())
        if match is None:
            raise CuypilotError(f"Restricción cuypilot inválida: {requirement}")
        op, value = match.groups()
        parts = tuple(map(int, value.split(".")))
        bound = (*parts, *((0,) * (3 - len(parts))))
        matches = {
            ">=": current >= bound,
            "<=": current <= bound,
            ">": current > bound,
            "<": current < bound,
            "==": current == bound,
            "!=": current != bound,
        }
        if not matches[op]:
            raise CuypilotError(f"Wheel {version} fuera de la restricción cuypilot {requirement}.")


@dataclass(frozen=True)
class Manifest:
    """Selección común de piezas y herramientas para los destinos del proyecto."""

    cuypilot: str
    targets: tuple[str, ...] = ()
    pieces: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()

    @property
    def names(self) -> tuple[str, ...]:
        """Selección explícita, antes de expandir dependencias."""
        return self.pieces + self.tools

    @classmethod
    def read(cls, path: Path, version: str) -> Manifest:
        """Lee, valida el esquema y comprueba la restricción del wheel."""
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise CuypilotError(f"Manifiesto inválido: {exc}") from exc
        if set(data) - {"cuypilot", "targets", "pieces", "tools"}:
            raise CuypilotError("Manifiesto inválido: claves desconocidas.")
        requirement = data.get("cuypilot")
        if not isinstance(requirement, str):
            raise CuypilotError("Manifiesto inválido: cuypilot debe ser una restricción de versión.")
        check_version(requirement, version)
        for field in ("targets", "pieces", "tools"):
            values = data.get(field, [])
            if (
                not isinstance(values, list)
                or not all(isinstance(value, str) for value in values)
                or len(set(values)) != len(values)
            ):
                raise CuypilotError(f"Manifiesto inválido: {field} debe ser una lista de nombres únicos.")
            if field == "targets":
                valid = bool(values) and set(values) <= TARGETS.keys()
            else:
                valid = all(len(value) <= 64 and NAME.fullmatch(value) for value in values)
            if field in data and not valid:
                raise CuypilotError(f"Manifiesto inválido: {field} contiene nombres no permitidos.")
        if set(data.get("pieces", [])) & set(data.get("tools", [])):
            raise CuypilotError("Manifiesto inválido: una pieza aparece también como tool.")
        return cls(requirement, *(tuple(data.get(field, [])) for field in ("targets", "pieces", "tools")))

    def write(self, path: Path) -> None:
        """Escribe el formato corto canónico; conserva la selección, no comentarios TOML."""
        lines = [f"cuypilot = {json.dumps(self.cuypilot)}"]
        for field in ("targets", "pieces", "tools"):
            lines.append(f"{field} = {json.dumps(list(getattr(self, field)))}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
