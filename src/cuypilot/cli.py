"""CLI ``cuypilot``: instala piezas del catálogo en el workspace actual."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version as pkg_version
from pathlib import Path

from cuypilot.catalog import PATHS, load_catalog, load_roles
from cuypilot.console import paint, paragraph
from cuypilot.deploy import GenieDeployment
from cuypilot.project import Project, detect_targets
from cuypilot.targets import TARGETS
from cuypilot.wizard import choose_target, run_wizard
from cuypilot.workspace import (
    MODIFIED,
    NOT_INSTALLED,
    OK,
    OUTDATED,
    RETIRED,
    Command,
    CuypilotError,
    Report,
    Workspace,
)


def _ask(commands: list[Command]) -> bool:
    """Muestra los comandos que se van a ejecutar y pide confirmación en la terminal."""
    print("Se ejecutarán estos comandos:")
    for cmd in commands:
        print(f"  $ {' '.join(cmd)}")
    return input("¿Continuar? [s/N] ").strip().lower() in ("s", "si", "sí", "y", "yes")


def _print_report(report: Report, verb: str) -> None:
    preview = verb.startswith("se ")
    summary = f"{len(report.done)} previstas" if preview else f"{len(report.done)} aplicadas"
    attention = sum(reason.startswith(("modificada", "ya no existe")) for reason in report.skipped.values())
    badge, color = ("[PLAN]", "36") if preview else (("[!]", "33") if attention else ("[OK]", "32"))
    skipped_label = "sin aplicar" if attention else "sin cambios"
    print(paint(paragraph(f"{badge} {summary} · {len(report.skipped)} {skipped_label}"), color))
    for name in report.done:
        print(f"  {verb}: {name}")
    for name, reason in report.skipped.items():
        print(paragraph(f"omitida: {name} — {reason}"))
    for note in report.notes:
        print(paragraph(f"nota: {note}"))
    if attention:
        print(paragraph("Revisa las piezas omitidas antes de continuar; sus archivos se conservaron."))


def _next(command: str) -> None:
    # Los comandos se mantienen completos para poder copiarlos, incluso en terminales estrechas.
    print(f"\n  Desde la raíz del proyecto:\n    {command}")


def _cmd_list(ws: Workspace, args: argparse.Namespace) -> None:
    items = [i for i in ws.catalog.values() if args.type in (None, i.type)]
    print(paint(f"\nCatálogo · {ws.target.label}", "1;36"))
    installed = sum(i.name in ws.lock for i in items)
    print(paragraph(f"{len(items)} piezas · {installed} instaladas · * instalada · ! no compatible"))
    labels = {"instruction": "Instrucciones", "skill": "Skills", "agent": "Agentes", "tool": "Herramientas"}
    for kind, label in labels.items():
        group = sorted((item for item in items if item.type == kind), key=lambda item: item.name)
        if not group:
            continue
        print(paint(f"\n  {label} ({len(group)})", "1"))
        for item in group:
            compatible = ws.target.supports(item)
            mark = "*" if item.name in ws.lock else " "
            state = "" if compatible else " · ! no compatible"
            print(paragraph(f"{mark} {item.name}  {item.version}{state}"))
            print(paint(paragraph(item.description, indent=6), "2"))
    if not items:
        print(paragraph("No hay piezas para este filtro."))
    print("\n  Instalar una pieza:\n    cuypilot add <nombre>")
    print("  Filtrar catálogo:\n    cuypilot list --type skill")


def _cmd_add(ws: Workspace, args: argparse.Namespace) -> None:
    project = Project(ws, getattr(args, "target", None))
    if project.manifest is not None:
        if args.dry_run:
            print(paint("\n[PLAN] Vista previa · no se escribirán archivos", "36"))
            manifest = project.changed_manifest(args.names)
            desired = project.desired(manifest)
            for target, workspace in project.workspaces.items():
                required = {item.name for item in desired[target]}
                report, update_commands = workspace.plan_update(
                    sorted(set(workspace.lock) & required), force=args.force
                )
                items, commands = workspace.plan_add(
                    list(manifest.names) if target in project.targets else []
                )
                print(
                    f"{target}: se declararían {', '.join(args.names)}; "
                    f"nuevas: {', '.join(i.name for i in items)}"
                )
                _print_report(report, "se actualizaría")
                for name in sorted(set(workspace.lock) - required):
                    print(f"  se retiraría: {name}")
                for cmd in dict.fromkeys([*update_commands, *commands]):
                    print(f"  $ {' '.join(cmd)}")
        else:
            for target, report in project.change(args.names, force=args.force).items():
                print(f"Destino: {target}")
                _print_report(report, "instalada/actualizada")
        return
    if args.dry_run:
        print(paint("\n[PLAN] Vista previa · no se escribirán archivos", "36"))
        items, commands = ws.plan_add(args.names)
        print("Se instalarían: " + (", ".join(i.name for i in items) or "nada (ya instaladas)"))
        for cmd in commands:
            print(f"  $ {' '.join(cmd)}")
        return
    _print_report(ws.add(args.names, force=args.force), "instalada")


def _cmd_remove(ws: Workspace, args: argparse.Namespace) -> None:
    project = Project(ws, getattr(args, "target", None))
    if project.manifest is not None:
        for target, report in project.change(args.names, remove=True, force=args.force).items():
            print(f"Destino: {target}")
            _print_report(report, "actualizada")
        return
    _print_report(ws.remove(args.names, force=args.force), "quitada")


def _cmd_status(ws: Workspace, args: argparse.Namespace) -> None:
    states = ws.status()
    block = ws.block_status()
    if not states:
        print(paragraph("No hay piezas instaladas. Empieza con: cuypilot init"))
    issues = sum(state != OK for state in states.values()) + (block != OK)
    action = "estado requiere atención" if issues == 1 else "estados requieren atención"
    label = f"[!] {issues} {action}" if issues else "[OK] Instalación al día"
    if states or block != OK:
        print(paint(paragraph(f"{label} · {len(states)} piezas"), "33" if issues else "32"))
    priority = {MODIFIED: 0, NOT_INSTALLED: 1, RETIRED: 2, OUTDATED: 3, OK: 4}
    for name, state in sorted(states.items(), key=lambda row: (priority[row[1]], row[0])):
        installed = ws.lock[name]["version"]
        approved = ws.catalog[name].version if name in ws.catalog else "retirada"
        print(paint(paragraph(f"{name}: {state}"), "32" if state == OK else "33"))
        print(paragraph(f"instalada {installed} · catálogo {approved}", indent=4))
    if ws.lock or block != OK:
        print(paragraph(f"bloque compartido: {block} · {ws.instructions_path}"))
    values = set(states.values()) | {block}
    if MODIFIED in values:
        print(paragraph("Siguiente: revisa el diff de tus cambios locales antes de actualizar o eliminar."))
    if OUTDATED in values or NOT_INSTALLED in values:
        _next(f"cuypilot update --dry-run --target {ws.target.name}")
    if RETIRED in values:
        print(paragraph("Revisa las piezas retiradas antes de quitarlas."))
        _next("cuypilot remove <nombre>")


def _cmd_update(ws: Workspace, args: argparse.Namespace) -> None:
    if args.dry_run:
        print(paint("\n[PLAN] Vista previa · no se escribirán archivos", "36"))
        report, commands = ws.plan_update(args.names or None, force=args.force)
        _print_report(report, "se actualizaría")
        for cmd in commands:
            print(f"  $ {' '.join(cmd)}")
        return
    _print_report(ws.update(args.names or None, force=args.force), "actualizada")


def _cmd_install(ws: Workspace, args: argparse.Namespace) -> None:
    if args.frozen and (args.force or args.yes):
        raise CuypilotError("--frozen solo verifica; no se combina con --force ni --yes.")
    project = Project(ws, getattr(args, "target", None))
    if args.frozen:
        differences = project.differences(frozen=True)
        if differences:
            raise CuypilotError("Instalación congelada inconsistente:\n  " + "\n  ".join(differences))
        print(paint("[OK] Instalación congelada verificada.", "32"))
        return
    for target, report in project.install(force=args.force).items():
        print(f"Destino: {target}")
        _print_report(report, "instalada/actualizada")


def _cmd_audit(ws: Workspace, args: argparse.Namespace) -> None:
    differences = Project(ws, getattr(args, "target", None)).differences()
    for difference in differences:
        print(f"  {difference}")
    if not differences:
        print(paint("[OK] Integridad verificada.", "32"))
        print(paragraph("Alcance: archivos, lockfiles y bloques gestionados."))
    else:
        print(paragraph(f"[!] {len(differences)} inconsistencias. Revisa los detalles anteriores."))
    if args.ci and differences:
        raise CuypilotError("Auditoría de integridad fallida.")


def _cmd_outdated(ws: Workspace, args: argparse.Namespace) -> None:
    count = 0
    for name, entry in sorted(ws.lock.items()):
        item = ws.catalog.get(name)
        if item is None:
            count += 1
            print(f"  {name}: retirada")
        elif entry["version"] != item.version or ws._status(name) == OUTDATED:
            count += 1
            print(f"  {name}: {entry['version']} -> {item.version} (versión o contenido/integración)")
    if ws.block_status() == OUTDATED:
        count += 1
        print(f"  bloque compartido: desactualizado · {ws.instructions_path}")
    if count:
        print(paragraph(f"[!] {count} diferencias respecto al wheel instalado."))
        _next(f"cuypilot update --dry-run --target {ws.target.name}")
    elif ws.lock:
        print(paint(paragraph("[OK] No hay actualizaciones pendientes respecto al wheel instalado."), "32"))
    else:
        print(paragraph("No hay piezas instaladas. Empieza con: cuypilot init"))


def _cmd_why(ws: Workspace, args: argparse.Namespace) -> None:
    if args.name not in ws.lock:
        raise CuypilotError(f"No está instalada: {args.name}")
    paths = []

    def visit(name, path):
        if name in path:
            return
        trail = [*path, name]
        if name == args.name and path:
            paths.append(" -> ".join(trail))
        item = ws.catalog.get(name)
        for dep in ws.lock[name].get("requires", item.requires if item else ()):
            if dep in ws.lock:
                visit(dep, trail)

    for name in sorted(ws.lock):
        visit(name, [])
    print("\n".join(f"  {path}" for path in paths) or f"  {args.name}: sin dependientes instalados.")


def _cmd_deploy(ws: Workspace, args: argparse.Namespace) -> None:
    deployment = GenieDeployment(ws, args.workspace_path, args.profile)
    changed = deployment.deploy(dry_run=args.dry_run, force=args.force, resume=args.resume)
    if not changed:
        print("El destino remoto ya está al día.")


def build_parser() -> argparse.ArgumentParser:
    """Construye el parser de argumentos.

    :returns: Parser de instalación, gestión, consultas y despliegue del catálogo.
    """
    parser = argparse.ArgumentParser(
        prog="cuypilot",
        description="Instala un catálogo versionado para Copilot, OpenCode y Genie Code.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Empieza aquí:\n  cuypilot init                     Elegir e instalar piezas\n"
            "  cuypilot list                     Explorar el catálogo\n"
            "  cuypilot status                   Revisar lo instalado\n"
            "  cuypilot install --frozen         Verificar en CI\n\n"
            "Más ayuda: cuypilot <comando> --help"
        ),
    )
    parser.add_argument("--version", action="version", version=f"cuypilot {pkg_version('cuypilot')}")
    sub = parser.add_subparsers(dest="command", title="Comandos", metavar="comando")

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
    p.add_argument("--dry-run", action="store_true", help="Muestra el plan sin escribir.")
    p.set_defaults(func=_cmd_update)
    p = sub.add_parser("install", help="Reconcilia los destinos desde cuypilot.toml; migra locks si falta.")
    p.add_argument("--frozen", action="store_true", help="Solo verifica manifiesto, locks y archivos.")
    p.add_argument("--force", action="store_true", help="Adopta conflictos y restaura cambios locales.")
    p.add_argument("--yes", "-y", action="store_true", help="Acepta comandos de herramientas.")
    p.set_defaults(func=_cmd_install)
    p = sub.add_parser("audit", help="Comprueba integridad instalada (sin escaneo de contenido).")
    p.add_argument("--ci", action="store_true", help="Devuelve error si encuentra inconsistencias.")
    p.set_defaults(func=_cmd_audit)
    p = sub.add_parser("outdated", help="Lista diferencias de versión o contenido respecto al wheel.")
    p.set_defaults(func=_cmd_outdated)
    p = sub.add_parser("why", help="Explica las dependencias instaladas de una pieza.")
    p.add_argument("name")
    p.set_defaults(func=_cmd_why)
    p = sub.add_parser("deploy", help="Publica la instalación Genie en Databricks Workspace.")
    p.add_argument("--workspace-path", required=True, help="Carpeta absoluta específica del workspace.")
    p.add_argument("--profile", help="Perfil de autenticación de la CLI oficial de Databricks.")
    p.add_argument("--dry-run", action="store_true", help="Consulta cambios sin escribir en Databricks.")
    p.add_argument("--force", action="store_true", help="Sobrescribe archivos remotos ajenos o modificados.")
    p.add_argument("--resume", action="store_true", help="Reintenta adoptando solo contenido idéntico.")
    p.add_argument("--yes", "-y", action="store_true", help="Acepta los comandos de publicación.")
    p.set_defaults(func=_cmd_deploy)

    for command_parser in [parser, *sub.choices.values()]:
        command_parser.add_argument(
            "--target",
            choices=TARGETS,
            default=argparse.SUPPRESS,
            help="Asistente destino; por defecto manifiesto/detección, o genie en deploy.",
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
        catalog, version = load_catalog(), pkg_version("cuypilot")
        # Validar el manifiesto antes de cualquier escritura, incluso en comandos históricos.
        initial = Workspace(root, catalog, version, confirm=confirm, target=target or "copilot")
        project = Project(initial, target)
        if (
            target is None
            and args.command in (None, "init")
            and not getattr(args, "yes", False)
            and not (args.command is None and any(w.lock for w in project.workspaces.values()))
        ):
            target = choose_target()
        ws = Workspace(
            root,
            catalog,
            version,
            confirm=confirm,
            target=target or ("genie" if args.command == "deploy" else project.targets[0]),
        )
        if args.command is None and any(w.lock for w in project.workspaces.values()):
            parser.print_help()
            return 0
        if args.command in (None, "init"):
            if getattr(args, "yes", False) and not args.role:
                raise CuypilotError("--yes requiere --role (dev, ds, mle o docs).")
            if project.manifest:
                raise CuypilotError("Ya existe cuypilot.toml; usa install o add para cambiar la selección.")
            return run_wizard(
                ws,
                load_roles(),
                version,
                getattr(args, "role", None),
                getattr(args, "yes", False),
                install=lambda names: _init_install(ws, names),
            )
        multiple = args.command in ("list", "status", "update", "outdated", "why") and target is None
        if multiple:
            for workspace in project.workspaces.values():
                if args.command != "list":
                    print(paint(f"\nDestino: {workspace.target.label}", "1;36"))
                args.func(workspace, args)
        else:
            if args.command in ("status", "update", "outdated", "why"):
                print(paint(f"\nDestino: {ws.target.label}", "1;36"))
            args.func(ws, args)
    except (CuypilotError, OSError, UnicodeError) as exc:
        print(paint(f"Error: {exc}", "31", stream=sys.stderr), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\nCancelado; no se cambió nada más.", file=sys.stderr)
        return 1
    return 0


def _init_install(ws: Workspace, names: list[str]) -> Report:
    """El wizard confirma una selección; manifiesto y archivos se guardan juntos."""
    from dataclasses import replace

    from cuypilot.catalog import Tool

    existing_targets = detect_targets(ws.root)
    if any(target != ws.target.name for target in existing_targets):
        raise CuypilotError("Para migrar varios destinos existentes usa install o escribe cuypilot.toml.")
    project = Project(ws, ws.target.name)
    manifest = project.migrate()
    selected = set(manifest.names) | set(names)
    manifest = replace(
        manifest,
        pieces=tuple(sorted(name for name in selected if not isinstance(ws.catalog[name], Tool))),
        tools=tuple(sorted(name for name in selected if isinstance(ws.catalog[name], Tool))),
    )
    return project.install(manifest)[ws.target.name]


if __name__ == "__main__":
    sys.exit(main())
