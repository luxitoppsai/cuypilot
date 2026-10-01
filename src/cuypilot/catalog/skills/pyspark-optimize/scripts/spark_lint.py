"""Find high-confidence PySpark performance anti-patterns in .py modules, Databricks notebooks and .ipynb.

Read-only, standard library only. Usage::

    python spark_lint.py [PATH ...] [--json]

One line per finding: ``SEVERITY  location  CODE  message``.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

SKIP_DIRS = {"venv", "build", "dist", "node_modules", "site-packages", "__pycache__"}
SEVERITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
LOOPS = (ast.For, ast.AsyncFor, ast.While)
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
ACTIONS = {"count", "collect", "show", "first", "toPandas"}  # zero-argument Spark actions
LANGUAGE_MAGICS = {"sql", "md", "sh", "scala", "r", "fs", "bash", "markdown"}  # whole cell is not Python
REDUCED = {"limit", "agg", "groupBy", "groupby", "summary", "describe", "head", "take", "first"}

RULES = {
    "SP001": ("HIGH", "Python UDF: prefer pyspark.sql.functions built-ins, else a vectorized pandas_udf"),
    "SP002": ("MEDIUM", "collect()/toPandas() brings data to the driver: confirm the volume is small"),
    "SP003": ("HIGH", "withColumn inside a loop: build the columns once with select()/withColumns()"),
    "SP004": ("HIGH", "Spark action inside a loop: each iteration triggers a full job"),
    "SP005": ("MEDIUM", ".rdd drops the optimizer: use the DataFrame API equivalent"),
    "SP006": ("MEDIUM", "repartition(1)/coalesce(1) funnels all data through one task"),
    "SP007": ("LOW", "cache()/persist() without unpersist() in this file: release it or justify it"),
    "SP008": ("MEDIUM", "cross join: confirm it is intentional (rows multiply)"),
    "SP009": ("HIGH", "SQL built with string formatting: use spark.sql(query, args={...}) parameters"),
    "SP010": ("LOW", "display()/show() left in a module: remove from production code"),
    "SP011": ("MEDIUM", "inferSchema reads the data twice and is unstable: declare an explicit schema"),
    "SP012": ("HIGH", "iterating rows on the driver: express it as a distributed transformation"),
}


def iter_sources(paths: list[Path]):
    """Yield ``.py`` and ``.ipynb`` files under ``paths``, skipping hidden, virtualenv and build folders."""
    for path in paths:
        if path.is_file() and path.suffix in (".py", ".ipynb"):
            yield path
        elif path.is_dir():
            for file in sorted([*path.rglob("*.py"), *path.rglob("*.ipynb")]):
                parts = file.relative_to(path).parts[:-1]
                if not any(p.startswith(".") or p in SKIP_DIRS for p in parts):
                    yield file


def load_ipynb(path: Path) -> tuple[str, list[tuple[int, int]]]:
    """Join the Python code cells of a notebook.

    Magic cells (``%sql``, ``%md``...) are blanked and magic/shell lines become ``pass`` so line numbers
    stay aligned.

    :returns: The source and, per source line, its ``(cell number, line in cell)``.
    """
    cells = json.loads(path.read_text(encoding="utf-8")).get("cells", [])
    lines, where = [], []
    for number, cell in enumerate(cells, start=1):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", "")
        cell_lines = (source if isinstance(source, str) else "".join(source)).splitlines()
        first = cell_lines[0].split()[0] if cell_lines and cell_lines[0].split() else ""
        magic_cell = first.lstrip("%") in LANGUAGE_MAGICS and first.startswith("%")
        for i, line in enumerate(cell_lines, start=1):
            stripped = line.lstrip()
            if magic_cell:
                line = ""
            elif stripped.startswith(("%", "!")):
                line = line[: len(line) - len(stripped)] + "pass"
            lines.append(line)
            where.append((number, i))
    return "\n".join(lines), where


def call_name(node: ast.Call) -> str:
    func = node.func
    return func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")


def chain_names(node: ast.AST) -> set[str]:
    """Method names called along a ``a.b().c().d()`` receiver chain."""
    names = set()
    while isinstance(node, (ast.Call, ast.Attribute)):
        if isinstance(node, ast.Call):
            names.add(call_name(node))
            node = node.func
        node = node.value if isinstance(node, ast.Attribute) else node
    return names


def nodes_in_loops(tree: ast.AST):
    """Yield nodes that execute inside a loop body (without crossing into nested functions/classes)."""

    def walk(node: ast.AST, in_loop: bool):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, SCOPES):
                yield from walk(child, False)
                continue
            if in_loop:
                yield child
            loop_body = isinstance(node, LOOPS) and child not in (
                getattr(node, "iter", None),
                getattr(node, "target", None),
            )
            yield from walk(child, in_loop or loop_body)

    yield from walk(tree, False)


def is_string_built(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return any(isinstance(v, ast.FormattedValue) for v in node.values)
    if isinstance(node, ast.Call) and call_name(node) == "format":
        return True
    return (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, (ast.Add, ast.Mod))
        and (
            isinstance(node.left, (ast.Constant, ast.JoinedStr))
            or isinstance(node.right, (ast.Constant, ast.JoinedStr))
        )
    )


def lint_tree(tree: ast.AST, notebook: bool) -> list[tuple[int, str]]:
    """Apply the rules to a parsed file.

    :param tree: Parsed module.
    :param notebook: Whether the file is a notebook (``display``/``show`` are fine there).
    :returns: ``(line, code)`` pairs.
    """
    hits: set[tuple[int, str]] = set()
    in_loop = set(map(id, nodes_in_loops(tree)))
    row_iterations = set()

    for node in ast.walk(tree):
        if (
            isinstance(node, (ast.For, ast.AsyncFor))
            and isinstance(node.iter, ast.Call)
            and call_name(node.iter) in ("collect", "toLocalIterator", "iterrows", "itertuples")
        ):
            hits.add((node.lineno, "SP012"))
            row_iterations.add(id(node.iter))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for deco in node.decorator_list:  # bare @udf; @udf(...) is caught as a call below
                if not isinstance(deco, ast.Call) and getattr(deco, "attr", getattr(deco, "id", "")) == "udf":
                    hits.add((node.lineno, "SP001"))
        elif isinstance(node, ast.Attribute) and node.attr == "rdd":
            hits.add((node.lineno, "SP005"))
        elif isinstance(node, ast.Call):
            name, func, args = call_name(node), node.func, node.args
            if name == "udf" or (
                name == "register" and getattr(getattr(func, "value", None), "attr", "") == "udf"
            ):
                hits.add((node.lineno, "SP001"))
            elif name in ("collect", "toPandas") and not args and id(node) not in row_iterations | in_loop:
                hits.add((node.lineno, "SP002"))
            if name == "withColumn" and id(node) in in_loop:
                hits.add((node.lineno, "SP003"))
            if name in ACTIONS and not args and id(node) in in_loop and id(node) not in row_iterations:
                hits.add((node.lineno, "SP004"))
            if (
                name in ("repartition", "coalesce")
                and args
                and isinstance(args[0], ast.Constant)
                and args[0].value == 1
            ):
                hits.add((node.lineno, "SP006"))
            if name in ("cache", "persist"):
                hits.add((node.lineno, "SP007"))
            if name == "crossJoin" or (
                name == "join"
                and any(k.arg == "how" and getattr(k.value, "value", None) == "cross" for k in node.keywords)
            ):
                hits.add((node.lineno, "SP008"))
            if name == "sql" and args and is_string_built(args[0]):
                hits.add((node.lineno, "SP009"))
            if not notebook and (name == "display" and isinstance(func, ast.Name) or name == "show"):
                hits.add((node.lineno, "SP010"))
            infer = any(
                k.arg == "inferSchema" and getattr(k.value, "value", None) in (True, "true")
                for k in node.keywords
            )
            option = (
                name == "option"
                and len(args) == 2
                and getattr(args[0], "value", None) == "inferSchema"
                and str(getattr(args[1], "value", "")).lower() == "true"
            )
            if infer or option:
                hits.add((node.lineno, "SP011"))

    if any(isinstance(n, ast.Call) and call_name(n) == "unpersist" for n in ast.walk(tree)):
        hits = {h for h in hits if h[1] != "SP007"}
    return sorted(hits)


def reduced_collect(tree: ast.AST, line: int) -> bool:
    """Whether the collect()/toPandas() on ``line`` follows a reducing call (agg, limit...)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.lineno == line and call_name(node) in ("collect", "toPandas"):
            return bool(chain_names(node.func) & REDUCED)
    return False


