---
name: sphinx-docstrings
description: Write, complete or fix Sphinx (reStructuredText) docstrings in Python code - modules, classes, public functions and methods - using :param:, :returns:, :raises: fields, ready for sphinx autodoc. Use when the user asks to document Python code, add or fix docstrings, or prepare code for Sphinx API documentation.
---

# Sphinx docstrings

Goal: accurate reST docstrings that Sphinx `autodoc` renders well and that describe behavior, not implementation.

## Scope

- Document: modules, public classes, public functions and methods (names without a leading `_`).
- Skip private helpers unless the user asks or their behavior is non-obvious.
- Never change code behavior or signatures while documenting.

## Format

```python
"""Short summary in one line, imperative mood, ending with a period.

Optional longer description: what it does and why, assumptions, side effects.

:param name: What the parameter means (units, allowed values). Do not repeat the type
    if the signature has type hints.
:param other: ...
:returns: What is returned and in which situations.
:raises ValueError: When and why it is raised.
"""
```

Rules:
- One-line summary first, blank line, then details.
- Rely on type hints for types; add `:type:`/`:rtype:` only if the code has no type hints.
- Use ``double backticks`` for code literals and `:class:`/`:func:` roles for cross-references (e.g. ``:class:`pandas.DataFrame```).
- Document only exceptions the function raises intentionally.
- For generators use `:yields:`.
- Class docstrings describe the purpose and the constructor parameters (`:param:` fields in the class docstring).
- Module docstrings: one line on what the module provides.
- For PySpark functions, document expected input columns and the columns added/removed in the output.
- Keep the language of existing docstrings in the project; default to English.

## Workflow

1. Read the code and its callers to understand real behavior (do not guess from names).
2. Add or fix docstrings; keep existing correct content.
3. If something is unclear (e.g. a parameter's meaning), write the best accurate description you can and list the uncertainty for the user.
