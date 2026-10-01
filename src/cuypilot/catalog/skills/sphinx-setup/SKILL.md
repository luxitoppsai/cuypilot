---
name: sphinx-setup
description: Create or repair the Sphinx documentation project of a Python repo with two sections - technical (API generated from Sphinx/reST docstrings via autodoc + autosummary) and functional (Markdown pages for business via MyST) - using the furo theme, and make it build cleanly with sphinx-build -W. Use when the user asks to set up, configure, fix or build Sphinx docs, or "create the docs folder". Do NOT use to write docstrings (use sphinx-docstrings) or functional content (use functional-docs).
---

# Sphinx setup

Goal: a `docs/` folder that builds without warnings and has a clear split between **funcional** (business) and **técnica** (API).

## Workflow

1. **Inspect first.** Check whether `docs/` exists (`conf.py`, `index.*`), the project layout (`src/<package>` or flat) and the package name(s). If a Sphinx project exists, **repair/extend it** instead of replacing it; never overwrite existing pages.
2. **Create the structure** from this skill's `assets/docs/` (copy the files, then replace the `[...]` and `<...>` placeholders):

   ```
   docs/
     conf.py              # <Nombre del proyecto>, <Equipo>; sys.path for src/ or flat layout
     index.md             # portada
     funcional/index.md   # páginas de negocio (las escribe functional-docs)
     tecnica/index.md     # autosummary recursivo sobre <paquete>
   ```

   - Replace `<paquete>` in `tecnica/index.md` with the importable package name(s), one per line.
   - In `conf.py`, adjust `sys.path` for a flat layout and extend `autodoc_mock_imports` with any heavy dependency the package imports (cluster-only libraries) so the docs build anywhere.
3. **Dependencies** (propose, and run only after the user agrees): add to a `docs` dependency group, e.g.
   `uv add --group docs sphinx myst-parser furo` (or the project's equivalent in `requirements-docs.txt`).
4. **Ignore generated files**: add `docs/_build/` and `docs/tecnica/_autosummary/` to `.gitignore`.
5. **Build and fix until clean**:

   ```bash
   sphinx-build -W --keep-going -b html docs docs/_build/html
   ```

   Typical fixes: docstring reST formatting errors (fix the docstring, see `sphinx-docstrings`), import errors (add to `autodoc_mock_imports` or fix `sys.path`), pages not in any toctree.
6. **Report**: what was created or changed, the build command, and that functional pages go in `docs/funcional/` (suggest `functional-docs`).

## Conventions

- Docstrings in **Sphinx/reST** field format (`:param:`, `:returns:`, `:raises:`); no Napoleon (Google/NumPy styles) unless the project already uses it.
- Functional pages in Spanish, in Markdown (MyST); technical reference generated, never hand-written.
- `intersphinx` is optional (needs internet at build time); enable it only if the build environment has access.
