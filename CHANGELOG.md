# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado: semver (ver `CONTRIBUTING.md`).

## [0.2.0] - 2026-09-30

### CLI
- Tipo de pieza `tool`: ejecuta el instalador oficial con confirmación (`--yes` la omite), sin shell y con versión aprobada; `add --dry-run`; `status` informa `no instalada`.
- `remove` avisa con notas (por ejemplo, que el programa de una herramienta sigue instalado).
- **Fix:** el bloque gestionado empieza en un encabezado H2 con el marcador en la misma línea. Antes, herramientas que borran su sección "hasta el siguiente `##`" (graphify) se llevaban el marcador de inicio. El formato de 0.1.0 se migra solo.

### Piezas
- Scripts deterministas (stdlib, solo lectura):
  - `sphinx-docstrings` 1.1.0: `docstring_audit.py`.
  - `design-review` 1.1.0: `code_metrics.py`; `python-refactor` 1.1.0 lo usa si está instalado.
  - `improve-prompt` 1.1.0: `workspace_context.py`.
- Nuevas de terceros:
  - `ponytail`, `ponytail-audit`, `ponytail-debt` (ponytail, MIT).
  - `systematic-debugging` (adaptada), `test-driven-development`, `verification-before-completion` (superpowers, MIT).
  - `spark-performance` (awesome-copilot, MIT, adaptada).
- Nueva herramienta: `graphify` 0.9.73 (Apache-2.0), con la regla `--code-only` en el bloque gestionado.

### Gobernanza
- El CI valida `upstream` (commit sha, licencia permitida, texto de licencia), las herramientas (sin shell, versión fijada) y las reglas de los scripts.
- Guía de usuario en `docs/guia-usuario.md`.

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
