---
name: functional-docs
description: Write FUNCTIONAL (business-facing) documentation in Spanish for a data pipeline, job, notebook or ML model - purpose, inputs, outputs, business rules, parameters, schedule, data quality, limitations, owners - as a Markdown page for the Sphinx docs (docs/funcional/). Use when the user asks for functional documentation, documentation for business/analysts, or "what does this pipeline/model do" docs. Do NOT use for API docstrings (use sphinx-docstrings or the docs-writer agent) or to set up Sphinx itself (use sphinx-setup).
---

# Functional docs

Goal: a page a business analyst can read to understand **what** a pipeline or model does and **why**, without reading code. Always in **Spanish**.

## Workflow

1. **Extract the facts deterministically first**:

   ```bash
   python .github/skills/functional-docs/scripts/data_flow.py <file-or-folder> [...]
   ```

   It lists tables/paths read and written, parameters (widgets, CLI args), functions in order with their docstring summary, `%run` dependencies and new/renamed columns. Values shown as `<...>` are dynamic (f-strings, variables): resolve them from the code (e.g. default parameter values) or mark them.
2. **Read only what you need** to explain business rules: the transformation functions that create columns, filters and joins reported by the script.
3. **Write the page** at `docs/funcional/<pipeline>.md` using `assets/plantilla_funcional.md` from this skill. Fill the 9 sections in plain business language:
   - translate code into rules ("se excluyen clientes con estado distinto de 'A'"), not into code descriptions ("filter(col('estado') == 'A')");
   - name tables with their full name in backticks and say what they contain.
4. **Never invent.** Purpose, owners, schedule, SLAs and data quality expectations usually are not in the code: ask the user, or leave `[COMPLETAR: ...]` with a hint of what is missing. Do not guess business meaning from a column name alone; mark it `[VERIFICAR]` if unsure.
5. If the Sphinx project exists, add the page to `docs/funcional/index.md` (toctree). If `docs/` does not exist, suggest the `sphinx-setup` skill instead of creating the structure ad hoc.
6. End with a short list of the `[COMPLETAR]` / `[VERIFICAR]` items for the user.
