"""Wizard de bienvenida (``cuypilot init``): banner, elección de rol e instalación guiada."""

from __future__ import annotations

import os
import sys
from collections.abc import Callable

from cuypilot.catalog import Tool
from cuypilot.workspace import Workspace

ART = r"""
                          _ __      __
  _______  ____  ______  (_) /___  / /_
 / ___/ / / / / / / __ \/ / / __ \/ __/
/ /__/ /_/ / /_/ / /_/ / / / /_/ / /_
\___/\__,_/\__, / .___/_/_/\____/\__/
          /____/_/"""


def paint(text: str, code: str) -> str:
    """Colorea ``text`` con un código ANSI solo si la salida es una terminal y no existe ``NO_COLOR``."""
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def banner(version: str) -> str:
    """Banner de cuypilot con la versión.

    :param version: Versión instalada de cuypilot.
    :returns: Texto listo para imprimir.
    """
    tagline = f"v{version} · skills, agents y herramientas para GitHub Copilot"
    return paint(ART, "1;36") + "  " + paint(tagline, "2") + "\n"


def _choose(ask: Callable[[str], str], prompt: str, options: list[str]) -> int:
    """Pide un número entre 1 y ``len(options)``; repite hasta que la respuesta sea válida."""
    for i, option in enumerate(options, start=1):
        print(f"    {i}) {option}")
    while True:
        answer = ask(f"  {prompt} ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(options):
            return int(answer) - 1
        print(f"  Escribe un número del 1 al {len(options)}.")


def _yes(ask: Callable[[str], str], prompt: str, default: bool) -> bool:
    answer = ask(f"  {prompt} {'[S/n]' if default else '[s/N]'} ").strip().lower()
    return default if not answer else answer in ("s", "si", "sí", "y", "yes")


def run_wizard(
    ws: Workspace,
    roles: dict[str, dict],
    version: str,
    role: str | None = None,
    assume_yes: bool = False,
    ask: Callable[[str], str] | None = None,
) -> int:
    """Guía la primera instalación: rol → piezas sugeridas → herramientas opcionales → instalación.

    :param ws: Workspace donde instalar.
    :param roles: Combinaciones por rol (``[roles]`` de ``catalog.toml``).
    :param version: Versión de cuypilot, para el banner.
    :param role: Rol elegido de antemano (modo no interactivo con ``assume_yes``).
    :param assume_yes: No preguntar: instala las piezas del rol, sin herramientas opcionales.
    :param ask: Función que lee la respuesta del usuario (por defecto, :func:`input`).
    :returns: Código de salida.
    """
    ask = ask or input
    print(banner(version))
    if ws.lock:
        print(
            f"  Este repo ya tiene {len(ws.lock)} pieza(s) instalada(s); "
            "usa `cuypilot status` o `cuypilot add`.\n"
        )

    keys = list(roles)
    if role is None:
        print("  ¿Cuál es tu rol?")
        labels = [roles[k]["label"] for k in keys] + ["Elegir piezas a mano"]
        index = _choose(ask, ">", labels)
        role = keys[index] if index < len(keys) else None
    elif role not in roles:
        print(f"  Rol desconocido: {role}. Opciones: {', '.join(keys)}", file=sys.stderr)
        return 1

    pieces = [n for n, item in ws.catalog.items() if not isinstance(item, Tool)]
    if role is None:
        print("\n  Piezas disponibles:")
        for i, name in enumerate(pieces, start=1):
            print(f"    {i:>2}) {name:<32} {ws.catalog[name].description}")
        answer = ask("  Números separados por coma (ej. 1,3,5): ")
        chosen = [
            pieces[int(x) - 1]
            for x in answer.replace(" ", "").split(",")
            if x.isdigit() and 0 < int(x) <= len(pieces)
        ]
    else:
        chosen = list(roles[role]["items"])

    if not assume_yes:
        tools = [i for n, i in ws.catalog.items() if isinstance(i, Tool) and n not in ws.lock]
        if tools:
            print("\n  Herramientas opcionales:")
        for tool in tools:
            print(f"    {paint(tool.name, '1')}: {tool.description}")
            if _yes(ask, f"¿Agregar {tool.name}?", False):
                chosen.append(tool.name)

    if not chosen:
        print("  No elegiste ninguna pieza; no se instaló nada.")
        return 0
    print(f"\n  Se instalará: {', '.join(paint(n, '1') for n in chosen)}")
    _, commands = ws.plan_add(chosen)
    if commands:
        print("  Y se ejecutarán estos comandos:")
        for cmd in commands:
            print(f"    $ {' '.join(cmd)}")
    if not assume_yes and not _yes(ask, "¿Instalar?", True):
        print("  Cancelado; no se instaló nada.")
        return 0

    ws.confirm = lambda commands: True  # ya se confirmó arriba, con los comandos a la vista
    report = ws.add(chosen)
    for name in report.done:
        print(f"  {paint('✓', '32')} {name}")
    for name, reason in report.skipped.items():
        print(f"  - {name}: {reason}")
    for note in report.notes:
        print(f"  nota: {note}")
    print(
        "\n  Cómo se usa cada tipo en Copilot Chat (modo Agent):\n"
        "    - instruction: se aplica SOLA al editar archivos; no aparece con /. Búscala en References.\n"
        "    - skill: escribe / y su nombre (ej. /design-review), o Copilot la elige según tu pedido.\n"
        "    - agent: elígelo en el selector de agentes del chat.\n"
        "\n  Siguientes pasos:\n"
        '    1. git add .github .gitignore && git commit -m "chore: copilot customizations via cuypilot"\n'
        "    2. En VS Code: Developer: Reload Window y abre Copilot Chat.\n"
        "    3. Guía completa: docs/guia-usuario.md del repo de cuypilot.\n"
    )
    return 0