def lint_file(path: Path) -> list[dict]:
    """Lint one file.

    :param path: ``.py`` module, Databricks ``.py`` notebook or ``.ipynb``.
    :returns: Findings as dicts with ``severity``, ``location``, ``code`` and ``message``.
    """
    where = None
    try:
        if path.suffix == ".ipynb":
            source, where = load_ipynb(path)
        else:
            source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (SyntaxError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [
            {"severity": "LOW", "location": str(path), "code": "PARSE", "message": f"could not parse: {exc}"}
        ]

    notebook = where is not None or source.startswith("# Databricks notebook source")
    findings = []
    for line, code in lint_tree(tree, notebook):
        severity, message = RULES[code]
        if code == "SP002" and reduced_collect(tree, line):
            severity = "LOW"
        location = f"{path}:cell{where[line - 1][0]}:{where[line - 1][1]}" if where else f"{path}:{line}"
        findings.append({"severity": severity, "location": location, "code": code, "message": message})
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", type=Path, default=[Path(".")])
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    files = list(iter_sources(args.paths))
    findings = sorted(
        (f for file in files for f in lint_file(file)),
        key=lambda f: (SEVERITY_ORDER[f["severity"]], f["location"]),
    )
    if args.json:
        print(json.dumps(findings, indent=1))
        return 0
    for f in findings:
        print(f"{f['severity']:<6}  {f['location']}  {f['code']}  {f['message']}")
    print(f"\n{len(findings)} finding(s) in {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
