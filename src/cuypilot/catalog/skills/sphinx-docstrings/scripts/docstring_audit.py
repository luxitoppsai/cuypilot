"""Report public Python API elements whose Sphinx docstrings are missing or incomplete.

Read-only, standard library only. Usage::

    python docstring_audit.py [PATH ...] [--json]

One line per finding: ``path:line  kind  name - problems``.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {"venv", "build", "dist", "node_modules", "site-packages", "__pycache__"}
PARAM_RE = re.compile(r":param\s+(?:[^:]*\s)?\*{0,2}(\w+)\s*:")
RETURNS_RE = re.compile(r":returns?:")
YIELDS_RE = re.compile(r":yields?:")


def iter_python_files(paths: list[Path]):
    """Yield ``.py`` files under ``paths``, skipping hidden, virtualenv and build folders."""
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
        elif path.is_dir():
            for file in sorted(path.rglob("*.py")):
                parts = file.relative_to(path).parts[:-1]
                if not any(p.startswith(".") or p in SKIP_DIRS for p in parts):
                    yield file


def is_public(name: str) -> bool:
    return not name.startswith("_")


def own_nodes(func: ast.AST):
    """Walk the body of ``func`` without entering nested functions, classes or lambdas."""
    stack = list(ast.iter_child_nodes(func))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))


def signature_params(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = func.args
    names = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    names += [a.arg for a in (args.vararg, args.kwarg) if a]
    return [n for n in names if n not in ("self", "cls")]


def function_problems(func: ast.FunctionDef | ast.AsyncFunctionDef, doc: str) -> list[str]:
    """Compare a function docstring with its signature and body."""
    problems = []
    documented = set(PARAM_RE.findall(doc))
    params = signature_params(func)
    if missing := [p for p in params if p not in documented]:
        problems.append("missing :param: " + ", ".join(missing))
    if extra := sorted(documented - set(params)):
        problems.append("documents unknown params " + ", ".join(extra))

    decorators = {getattr(d, "id", getattr(d, "attr", "")) for d in func.decorator_list}
    nodes = list(own_nodes(func))
    if any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in nodes):
        if not YIELDS_RE.search(doc):
            problems.append("missing :yields:")
    elif "property" not in decorators and func.name != "__init__":
        returns_value = any(isinstance(n, ast.Return) and n.value is not None for n in nodes)
        annotated = func.returns is not None and not (
            isinstance(func.returns, ast.Constant) and func.returns.value is None
        )
        if (returns_value or annotated) and not RETURNS_RE.search(doc):
            problems.append("missing :returns:")
    return problems


def audit_file(path: Path) -> list[dict]:
    """Audit one file.

    :param path: Python source file.
    :returns: Findings as dicts with ``path``, ``line``, ``kind``, ``name`` and ``problems``.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError) as exc:
        return [{"path": str(path), "line": 1, "kind": "file", "name": path.name, "problems": [str(exc)]}]

    findings = []

    def report(node, kind, name, problems):
        if problems:
            findings.append(
                {
                    "path": str(path),
                    "line": getattr(node, "lineno", 1),
                    "kind": kind,
                    "name": name,
                    "problems": problems,
                }
            )

    if is_public(path.stem) or path.stem == "__init__":
        report(tree, "module", path.stem, [] if ast.get_docstring(tree) else ["missing docstring"])

    def visit_function(func, qualname, kind):
        doc = ast.get_docstring(func)
        report(func, kind, qualname, ["missing docstring"] if doc is None else function_problems(func, doc))

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and is_public(node.name):
            visit_function(node, node.name, "function")
        elif isinstance(node, ast.ClassDef) and is_public(node.name):
            class_doc = ast.get_docstring(node)
            report(node, "class", node.name, [] if class_doc else ["missing docstring"])
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if item.name == "__init__":
                    # Constructor params may be documented in the class or the __init__ docstring.
                    doc = (class_doc or "") + "\n" + (ast.get_docstring(item) or "")
                    missing = [p for p in signature_params(item) if p not in PARAM_RE.findall(doc)]
                    report(
                        item,
                        "init",
                        f"{node.name}.__init__",
                        ["missing :param: " + ", ".join(missing)] if missing else [],
                    )
                elif is_public(item.name):
                    visit_function(item, f"{node.name}.{item.name}", "method")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")])
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    files = list(iter_python_files(args.paths))
    findings = [f for file in files for f in audit_file(file)]
    if args.json:
        print(json.dumps(findings, indent=1))
        return 0
    for f in findings:
        print(f"{f['path']}:{f['line']}  {f['kind']}  {f['name']} - {'; '.join(f['problems'])}")
    print(f"\n{len(findings)} element(s) to document in {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
