"""Reglas para scripts dentro de skills (RFC-002 §4.1): solo stdlib, sin red, sin escribir archivos."""

import ast
import sys

import pytest

from cuypilot.catalog import CATALOG_DIR

SCRIPTS = sorted(CATALOG_DIR.glob("skills/*/scripts/*.py"))
NETWORK = {"socket", "http", "urllib", "ftplib", "smtplib", "requests", "httpx", "aiohttp"}
WRITES = {"write_text", "write_bytes", "unlink", "rmdir", "rename", "replace", "mkdir", "remove", "rmtree"}


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parents[1].name}/{p.name}")
def test_script_follows_rules(script):
    tree = ast.parse(script.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [a.name.split(".")[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            modules = [node.module.split(".")[0]]
        else:
            modules = []
        for module in modules:
            assert module in sys.stdlib_module_names, f"{module} no es stdlib"
            assert module not in NETWORK, f"{module}: los scripts no usan red"

        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "attr", getattr(func, "id", ""))
            assert name not in WRITES, f"línea {node.lineno}: {name}() escribe en disco"
            if name == "open":
                mode = (
                    node.args[1]
                    if len(node.args) > 1
                    else next((k.value for k in node.keywords if k.arg == "mode"), None)
                )
                assert mode is None or "r" in getattr(mode, "value", ""), (
                    f"línea {node.lineno}: open() en modo escritura"
                )


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: f"{p.parents[1].name}/{p.name}")
def test_script_is_referenced_by_its_skill(script):
    skill_md = (script.parents[1] / "SKILL.md").read_text(encoding="utf-8")
    assert f"scripts/{script.name}" in skill_md, "el SKILL.md debe explicar cuándo ejecutar el script"
