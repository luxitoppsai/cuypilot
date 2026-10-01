"""Helpers para ejecutar los scripts de las skills como lo haría Copilot."""

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from cuypilot.catalog import CATALOG_DIR


@pytest.fixture
def run_script():
    """Ejecuta ``skills/<skill>/scripts/<script>`` con el Python actual y devuelve stdout."""

    def run(skill: str, script: str, *args: str) -> str:
        path = CATALOG_DIR / "skills" / skill / "scripts" / script
        result = subprocess.run(
            [sys.executable, str(path), *args], capture_output=True, text=True, check=True
        )
        return result.stdout

    return run


@pytest.fixture
def write(tmp_path):
    """Escribe un archivo dedentado en ``tmp_path`` y devuelve su ruta."""

    def _write(rel: str, content: str) -> Path:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content))
        return path

    return _write
