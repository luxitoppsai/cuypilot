---
name: pyspark-testing
description: Write fast pytest unit tests for PySpark transformations - local SparkSession fixture, tiny DataFrames built in the test, assertDataFrameEqual, edge cases (nulls, duplicates, empty input), and how to make notebook or job code testable by isolating I/O. Use when the user asks to test PySpark/Databricks code, add tests for a transformation, or set up Spark tests in a project. Do NOT use for non-Spark tests (use test-driven-development) or to optimize Spark code (use pyspark-optimize).
---

# PySpark testing

Goal: unit tests for Spark transformations that run in seconds on a laptop or in CI, without a cluster.

## 1. Make the code testable (if it is not)

- One transformation = one function `DataFrame -> DataFrame` (plus plain parameters). No reads, writes, `display()` or widgets inside.
- Reading tables and writing outputs stays at the edges (job entry point / notebook), so tests never touch Unity Catalog.
- If logic lives in a notebook, extract it first (see the `notebook-to-module` skill if installed).

## 2. Set up the fixture once

If the project has no Spark fixture yet, copy `assets/conftest.py` from this skill to `tests/conftest.py` (or merge it into the existing one). It creates **one** local `SparkSession` per test session (`local[1]`, UI off, 1 shuffle partition) — fast and deterministic.

Requirements: `pyspark` in the dev dependencies matching the cluster's Spark version (Databricks Runtime 15.4 LTS → `pyspark==3.5.*`) and a Java runtime (JDK 17) on the machine.

> **Projects that use `databricks-connect`**: it replaces `pyspark` in the environment and has no local engine. Options: (a) run unit tests in a separate environment/dependency group with plain `pyspark`, or (b) use `DatabricksSession` against serverless/a dev cluster (slower, costs money, needs credentials). Recommend (a) for unit tests; ask the user before choosing.

## 3. Write the tests

Follow `assets/test_example.py`:

- Build input and expected DataFrames **inside the test** with 3–10 rows and an explicit schema (DDL string: `"id INT, amount DOUBLE"`).
- Compare with `from pyspark.testing import assertDataFrameEqual` (Spark ≥3.5). It ignores row order by default; pass `checkRowOrder=True` only when order matters.
- Cover, for each transformation: the normal case, **nulls**, **duplicates**, **empty input**, and boundary values (dates at month end, zero/negative amounts).
- One behavior per test; name tests after the business rule (`test_discount_not_applied_to_inactive_clients`).
- Use `pytest.mark.parametrize` for rule tables instead of copy-pasted tests.
- Do not assert on `count()` alone — compare full content.
- Keep Spark tests out of tight loops; the session fixture is session-scoped on purpose.

## 4. Run

```bash
pytest -q tests/
```

If the user has no Java, say so explicitly and provide the install hint for their OS instead of skipping silently.
