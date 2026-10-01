"""Extract a pipeline's data flow (tables read/written, parameters, steps, new columns) for docs.

Works on .py modules, Databricks .py notebooks and .ipynb. Read-only, standard library only. Usage::

    python data_flow.py PATH [PATH ...] [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

SKIP_DIRS = {"venv", "build", "dist", "node_modules", "site-packages", "__pycache__", "tests", "test"}

# --- shared helpers: keep identical in notebook-to-module/scripts/notebook_outline.py -------------------

MAGIC_KINDS = {
    "sql": "sql",
    "md": "md",
    "run": "run",
    "pip": "pip",
    "sh": "sh",
    "fs": "fs",
    "scala": "scala",
    "r": "r",
}
READ_SOURCES = {"table", "load", "parquet", "csv", "json", "orc", "text", "delta"}
WRITE_TARGETS = {
    "saveAsTable",
    "insertInto",
    "toTable",
    "save",
    "parquet",
    "csv",
    "json",
    "orc",
    "text",
    "delta",
}
SQL_READ = re.compile(r"\b(?:FROM|JOIN)\s+([`\w.{}$]+)", re.IGNORECASE)
SQL_WRITE = re.compile(
    r"\b(?:INSERT\s+(?:INTO|OVERWRITE)(?:\s+TABLE)?|MERGE\s+INTO|CREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW)"
    r"(?:\s+IF\s+NOT\s+EXISTS)?)\s+([`\w.{}$]+)",
    re.IGNORECASE,
)


def split_cells(path: Path) -> list[tuple[int, str, str]]:
    """Split a source file into cells.

    :param path: ``.ipynb``, Databricks ``.py`` notebook or plain ``.py`` module (one cell).
    :returns: ``(cell number, kind, source)`` where kind is ``python``, ``sql``, ``md``, ``run``, ``pip``...
    """
    if path.suffix == ".ipynb":
        raw = []
        for cell in json.loads(path.read_text(encoding="utf-8")).get("cells", []):
            source = cell.get("source", "")
            text = source if isinstance(source, str) else "".join(source)
            raw.append(text if cell.get("cell_type") == "code" else "%md\n" + text)
    else:
        text = path.read_text(encoding="utf-8")
        if not text.startswith("# Databricks notebook source"):
            return [(1, "python", text)]
        raw = []
        for chunk in re.split(
            r"^# COMMAND -+\s*$", text.split("\n", 1)[1] if "\n" in text else "", flags=re.M
        ):
            lines = chunk.strip("\n").splitlines()
            if lines and all(line.startswith("# MAGIC") for line in lines):
                lines = [line[len("# MAGIC") :].removeprefix(" ") for line in lines]
            raw.append("\n".join(lines))
    cells = []
    for number, text in enumerate(raw, start=1):
        first = text.split(None, 1)[0] if text.split() else ""
        kind = MAGIC_KINDS.get(first[1:], "python") if first.startswith("%") else "python"
        lines = [line for line in text.splitlines() if line.strip()]
        if kind in ("pip", "run") and not all(line.lstrip().startswith(("%", "!", "#")) for line in lines):
            kind = "python"  # line magic followed by Python code
        if kind == "python":
            body = "\n".join(
                "pass" if line.lstrip().startswith(("%", "!")) else line for line in text.splitlines()
            )
        else:  # drop the magic token (%sql, %run...) and keep the rest
            body = text.split(None, 1)[1] if len(text.split(None, 1)) > 1 else ""
        cells.append((number, kind, body))
    return cells


def literal(node: ast.AST | None) -> str | None:
    """String value of a literal or, for dynamic expressions (f-strings, variables), their source text."""
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return f"<{ast.unparse(node)}>"


def tables_in_sql(sql: str) -> tuple[list[str], list[str]]:
    """Tables read and written by a SQL text.

    :returns: ``(reads, writes)``.
    """
    writes = [t.strip("`") for t in SQL_WRITE.findall(sql)]
    reads = [t.strip("`") for t in SQL_READ.findall(sql) if t.strip("`") not in writes]
    return reads, writes


def chain(node: ast.AST) -> list[str]:
    """Attribute/call names along a receiver chain, outermost last (``spark.read.format().load`` ...)."""
    names = []
    while isinstance(node, (ast.Call, ast.Attribute, ast.Name)):
        if isinstance(node, ast.Call):
            node = node.func
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
            node = node.value
        else:
            names.append(node.id)
            break
    return names[::-1]


def calls_in_order(tree: ast.AST) -> list[ast.Call]:
    """Method calls sorted by where the method name appears (keeps chained calls in reading order)."""
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
    return sorted(calls, key=lambda n: (n.func.end_lineno, n.func.end_col_offset))


def io_calls(tree: ast.AST) -> dict[str, list[str]]:
    """Reads, writes and parameters found in Python code.

    :returns: Dict with ``reads``, ``writes`` and ``params`` (each a list, in source order).
    """
    found: dict[str, list[str]] = {"reads": [], "writes": [], "params": []}
    for node in calls_in_order(tree):
        names, method, arg = chain(node.func), node.func.attr, literal(node.args[0]) if node.args else None
        receiver = names[:-1]
        if method == "sql" and node.args:
            if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                reads, writes = tables_in_sql(node.args[0].value)
            else:
                reads, writes = [f"<sql: {ast.unparse(node.args[0])}>"], []
            found["reads"] += reads
            found["writes"] += writes
        elif method in READ_SOURCES and (
            "read" in receiver or "readStream" in receiver or receiver == ["spark"]
        ):
            found["reads"].append(arg or "<?>")
        elif method == "forName" and receiver[-1:] == ["DeltaTable"] and len(node.args) > 1:
            found["reads"].append(literal(node.args[1]))
        elif method in WRITE_TARGETS and (
            "write" in receiver
            or "writeStream" in receiver
            or method in ("saveAsTable", "insertInto", "toTable")
        ):
            found["writes"].append(arg or "<?>")
        elif receiver[-2:] == ["dbutils", "widgets"] and method in (
            "get",
            "text",
            "dropdown",
            "combobox",
            "multiselect",
        ):
            found["params"].append(f"widget:{arg}")
        elif method == "add_argument" and arg:
            found["params"].append(f"arg:{arg}")
    return {key: list(dict.fromkeys(values)) for key, values in found.items()}


# --- end of shared helpers ------------------------------------------------------------------------------


def new_columns(tree: ast.AST) -> list[str]:
    """Columns created or renamed by DataFrame code (``withColumn``, ``withColumns``, ``alias``, renames)."""
    columns = []
    for node in calls_in_order(tree):
        method, args = node.func.attr, node.args
        if method in ("withColumn", "alias") and args:
            columns.append(literal(args[0]))
        elif method == "withColumnRenamed" and len(args) == 2:
            columns.append(f"{literal(args[0])} -> {literal(args[1])}")
        elif method == "withColumns" and args and isinstance(args[0], ast.Dict):
            columns += [literal(k) for k in args[0].keys if k is not None]
    return list(dict.fromkeys(c for c in columns if c))


def functions(tree: ast.AST) -> list[str]:
    """Top-level functions with the first line of their docstring, in source order."""
    result = []
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = (ast.get_docstring(node) or "").strip().splitlines()
            result.append(f"{node.name}()" + (f" - {doc[0]}" if doc else ""))
    return result


def analyze(path: Path) -> dict:
    """Data flow of one file.

    :param path: Module or notebook.
    :returns: Dict with ``file``, ``reads``, ``writes``, ``params``, ``steps``, ``new_columns``, ``runs``.
    """
    flow = {
        "file": str(path),
        "reads": [],
        "writes": [],
        "params": [],
        "steps": [],
        "new_columns": [],
        "runs": [],
    }
    for _, kind, source in split_cells(path):
        if kind == "sql":
            reads, writes = tables_in_sql(source)
            flow["reads"] += reads
            flow["writes"] += writes
        elif kind == "run":
            flow["runs"].append(source.strip())
        elif kind == "python":
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                flow["steps"].append(f"<could not parse a cell: {exc.msg}>")
                continue
            io = io_calls(tree)
            for key in ("reads", "writes", "params"):
                flow[key] += io[key]
            flow["steps"] += functions(tree)
            flow["new_columns"] += new_columns(tree)
    return {key: list(dict.fromkeys(v)) if isinstance(v, list) else v for key, v in flow.items()}


def iter_sources(paths: list[Path]):
    for path in paths:
        if path.is_file() and path.suffix in (".py", ".ipynb"):
            yield path
        elif path.is_dir():
            for file in sorted([*path.rglob("*.py"), *path.rglob("*.ipynb")]):
                parts = file.relative_to(path).parts[:-1]
                if not any(p.startswith(".") or p in SKIP_DIRS for p in parts) and file.name != "__init__.py":
                    yield file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    flows = [analyze(p) for p in iter_sources(args.paths)]
    if args.json:
        print(json.dumps(flows, indent=1, ensure_ascii=False))
        return 0
    labels = {
        "reads": "reads",
        "writes": "writes",
        "params": "parameters",
        "runs": "runs (%run)",
        "steps": "functions (in order)",
        "new_columns": "new/renamed columns",
    }
    for flow in flows:
        print(f"== {flow['file']}")
        for key, label in labels.items():
            if flow[key]:
                print(f"  {label}: {', '.join(flow[key])}")
    print(f"\n{len(flows)} file(s) analyzed. <...> = dynamic value, resolve it from the code or ask.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
