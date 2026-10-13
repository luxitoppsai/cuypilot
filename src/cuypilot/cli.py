"""CLI ``cuypilot``: instala piezas del catálogo en el workspace actual."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

from cuypilot.catalog import PATHS, load_catalog, load_roles
from cuypilot.deploy import GenieDeployment
from cuypilot.targets import TARGETS
from cuypilot.wizard import banner, choose_target, run_wizard
from cuypilot.workspace import Command, CuypilotError, Report, Workspace


def _ask(commands: list[Command]) -> bool:
    """Muestra los comandos que se van a ejecutar y pide confirmación en la terminal."""
    print("Se ejecutarán estos comandos:")
    for cmd in commands:
        print(f"  $ {' '.join(cmd)}")
    return input("¿Continuar? [s/N] ").strip().lower() in ("s", "si", "sí", "y", "yes")


def _print_report(report: Report, verb: str) -> None:
    for name in report.done:
        print(f"  {verb}: {name}")
    for name, reason in report.skipped.items():
        print(f"  omitida: {name} — {reason}")
    for note in report.notes:
        print(f"  nota: {note}")


def _cmd_list(ws: Workspace, args: argparse.Namespace) -> None:
    items = [i for i in ws.catalog.values() if args.type in (None, i.type)]
    print(f"Destino: {ws.target.label}")
    width = max((len(i.name) for i in items), default=0)
    for item in sorted(items, key=lambda i: (i.type, i.name)):
        mark = "*" if item.name in ws.lock else " "
        compatibility = "" if ws.target.supports(item) else " [no compatible]"
        print(
            f"{mark} {item.name:<{width}}  {item.type:<11}  {item.version:<8}  "
            f"{item.description}{compatibility}"
        )
    print("\n* = instalada en este workspace")


def _cmd_add(ws: Workspace, args: argparse.Namespace) -> None:
    if args.dry_run:
        items, commands = ws.plan_add(args.names)
        print("Se instalarían: " + (", ".join(i.name for i in items) or "nada (ya instaladas)"))
        for cmd in commands:
            print(f"  $ {' '.join(cmd)}")
        return
    _print_report(ws.add(args.names, force=args.force), "instalada")


def _cmd_remove(ws: Workspace, args: argparse.Namespace) -> None:
    _print_report(ws.remove(args.names, force=args.force), "quitada")


def _cmd_status(ws: Workspace, args: argparse.Namespace) -> None:
    states = ws.status()
    if not states:
        print("No hay piezas instaladas. Prueba `cuypilot list`.")
    for name, state in states.items():
        installed = ws.lock[name]["version"]
        approved = ws.catalog[name].version if name in ws.catalog else "retirada"
        print(f"  {name}: {state} · instalada {installed} · catálogo {approved} · {ws.target.name}")


def _cmd_update(ws: Workspace, args: argparse.Namespace) -> None:
    _print_report(ws.update(args.names or None, force=args.force), "actualizada")


def _cmd_deploy(ws: Workspace, args: argparse.Namespace) -> None:
    deployment = GenieDeployment(ws, args.workspace_path, args.profile)
    changed = deployment.deploy(dry_run=args.dry_run, force=args.force)
    if not changed:
        print("El destino remoto ya está al día.")


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos.

    :returns: Parser con los subcomandos ``list``, ``add``, ``remove``, ``status`` y ``update``.
    """
    parser = argparse.ArgumentParser(
        prog="cuypilot", description="Instala un catálogo versionado para Copilot, OpenCode y Genie Code."
    )
    parser.add_argument("--version", action="version", version=banner(pkg_version("cuypilot")))
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("init", help="Wizard: elige tu rol e instala las piezas sugeridas.")
    p.add_argument("--role", help="Rol a usar sin preguntar (dev, ds, mle, docs).")
    p.add_argument(
        "--yes", "-y", action="store_true", help="No preguntar (requiere --role; sin herramientas)."
    )
    p.set_defaults(func=None)

    p = sub.add_parser("list", help="Muestra el catálogo disponible.")
    p.add_argument("--type", choices=[*sorted(PATHS), "tool"])
    p.set_defaults(func=_cmd_list)

    p = sub.add_parser("add", help="Instala piezas (y sus dependencias).")
    p.add_argument("names", nargs="+")
    p.add_argument("--force", action="store_true", help="Sobrescribe archivos que no son de cuypilot.")
    p.add_argument("--dry-run", action="store_true", help="Muestra qué haría, sin cambiar nada.")
    p.add_argument("--yes", "-y", action="store_true", help="No pide confirmación para ejecutar comandos.")
    p.set_defaults(func=_cmd_add)

    p = sub.add_parser("remove", help="Quita piezas instaladas.")
    p.add_argument("names", nargs="+")
    p.add_argument("--force", action="store_true", help="Elimina también archivos modificados localmente.")
    p.add_argument("--yes", "-y", action="store_true", help="No pide confirmación para ejecutar comandos.")
    p.set_defaults(func=_cmd_remove)

    p = sub.add_parser("status", help="Estado de las piezas instaladas.")
    p.set_defaults(func=_cmd_status)

    p = sub.add_parser("update", help="Actualiza piezas instaladas a esta versión de cuypilot.")
    p.add_argument("names", nargs="*")
    p.add_argument("--force", action="store_true", help="Pisa también piezas modificadas localmente.")
    p.add_argument("--yes", "-y", action="store_true", help="No pide confirmación para ejecutar comandos.")
    p.set_defaults(func=_cmd_update)
    p = sub.add_parser("deploy", help="Publica la instalación Genie en Databricks Workspace.")
    p.add_argument("--workspace-path", required=True, help="Carpeta absoluta específica del workspace.")
    p.add_argument("--profile", help="Perfil de autenticación de la CLI oficial de Databricks.")
    p.add_argument("--dry-run", action="store_true", help="Consulta cambios sin escribir en Databricks.")
    p.add_argument("--force", action="store_true", help="Sobrescribe archivos remotos ajenos o modificados.")
    p.add_argument("--yes", "-y", action="store_true", help="Acepta los comandos de publicación.")
    p.set_defaults(func=_cmd_deploy)

    for command_parser in [parser, *sub.choices.values()]:
        command_parser.add_argument(
            "--target",
            choices=TARGETS,
            default=argparse.SUPPRESS,
            help="Asistente destino (copilot por defecto; deploy usa genie).",
        )
        command_parser.add_argument(
            "--path",
            type=Path,
            default=argparse.SUPPRESS,
            help="Raíz del proyecto (por defecto: directorio actual).",
        )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Punto de entrada de la CLI.

    :param argv: Argumentos (por defecto, ``sys.argv[1:]``).
    :returns: Código de salida.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    root = getattr(args, "path", Path.cwd()).resolve()
    if not (root / ".git").exists() and args.command in ("add", "update", "remove"):
        print("Aviso: este directorio no es la raíz de un repo git.", file=sys.stderr)
    confirm = (lambda commands: True) if getattr(args, "yes", False) else _ask
    try:
        target = getattr(args, "target", None)
        if (
            target is None
            and args.command in (None, "init")
            and not getattr(args, "yes", False)
            and not (args.command is None and (root / ".github/cuypilot.lock.json").exists())
        ):
            target = choose_target()
        ws = Workspace(
            root,
            load_catalog(),
            pkg_version("cuypilot"),
            confirm=confirm,
            target=target or ("genie" if args.command == "deploy" else "copilot"),
        )
        if args.command is None and ws.lock:
            parser.print_help()
            return 0
        if args.command in (None, "init"):
            if getattr(args, "yes", False) and not args.role:
                raise CuypilotError("--yes requiere --role (dev, ds, mle o docs).")
            return run_wizard(
                ws,
                load_roles(),
                pkg_version("cuypilot"),
                getattr(args, "role", None),
                getattr(args, "yes", False),
            )
        args.func(ws, args)
    except (CuypilotError, OSError, UnicodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado; no se cambió nada más.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
