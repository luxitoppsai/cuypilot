"""Flag Python code that is likely over-complex or over-engineered, ranked by severity.

Read-only, standard library only. Usage::

    python code_metrics.py [PATH ...] [--json] [--limit N]

One line per finding: ``SEVERITY  path:line  name - problem``.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

SKIP_DIRS = {"venv", "build", "dist", "node_modules", "site-packages", "__pycache__"}
NESTING = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.With, ast.AsyncWith, ast.Try, ast.Match)
BRANCHES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp, ast.match_case)
FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}

# (metric, medium threshold, high threshold)
LIMITS = {"lines": (50, 100), "params": (5, 8), "nesting": (3, 5), "complexity": (10, 20)}


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


def max_nesting(node: ast.AST, depth: int = 0) -> int:
    deepest = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, FUNCTIONS + (ast.ClassDef, ast.Lambda)):
            continue
        is_elif = isinstance(node, ast.If) and node.orelse == [child] and isinstance(child, ast.If)
        deepest = max(deepest, max_nesting(child, depth + (isinstance(child, NESTING) and not is_elif)))
    return deepest


def complexity(func: ast.AST) -> int:
    """Approximate cyclomatic complexity of ``func`` (nested functions excluded)."""
    score, stack = 1, list(ast.iter_child_nodes(func))
    while stack:
        node = stack.pop()
        if isinstance(node, FUNCTIONS + (ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(node, BRANCHES):
            score += 1
        elif isinstance(node, ast.BoolOp):
            score += len(node.values) - 1
        elif isinstance(node, ast.comprehension):
            score += 1 + len(node.ifs)
        stack.extend(ast.iter_child_nodes(node))
    return score


def rate(metric: str, value: int) -> str | None:
    medium, high = LIMITS[metric]
    return "HIGH" if value > high else "MEDIUM" if value > medium else None


def base_names(cls: ast.ClassDef) -> set[str]:
    return {getattr(b, "id", getattr(b, "attr", "")) for b in cls.bases}


def is_abstract(cls: ast.ClassDef) -> bool:
    if "ABC" in base_names(cls) or any(getattr(k.value, "id", "") == "ABCMeta" for k in cls.keywords):
        return True
    return any(
        getattr(d, "id", getattr(d, "attr", "")) == "abstractmethod"
        for item in cls.body
        if isinstance(item, FUNCTIONS)
        for d in item.decorator_list
    )


def analyze(files: list[Path]) -> list[dict]:
    """Analyze files and return findings sorted by severity.

    :param files: Python source files.
    :returns: Findings as dicts with ``severity``, ``path``, ``line``, ``name`` and ``problem``.
    """
    findings: list[dict] = []
    classes: list[tuple[Path, ast.ClassDef]] = []

    def add(severity, path, node, name, problem):
        findings.append(
            {"severity": severity, "path": str(path), "line": node.lineno, "name": name, "problem": problem}
        )

    for path in files:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, FUNCTIONS):
                args = node.args
                params = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
                metrics = {
                    "lines": node.end_lineno - node.lineno + 1,
                    "params": len([p for p in params if p not in ("self", "cls")]),
                    "nesting": max_nesting(node),
                    "complexity": complexity(node),
                }
                for metric, value in metrics.items():
                    if severity := rate(metric, value):
                        limit = LIMITS[metric][0]
                        add(severity, path, node, node.name, f"{metric}={value} (limit {limit})")
            elif isinstance(node, ast.ClassDef):
                classes.append((path, node))
                methods = [i.name for i in node.body if isinstance(i, FUNCTIONS)]
                public = [m for m in methods if not m.startswith("_")]
                if not node.bases and "__init__" in methods and len(public) == 1 and len(methods) == 2:
                    add(
                        "LOW",
                        path,
                        node,
                        node.name,
                        f"class with only __init__ and {public[0]}() - could be a function",
                    )
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    add("HIGH", path, node, "except", "bare `except:` catches everything, including bugs")
                elif all(isinstance(s, ast.Pass) for s in node.body):
                    add("HIGH", path, node, "except", "exception silently swallowed (`pass`)")

    for path, cls in classes:
        if is_abstract(cls):
            implementations = sum(cls.name in base_names(other) for _, other in classes)
            if implementations <= 1:
                add(
                    "MEDIUM",
                    path,
                    cls,
                    cls.name,
                    f"abstract class with {implementations} implementation(s) in the analyzed code",
                )

    return sorted(findings, key=lambda f: (SEVERITY_ORDER[f["severity"]], f["path"], f["line"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")])
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    parser.add_argument("--limit", type=int, default=50, help="Max findings to print (default 50).")
    args = parser.parse_args(argv)

    files = list(iter_python_files(args.paths))
    findings = analyze(files)
    shown = findings[: args.limit]
    if args.json:
        print(json.dumps(shown, indent=1))
        return 0
    for f in shown:
        print(f"{f['severity']:<6}  {f['path']}:{f['line']}  {f['name']} - {f['problem']}")
    hidden = len(findings) - len(shown)
    print(
        f"\n{len(findings)} finding(s) in {len(files)} file(s)"
        + (f", {hidden} not shown." if hidden else ".")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
