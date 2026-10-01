"""Summarize a Python project in ~20 lines so the agent does not have to explore it file by file.

Read-only, standard library only. Usage::

    python workspace_context.py [ROOT]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

PYSPARK_IMPORT = re.compile(r"^\s*(from|import)\s+pyspark\b", re.MULTILINE)
SKIP_DIRS = {"venv", "build", "dist", "node_modules", "site-packages", "__pycache__"}
TOOL_FILES = {
    "ruff": ["ruff.toml", ".ruff.toml"],
    "mypy": ["mypy.ini"],
    "pre-commit": [".pre-commit-config.yaml"],
    "sphinx": ["docs/conf.py", "docs/source/conf.py"],
    "databricks bundle": ["databricks.yml", "databricks.yaml"],
}


def project_files(root: Path, pattern: str) -> list[Path]:
    """Files matching ``pattern`` under ``root``, skipping hidden, virtualenv and build folders."""
    return [
        p
        for p in root.rglob(pattern)
        if not any(part.startswith(".") or part in SKIP_DIRS for part in p.relative_to(root).parts[:-1])
    ]


def dep_name(spec: str) -> str:
    return re.split(r"[\s<>=!~;\[@]", spec.strip(), maxsplit=1)[0]


def summarize(root: Path) -> list[str]:
    """Build the summary lines.

    :param root: Project root.
    :returns: Human/LLM-readable lines.
    """
    lines = [f"project: {root.resolve().name}"]
    pyproject = root / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8")) if pyproject.exists() else {}
    project = data.get("project", {})

    python = project.get("requires-python")
    if (root / ".python-version").exists():
        python = f"{python or ''} (.python-version: {(root / '.python-version').read_text().strip()})"
    lines.append(f"python: {python or 'not declared'}")

    deps = [dep_name(d) for d in project.get("dependencies", [])]
    dev = [
        dep_name(d)
        for group in data.get("dependency-groups", {}).values()
        for d in group
        if isinstance(d, str)
    ]
    dev += [dep_name(d) for group in project.get("optional-dependencies", {}).values() for d in group]
    for req in sorted(root.glob("requirements*.txt")):
        names = [
            dep_name(x) for x in req.read_text(encoding="utf-8").splitlines() if x.strip() and x[0].isalpha()
        ]
        (dev if "dev" in req.name or "test" in req.name else deps).extend(names)
    lines.append(f"dependencies: {', '.join(sorted(set(deps))) or 'none declared'}")
    if dev:
        lines.append(f"dev dependencies: {', '.join(sorted(set(dev)))}")

    tools = [name for name, files in TOOL_FILES.items() if any((root / f).exists() for f in files)]
    tools += [t for t in ("ruff", "mypy", "pytest", "black") if t in data.get("tool", {}) and t not in tools]
    lines.append(f"tooling: {', '.join(tools) or 'none detected'}")

    src = root / "src"
    packages = sorted(p.parent.name for p in (src if src.is_dir() else root).glob("*/__init__.py"))
    lines.append(f"layout: {'src/' if src.is_dir() else 'flat'}; packages: {', '.join(packages) or 'none'}")

    py_files = project_files(root, "*.py")
    notebooks = project_files(root, "*.ipynb")
    db_notebooks = [
        p
        for p in py_files
        if p.read_text(encoding="utf-8", errors="ignore").startswith("# Databricks notebook source")
    ]
    lines.append(
        f"python files: {len(py_files)}; "
        f"notebooks: {len(notebooks)} .ipynb + {len(db_notebooks)} Databricks .py"
    )

    tests = [p for p in py_files if p.name.startswith("test_") or p.name.endswith("_test.py")]
    has_conftest = any(p.name == "conftest.py" for p in py_files)
    lines.append(f"tests: {len(tests)} test file(s){' + conftest.py' if has_conftest else ''}")

    if any(PYSPARK_IMPORT.search(p.read_text(encoding="utf-8", errors="ignore")) for p in py_files[:500]):
        lines.append("uses: pyspark")

    lock = root / ".github" / "cuypilot.lock.json"
    if lock.exists():
        items = json.loads(lock.read_text(encoding="utf-8"))["items"]
        pieces = [f"{name} ({item['type']})" for name, item in items.items()]
        lines.append(f"cuypilot pieces: {', '.join(pieces)}")
    if (root / ".github" / "copilot-instructions.md").exists():
        lines.append("instructions: .github/copilot-instructions.md present")
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    args = parser.parse_args(argv)
    print("\n".join(summarize(args.root)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
