"""Reproduce hallazgos de la revisión en carpetas temporales, sin red ni credenciales.

Ejecutar desde el repositorio con ``.venv/bin/python docs/reviews/2026-11-12/reproduce.py``.
Los asserts describen el defecto observado en 0.5.1; al corregirlo, deben convertirse en
regresiones que exijan el comportamiento correcto dentro de ``tests/``.
"""

import json
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from cuypilot.catalog import CATALOG_DIR, load_catalog
from cuypilot.deploy import GenieDeployment
from cuypilot.workspace import END, START, CuypilotError, Workspace


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def unicode_rollback(root):
    ws = Workspace(root, load_catalog(), "0.5.1", target="genie")
    ws.add(["python-standards"])
    instruction = root / next(iter(ws.lock["python-standards"]["files"]))
    instruction.write_bytes(b"\xff")
    before = snapshot(root)
    try:
        ws.add(["python-design"])
    except UnicodeDecodeError:
        pass
    else:
        raise AssertionError("Se esperaba UnicodeDecodeError")
    after = snapshot(root)
    assert before != after
    assert "python-design" in ws.lock
    assert "python-design" not in json.loads((root / ws.lock_path).read_text())["items"]
    return "Un error UTF-8 deja archivos nuevos y lock en memoria distintos del lock en disco."


def orphan_block(root):
    path = root / ".github/copilot-instructions.md"
    path.parent.mkdir(parents=True)
    path.write_text(f"# Reglas del equipo\n\n{START}\nConservar esta regla.\n{END}\n")
    Workspace(root, load_catalog(), "0.5.1").add(["python-design"])
    assert "Conservar esta regla." not in path.read_text()
    return "Un bloque con marcadores pero sin lock se sobrescribe sin --force."


def base_drift(root):
    catalog = root / "catalog"
    shutil.copytree(CATALOG_DIR, catalog)
    project = root / "project"
    ws = Workspace(project, load_catalog(catalog), "0.5.1", catalog)
    ws.add(["python-design"])
    base = catalog / "base/copilot-instructions.md"
    base.write_text(base.read_text() + "\nA new team convention.\n")
    assert ws.status() == {"python-design": "ok"}
    before = (project / ws.instructions_path).read_bytes()
    report = ws.update()
    assert not report.done
    assert before != (project / ws.instructions_path).read_bytes()
    return "status indica ok y update omite la pieza, pero cambia las instrucciones base."


class Remote:
    """Simula solo el almacenamiento remoto usado por el despliegue."""

    def __init__(self):
        self.files = {}
        self.imports = 0
        self.fail_second_import = True

    def __call__(self, command, cwd):
        action, path = command[2:4]
        if action == "get-status":
            return (
                (0, json.dumps({"object_type": "FILE"}))
                if path in self.files
                else (1, "RESOURCE_DOES_NOT_EXIST")
            )
        if action == "export":
            Path(command[command.index("--file") + 1]).write_bytes(self.files[path])
        elif action == "import":
            self.imports += 1
            if self.fail_second_import and self.imports == 2:
                return 1, "simulated interruption"
            self.files[path] = Path(command[command.index("--file") + 1]).read_bytes()
        elif action == "delete":
            del self.files[path]
        return 0, ""


def partial_deploy(root):
    ws = Workspace(root, load_catalog(), "0.5.1", target="genie", confirm=lambda commands: True)
    ws.add(["python-design"])
    remote = Remote()
    deploy = GenieDeployment(ws, "/Workspace/Users/review/project", run=remote)
    try:
        deploy.deploy()
    except CuypilotError as exc:
        assert "Despliegue parcial" in str(exc)
    else:
        raise AssertionError("Se esperaba fallo de despliegue")
    assert remote.files and not any(p.endswith("cuypilot.lock.json") for p in remote.files)
    remote.fail_second_import = False
    try:
        deploy.deploy()
    except CuypilotError as exc:
        assert "ajeno o modificado" in str(exc)
    else:
        raise AssertionError("El reintento debería encontrar el conflicto observado")
    return "El reintento de un despliegue parcial requiere --force por archivos de su propio intento."


if __name__ == "__main__":
    for probe in (unicode_rollback, orphan_block, base_drift, partial_deploy):
        with TemporaryDirectory(prefix="cuypilot-review-") as directory:
            print(f"CONFIRMADO {probe.__name__}: {probe(Path(directory))}")
