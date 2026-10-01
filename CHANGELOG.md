# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado: semver (ver `CONTRIBUTING.md`).

## [0.1.0] - 2026-09-30

### CLI
- `cuypilot list | add | remove | status | update`, lockfile `.github/cuypilot.lock.json` con hashes y bloque gestionado en `.github/copilot-instructions.md`.

### Piezas
- `python-standards` 1.0.0 (instruction): estándares base para `.py`.
- `python-design` 1.0.0 (skill): diseño de código nuevo, SOLID y patrones con criterio.
- `python-refactor` 1.0.0 (skill): refactor que preserva el comportamiento.
- `design-review` 1.0.0 (skill): revisión sin edición, con hallazgos priorizados.
- `sphinx-docstrings` 1.0.0 (skill): docstrings Sphinx (reST).
- `docs-writer` 1.0.0 (agent): documenta la API pública; requiere `sphinx-docstrings`.
- `improve-prompt` 1.0.0 (skill, solo manual): mejora un pedido antes de ejecutarlo.
