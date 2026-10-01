---
name: pyspark-optimize
description: Find and fix PySpark performance anti-patterns in CODE (Python UDFs, collect/toPandas, withColumn or actions inside loops, .rdd, coalesce(1), unreleased cache, cross joins, SQL built with f-strings, inferSchema, driver-side row loops) and rewrite them Spark-natively without changing results; also Databricks/Delta guidance (joins, skew, AQE, liquid clustering). Use when the user asks to optimize, speed up or fix slow PySpark/Databricks code or notebooks. Do NOT use to diagnose a run from Spark UI metrics or explain() plans (use the spark-performance agent), nor for general non-Spark refactors (use python-refactor).
---

# PySpark optimize

Goal: faster, cheaper Spark code that returns **exactly the same result**. Fix one anti-pattern at a time.

Assume Databricks Runtime 15.4 LTS or newer (Spark ≥3.5, Python ≥3.11) unless the project's dependencies (`pyspark`, `databricks-connect`) say otherwise. On Spark 4.x, remember ANSI SQL mode is on by default (invalid casts raise instead of returning null).

## Workflow

1. **Scan first, do not read everything.** Run the linter with the project's Python on the target path (works with `.py` modules, Databricks `.py` notebooks and `.ipynb`):

   ```bash
   python .github/skills/pyspark-optimize/scripts/spark_lint.py <path>
   ```

   If the `pyspark-antipattern` tool is installed (`pyspark-antipattern --version` works), also run it for extra rules, without colors: `NO_COLOR=1 pyspark-antipattern check <path>` (PowerShell: `$env:NO_COLOR=1; pyspark-antipattern check <path>`). Its codes differ from `spark_lint.py` (e.g. `L003`, `D001`); treat duplicates as one finding.
2. **Prioritize** HIGH findings, then MEDIUM. Read only the reported locations and their direct context.
3. **Confirm before changing** anything whose impact depends on data volume (`collect()`, `toPandas()`, broadcast): ask the user or look for evidence (table sizes, comments, `limit`).
4. **Secure the result.** If there are tests for the transformation, run them before and after. If not, propose a small test first (see the `pyspark-testing` skill if installed). Never change semantics silently: null handling, duplicates, ordering and data types must stay identical.
5. **Rewrite one rule at a time**, using the fixes below. Re-run the linter to confirm the finding is gone.
6. **Summarize**: what changed, expected impact (less shuffle, no driver collection…), and what needs runtime evidence to confirm (suggest the `spark-performance` agent with `df.explain("formatted")` or Spark UI metrics).

## Fixes by rule

| Code | Fix |
|---|---|
| SP001 Python UDF | Use `pyspark.sql.functions` (`F.when`, `F.regexp_replace`, `F.transform`, `F.date_format`…). If no built-in exists, use a vectorized `@pandas_udf`. Keep row-wise Python UDFs only as last resort. |
| SP002 collect/toPandas | Aggregate or `limit()` in Spark first; write results to a table instead of collecting; `toPandas()` only on small, already-reduced data. |
| SP003 withColumn in loop | Build all expressions and apply once: `df.withColumns({name: expr, ...})` or a single `select`. |
| SP004 action in loop | Compute all metrics in one job (`agg` with several expressions, or `groupBy` over the loop key) instead of one action per iteration. |
| SP005 .rdd | Use DataFrame functions; for per-group Python logic use `groupBy().applyInPandas()`. |
| SP006 repartition(1)/coalesce(1) | Let Spark write several files; if one file is truly required, do it only for small outputs. |
| SP007 cache without unpersist | Cache only DataFrames reused by 2+ actions; `unpersist()` when done. |
| SP008 cross join | Replace with an equi-join if a key exists; otherwise confirm both sides are small. |
| SP009 SQL with string formatting | `spark.sql("... WHERE id = :id", args={"id": value})`. For identifiers (table names), validate against an allow-list. |
| SP010 display/show in module | Remove; return the DataFrame and let the caller decide. |
| SP011 inferSchema | Declare a `StructType` or DDL string schema: `spark.read.schema("id INT, name STRING")`. |
| SP012 row loop on driver | Express the per-row logic as column expressions; for side effects per row use `foreachPartition`. |

## Databricks / Delta guidance (when relevant)

- **Joins:** broadcast the small side explicitly (`F.broadcast(small_df)`) when it is clearly small (< ~100 MB); join on columns with matching types; filter and select columns **before** joining.
- **Skew:** with AQE (on by default) skew joins are split automatically; if one key dominates, consider salting or handling that key separately.
- **Pruning:** filter on clustering/partition columns early; avoid wrapping filter columns in functions (`F.year(col) == 2024` prevents pruning; use a range on `col`).
- **Layout of new Delta tables:** prefer **liquid clustering** (`CLUSTER BY`) over partitioning and ZORDER; keep partitioning only for very large tables with a low-cardinality filter column.
- **Small files:** avoid many tiny writes; let `OPTIMIZE` / predictive optimization compact them.
- **Caching:** on Databricks the disk cache often makes `.cache()` unnecessary for repeated reads of Delta tables.
- **Photon:** built-in functions run in Photon; Python UDFs do not — another reason for SP001.
