"""Outline a notebook cell by cell so its logic can be moved into a testable module.

For each cell: kind, functions defined, tables read/written, widgets, display() calls and the variables it
uses from earlier cells (hidden coupling). Works on Databricks .py notebooks and .ipynb.
Read-only, standard library only. Usage::

    python notebook_outline.py NOTEBOOK [--json]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# --- shared helpers: keep identical in functional-docs/scripts/data_flow.py ---------------------

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


def defined_names(tree: ast.AST) -> set[str]:
    """Names a cell defines at top level (assignments, functions, classes, imports)."""
    names = set()
    for node in getattr(tree, "body", []):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names |= {(a.asname or a.name).split(".")[0] for a in node.names}
        else:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    names.add(sub.id)
    return names


def used_names(tree: ast.AST) -> set[str]:
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}


def outline(path: Path) -> list[dict]:
    """Describe every cell of a notebook.

    :param path: Databricks ``.py`` notebook or ``.ipynb``.
    :returns: One dict per cell with ``cell``, ``kind`` and the detected facts.
    """
    known: dict[str, int] = {}  # name -> cell that last defined it
    result = []
    for number, kind, source in split_cells(path):
        info: dict = {"cell": number, "kind": kind}
        if kind == "md":
            info["title"] = next(
                (line.strip("# ").strip() for line in source.splitlines() if line.strip()), ""
            )
        elif kind == "sql":
            info["reads"], info["writes"] = tables_in_sql(source)
        elif kind in ("run", "pip", "sh", "fs"):
            info["command"] = source.strip()
        elif kind == "python":
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                info["error"] = f"could not parse: {exc.msg}"
                result.append(info)
                continue
            io = io_calls(tree)
            info["defines"] = sorted(
                n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
            )
            info["reads"], info["writes"] = io["reads"], io["writes"]
            info["widgets"] = [p.removeprefix("widget:") for p in io["params"] if p.startswith("widget:")]
            info["display"] = sum(
                isinstance(n, ast.Call)
                and getattr(n.func, "id", getattr(n.func, "attr", "")) in ("display", "show")
                for n in ast.walk(tree)
            )
            mine = defined_names(tree)
            info["uses_from_earlier_cells"] = sorted(
                f"{n} (cell {known[n]})" for n in used_names(tree) - mine if n in known
            )
            known.update(dict.fromkeys(mine, number))
        result.append({k: v for k, v in info.items() if v not in ([], 0, "")})
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("notebook", type=Path)
    parser.add_argument("--json", action="store_true", help="Machine-readable output.")
    args = parser.parse_args(argv)

    cells = outline(args.notebook)
    if args.json:
        print(json.dumps(cells, indent=1, ensure_ascii=False))
        return 0
    for info in cells:
        facts = "; ".join(
            f"{k.replace('_', ' ')}: {', '.join(map(str, v)) if isinstance(v, list) else v}"
            for k, v in info.items()
            if k not in ("cell", "kind")
        )
        print(f"cell {info['cell']:>3} [{info['kind']}] {facts}")
    python_cells = sum(c["kind"] == "python" for c in cells)
    print(
        f"\n{len(cells)} cell(s), {python_cells} Python. "
        "'uses from earlier cells' = hidden inputs to turn into parameters."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
