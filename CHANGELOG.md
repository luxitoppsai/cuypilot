# Changelog

Formato: [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versionado: semver (ver `CONTRIBUTING.md`).

## [0.3.2] - 2026-10-01

### Cambiado
- `graphify` construye el índice al instalarse (`graphify update .`: local, sin LLM); la regla del bloque gestionado explica cómo refrescarlo.
- El wizard explica cómo se usa cada tipo de pieza: las instructions se aplican solas y **no aparecen con `/`**; las skills sí; los agents van en el selector.
- La guía aclara cómo verificar que una instruction se usó (References).
- El wizard muestra los comandos de las herramientas en el resumen y pide **una sola** confirmación (antes preguntaba dos veces).

## [0.3.1] - 2026-10-01

Funciona **solo con pip**: sin uv ni pipx (enmienda a RFC-002).

### Cambiado
- Herramientas: el catálogo declara `package = "nombre==versión"` y cuypilot lo instala con `python -m pip install` en el entorno virtual del proyecto (antes `uv tool install`).
- Los ejecutables de las herramientas se buscan también en el `bin`/`Scripts` del entorno virtual, aunque no esté activado.
- Build con `hatchling` (antes `uv_build`); desarrollo con `pip install -e . --group dev` y `python -m build`.
- CI con `actions/setup-python` + pip.
- README, guía y CONTRIBUTING sin uv. `sphinx-setup` 1.0.1: dependencias de docs con pip.

### Corregido
- pip compila bytecode al instalar el wheel: los `__pycache__` del catálogo ya no se copian al repo del usuario.

## [0.3.0] - 2026-09-30

### CLI
- `cuypilot init`: wizard con banner ASCII, elección de rol (`dev`, `ds`, `mle`, `docs`), herramientas opcionales e instalación guiada; `--role X --yes` para modo no interactivo. `cuypilot` sin argumentos abre el wizard si el repo no tiene piezas.
- Las combinaciones por rol viven en `catalog.toml` (`[roles]`).
- Las herramientas pueden no tener `configure` (herramientas de solo terminal).
- Cancelar con Ctrl+C o sin entrada interactiva termina con un mensaje, sin traceback.

### Piezas nuevas (RFC-003)
- `pyspark-optimize` 1.0.0 + `spark_lint.py` (12 reglas; `.py`, notebooks de Databricks e `.ipynb`).
- `pyspark-testing` 1.0.0 (+ `assets/conftest.py`, `assets/test_example.py`).
- `notebook-to-module` 1.0.0 + `notebook_outline.py`.
- `ml-review` 1.0.0 (scikit-learn, XGBoost, LightGBM, Spark ML, MLflow).
- `sphinx-setup` 1.0.0 (plantillas técnica/funcional, tema `furo`; build `-W` verificado).
- `functional-docs` 1.0.0 + `data_flow.py` + plantilla funcional de 9 secciones en español.
- Herramienta `pyspark-antipattern` 0.4.1 (MIT).

### Corregido
- Docstring con reST inválido en `workspace.py` (lo detectó el build de Sphinx con `-W`).

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
