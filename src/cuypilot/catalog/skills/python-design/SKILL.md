---
name: python-design
description: Design NEW Python code (a module, class, API, package layout or data pipeline component) applying KISS, YAGNI, pragmatic OOP, SOLID and design patterns only when justified. Use when the user asks to create, design, structure or architect new code, or asks "should this be a class?", "which pattern fits here?". Do NOT use to change existing code (use python-refactor) or to review/audit code without editing it (use design-review).
---

# Python design

Goal: the smallest design that solves today's requirement cleanly and is easy to change tomorrow.

## Workflow

1. **Clarify the requirement.** Restate inputs, outputs and the concrete use cases in one or two sentences. If a requirement is speculative ("might need", "in the future"), leave it out and say so.
2. **Start with functions.** Sketch the solution as plain functions over plain data (`dataclass`, `dict`, `DataFrame`). Only move to classes when a rule below says so.
3. **Decide where classes earn their place.** Introduce a class only if at least one is true:
   - it owns **state + the behavior** that keeps that state consistent;
   - you need **polymorphism** with 2+ real implementations today;
   - it marks a **boundary** with the outside world (API client, repository, file store) that you want to swap in tests.
4. **Check SOLID as a smell detector, not a checklist.**
   - *S*: can you describe each unit's job without "and"?
   - *O*: will the next expected change mean adding code, or editing a growing `if/elif` chain?
   - *L*: do subclasses honor the parent's contract (no surprising `NotImplementedError`)?
   - *I*: do callers depend on methods they never use? Prefer small `Protocol`s.
   - *D*: do high-level policies import low-level details directly where that blocks testing? Inject the dependency (a function or object parameter), not a framework.
5. **Consider a pattern only to solve a problem present now.** Read `references/patterns.md` and prefer the Pythonic alternative listed there before a classic GoF structure.
6. **Present the design** before writing lots of code:
   - module/file layout (as a short tree);
   - public functions/classes with signatures and one-line responsibilities;
   - what you deliberately left out (YAGNI) and when it would become worth adding.
7. **Implement** following the `python-standards` rules: type hints and Sphinx docstrings on public API, validation only at the edges, tests for the logic that matters.

## Red flags to avoid

- Abstract base class with a single implementation.
- `Manager`, `Helper`, `Utils`, `Handler` classes that are bags of unrelated functions.
- Config flags or parameters no caller uses yet.
- Factories/builders for objects with a simple constructor.
- Inheritance used only to share code (use a function or composition).
- Wrapping a library in a class that just forwards calls.

## Data & PySpark notes

- Model transformations as pure functions `DataFrame -> DataFrame` and compose them with `DataFrame.transform`; this keeps them testable with small local DataFrames.
- Keep I/O (reading tables, writing outputs, Spark session creation) at the edges, separate from transformation logic.
