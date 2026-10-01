---
name: design-review
description: Review or audit Python code WITHOUT modifying it - find over-engineering (what to delete), KISS/YAGNI violations, SOLID problems, tight coupling, needless defensive code and unclear naming, and return prioritized findings. Use when the user asks to review, audit, evaluate, critique or give feedback on code, a module, a PR or a design. Do NOT edit files; if the user wants the changes applied, that is python-refactor.
---

# Design review

Goal: a short, prioritized list of findings the author can act on. Do not edit files.

## Workflow

1. **Scope.** Identify what is being reviewed (files, diff, module) and its purpose. If reviewing a diff, focus on the changed code and its direct impact.
2. **Read for intent first**, then evaluate against these lenses, in this order:
   1. **Over-engineering (what to delete):** abstractions with one implementation, unused parameters/flags/config, wrappers that only forward, layers with no logic, premature generalization.
   2. **Simplicity (KISS):** convoluted control flow, reimplemented standard-library features, clever code where plain code works.
   3. **Responsibilities (SOLID):** units that do several jobs, growing `if/elif` type switches, subclasses that break the parent contract, fat interfaces, hard-wired dependencies that block testing.
   4. **Coupling & boundaries:** I/O mixed with business logic, hidden global state, circular imports.
   5. **Robustness at the edges:** missing validation of external input; conversely, defensive `try/except` deep inside trusted code, bare `except`, swallowed errors.
   6. **Readability:** misleading names, long functions, missing Sphinx docstrings on public API, comments that restate code.
   7. **PySpark (if present):** Python UDFs replaceable by built-ins, `collect()`/`toPandas()` on large data, loops of `withColumn`, transformations not isolated from I/O.
3. **Verify each finding** against the actual code before reporting it; drop anything speculative.
4. **Report** using the format below. Lead with the most impactful items; at most ~10 findings.

## Output format

```
## Summary
<2-3 sentences: overall assessment and the single most important change>

## Findings
1. [High|Medium|Low] <file>:<line> — <problem in one sentence>
   Why it matters: <consequence>
   Suggestion: <concrete change, ideally "delete X" or "replace X with Y">

## What is good
<1-3 things worth keeping, briefly>
```

Severity guide: **High** = causes bugs, blocks testing or makes change risky; **Medium** = unnecessary complexity with real maintenance cost; **Low** = readability/polish.
