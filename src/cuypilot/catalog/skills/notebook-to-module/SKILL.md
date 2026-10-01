---
name: notebook-to-module
description: Move the logic of a Databricks notebook (.py source format or .ipynb) into an importable, testable Python module - pure DataFrame -> DataFrame functions, explicit parameters instead of widgets and hidden globals, I/O at the edges - leaving the notebook as a thin orchestrator. Use when the user asks to modularize, productionize, clean up or extract code from a notebook, or make notebook code testable. Do NOT use for refactoring code that is already in modules (use python-refactor).
---

# Notebook to module

Goal: same results, but the logic lives in a module with functions you can import and test; the notebook only wires inputs, calls functions and writes outputs.

## Workflow

1. **Outline the notebook first** (do not read it cell by cell):

   ```bash
   python .github/skills/notebook-to-module/scripts/notebook_outline.py <notebook>
   ```

   For each cell it reports the kind (`python`, `sql`, `md`, `run`, `pip`), functions defined, tables read/written, widgets, `display()` calls and **variables used from earlier cells** — the hidden inputs that must become explicit parameters.
2. **Propose the target layout** before moving code, and get the user's OK:
   - module path following the project layout (e.g. `src/<package>/<pipeline>.py`);
   - list of functions with signatures: transformations as `def step(df: DataFrame, ...) -> DataFrame`, reads and writes as separate small functions at the edges;
   - parameters (dates, catalog/schema names, thresholds) that replace widgets and globals;
   - `%run` dependencies → normal imports;
   - `%sql` cells → `spark.sql(query, args={...})` inside a function, or kept in the notebook if they are pure exploration.
3. **Extract one piece at a time**, in dependency order. Keep behavior identical (same filters, joins, column names, types). Remove `display()`/`show()` from the module; the notebook can still display results.
4. **Leave the notebook as an orchestrator**: read widgets → call the module's functions → write outputs. Keep exploratory cells only if the user wants them, under a clear "exploration" heading.
5. **Add tests** for the extracted transformations (use the `pyspark-testing` skill if installed). Add Sphinx docstrings to public functions (`sphinx-docstrings`).
6. **Verify**: run the tests, re-run the outline on the notebook (fewer hidden dependencies, no business logic left), and if possible compare the output of the old and new versions on a small sample.

## Rules

- Do not change business logic while moving it; report suspected bugs separately.
- Do not introduce classes for pipeline steps — plain functions compose better (`df.transform(step)`).
- Never hardcode credentials or environment-specific paths in the module; pass them as parameters.
