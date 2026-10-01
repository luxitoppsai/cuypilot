---
name: python-refactor
description: Refactor EXISTING Python code while preserving its behavior - simplify, remove over-engineering and dead code, split long functions, flatten needless class hierarchies, improve names and structure following KISS, YAGNI and SOLID. Use when the user asks to refactor, clean up, simplify, restructure, untangle or improve existing code. Do NOT use to only review or audit without changing code (use design-review) or to design something new from scratch (use python-design).
---

# Python refactor

Goal: same behavior, less and clearer code. Deleting beats adding.

## Workflow

1. **Understand before touching.** Read the code and its callers. State in one or two sentences what it does and which behavior must stay identical (inputs, outputs, side effects, raised exceptions, public signatures).
2. **Secure a safety net.**
   - If tests exist, run them first and note the baseline.
   - If not, write characterization tests for the public behavior you will touch (happy path + one edge case). For PySpark, use small local DataFrames and compare with `assertDataFrameEqual` (`pyspark.testing`).
   - If tests are impossible right now, say so explicitly and keep each step tiny.
3. **Plan the steps** and show the plan, ordered by value/risk. Typical moves, in order of preference:
   1. Delete: dead code, unused parameters/imports, commented-out code, speculative abstractions, flags nobody sets.
   2. Inline: wrappers that only forward calls, single-use helpers that hide nothing, base classes with one child.
   3. Simplify: nested conditionals to guard clauses, duplicated branches to one, manual loops to comprehensions or built-ins.
   4. Extract: long functions into well-named functions with one responsibility; magic values into named constants.
   5. Restructure: replace inheritance with composition; replace type-switching `if/elif` with dict dispatch or polymorphism when 3+ cases exist.
   6. Rename: names that lie or are vague.
4. **Apply in small, behavior-preserving steps.** Run the tests after each step. Do not mix refactoring with feature changes or bug fixes; if you find a bug, report it separately.
5. **Keep public API stable** unless the user agreed to change it. If a public signature must change, list every caller you updated.
6. **Summarize**: what changed, what was removed (line count before/after is useful), what you deliberately left alone, and any risks or follow-ups.

## PySpark-specific moves

- Replace Python UDFs with built-in `pyspark.sql.functions` when an equivalent exists.
- Replace chains of `withColumn` in loops with a single `select`/`withColumns`.
- Extract transformations into `DataFrame -> DataFrame` functions composed with `.transform()`.
- Remove unnecessary `collect()`, `toPandas()` or `count()` calls used only for debugging.

## Do not

- Introduce new patterns, base classes or layers "for flexibility".
- Reformat unrelated code in the same change.
- Change behavior silently, even if the old behavior looks wrong — flag it instead.
