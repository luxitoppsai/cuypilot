"""Wizard de bienvenida (``cuypilot init``): banner, elección de rol e instalación guiada."""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from textwrap import fill

from cuypilot.catalog import Tool
from cuypilot.targets import TARGETS
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
    if "NO_COLOR" in os.environ or not sys.stdout.isatty():
        return text
    return f"\033[{code}m{text}\033[0m"


def banner(version: str) -> str:
    """Banner de cuypilot con la versión.

    :param version: Versión instalada de cuypilot.
    :returns: Texto listo para imprimir.
    """
    tagline = f"v{version} · catálogo para Copilot, OpenCode y Genie Code"
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


def choose_target() -> str:
    """Selecciona el asistente para la instalación interactiva."""
    print("\n  ¿Dónde quieres usar el catálogo?")
    names = list(TARGETS)
    return names[_choose(input, ">", [TARGETS[name].label for name in names])]


def _yes(ask: Callable[[str], str], prompt: str, default: bool) -> bool:
    while True:
        answer = ask(f"  {prompt} {'[S/n]' if default else '[s/N]'} ").strip().lower()
        if not answer:
            return default
        if answer in ("s", "si", "sí", "y", "yes", "n", "no"):
            return answer not in ("n", "no")
        print("  Responde sí o no.")


def _select(ask, pieces, defaults):
    """Selecciona números válidos sin descartar errores silenciosamente."""
    while True:
        answer = ask("  Enter conserva la selección; números (1,3), todos o ninguno: ").strip().lower()
        if not answer:
            return list(defaults)
        if answer == "todos":
            return list(pieces)
        if answer == "ninguno":
            return []
        tokens = [token.strip() for token in answer.split(",")]
        if all(token.isdigit() and 1 <= int(token) <= len(pieces) for token in tokens):
            return list(dict.fromkeys(pieces[int(token) - 1] for token in tokens))
        print(f"  Selección inválida. Usa números entre 1 y {len(pieces)}.")


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

    print(paint("  1/4 · Rol", "1;36"))
    print(f"  Proyecto: {ws.root}\n  Destino: {ws.target.label}\n")
    keys = list(roles)
    if role is None:
        print("  ¿Cuál es tu rol?")
        labels = [roles[k]["label"] for k in keys] + ["Elegir piezas a mano"]
        index = _choose(ask, ">", labels)
        role = keys[index] if index < len(keys) else None
    elif role not in roles:
        print(f"  Rol desconocido: {role}. Opciones: {', '.join(keys)}", file=sys.stderr)
        return 1

    pieces = [n for n, item in ws.catalog.items() if not isinstance(item, Tool) and ws.target.supports(item)]
    chosen = list(roles[role]["items"]) if role else []
    print(paint("\n  2/4 · Selección", "1;36"))
    if not assume_yes:
        print("  [✓] sugerida · instalada = ya está en el proyecto")
        for i, name in enumerate(pieces, start=1):
            item = ws.catalog[name]
            mark = "✓" if name in chosen else " "
            state = " · instalada" if name in ws.lock else ""
            if ws.target.name == "genie" and item.type == "agent":
                state += " · se instala como skill"
            print(f"    {i:>2}) [{mark}] {name} ({item.type}){state}")
            print(
                fill(
                    item.description,
                    width=shutil.get_terminal_size((80, 24)).columns,
                    initial_indent="        ",
                    subsequent_indent="        ",
                )
            )
        chosen = _select(ask, pieces, chosen)

    if not assume_yes:
        tools = [
            i
            for n, i in ws.catalog.items()
            if isinstance(i, Tool) and n not in ws.lock and ws.target.supports(i)
        ]
        if tools:
            print("\n  Herramientas opcionales:")
        for tool in tools:
            print(f"    {paint(tool.name, '1')}: {tool.description}")
            if _yes(ask, f"¿Agregar {tool.name}?", False):
                chosen.append(tool.name)

    if not chosen:
        print("  No elegiste ninguna pieza; no se instaló nada.")
        return 0
    print(paint("\n  3/4 · Resumen", "1;36"))
    print(f"\n  Se instalará: {', '.join(paint(n, '1') for n in chosen)}")
    items, commands = ws.plan_add(chosen)
    for item in items:
        dependency = " · dependencia" if item.name not in chosen else ""
        print(f"    + {item.name} ({item.type} {item.version}){dependency}")
    if not items:
        print("  Todas las piezas elegidas ya están instaladas.")
    if commands:
        print("  Y se ejecutarán estos comandos:")
        for cmd in commands:
            print(f"    $ {' '.join(cmd)}")
    if not assume_yes and not _yes(ask, "¿Instalar?", True):
        print("  Cancelado; no se instaló nada.")
        return 0

    previous_confirm = ws.confirm
    ws.confirm = lambda commands: True  # confirmación única con los comandos a la vista
    print(paint("\n  4/4 · Instalación", "1;36"), flush=True)
    print("  Aplicando selección…", flush=True)
    try:
        report = ws.add(chosen)
    finally:
        ws.confirm = previous_confirm
    for index, name in enumerate(report.done, start=1):
        print(f"  {paint('✓', '32')} [{index}/{len(report.done)}] {name}")
    for name, reason in report.skipped.items():
        print(f"  - {name}: {reason}")
    for note in report.notes:
        print(f"  nota: {note}")
    if ws.target.name != "copilot":
        _target_next_steps(ws)
        return 0
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


def _target_next_steps(ws: Workspace) -> None:
    print(f"\n  Listo para {ws.target.label}.")
    if ws.target.name == "opencode":
        print("  Abre OpenCode en este proyecto. Pide una skill por su nombre o elige un agente con @.")
    else:
        print("  Sincroniza el Git folder con Databricks o usa `cuypilot deploy --workspace-path <carpeta>`.")
        print("  En Settings de Genie Code, registra la carpeta .assistant/skills del workspace una vez.")
        print(
            "  Invoca skills y workflows adaptados de agentes con @nombre.\n"
            "  Inicia un chat nuevo tras actualizar."
        )
    print("  Las instrucciones se incluyen en AGENTS.md, conservando el contenido del proyecto.")
    print(
        f"  Versiona {ws.target.directory} y AGENTS.md; revisa `cuypilot status --target {ws.target.name}`."
    )
