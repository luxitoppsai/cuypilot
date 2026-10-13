# cuypilot

Catálogo centralizado, versionado y revisado de **skills, agents, instructions y herramientas para
GitHub Copilot en VS Code, OpenCode y Genie Code de Databricks**, pensado para desarrolladores, data scientists y ML engineers que trabajan
con Python y PySpark (Databricks).

Se distribuye como **wheel** con una CLI (`cuypilot`). Cada proyecto instala **solo las piezas que
necesita**, que quedan versionadas en su propio repositorio.

📘 **[Guía de usuario](docs/guia-usuario.md)**: instalación, uso, catálogo completo, solución de problemas.

## Instalación

Requisitos: Python ≥3.11, pip y el asistente que vayas a usar. **No necesita uv ni pipx.**

cuypilot se instala como **dependencia de desarrollo**, en el entorno virtual del proyecto donde lo vas a usar:

```bash
python -m venv .venv                 # si el proyecto aún no tiene uno
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install <ruta>/cuypilot-0.5.1-py3-none-any.whl   # y agrega esa línea a tu requirements-dev.txt
cuypilot --version
```

> ⚠️ No lo pongas en el `requirements.txt` que se instala en el cluster de Databricks.

## Uso rápido

Desde la raíz de tu repo, el wizard te guía en cuatro pasos: rol, selección editable, resumen e instalación.
Primero eliges el asistente. Puedes conservar las sugerencias con Enter o elegir números, `todos` o `ninguno`:

```bash
cuypilot init
# O sin preguntas:
cuypilot init --target opencode --role dev --yes
cuypilot init --target genie --role mle --yes
```

O pieza por pieza:

```bash
cuypilot list                                          # catálogo (* = instalada)
cuypilot add python-standards python-design design-review
cuypilot status                                        # ok | desactualizada | modificada | retirada
git add .github .gitignore && git commit -m "chore: copilot customizations via cuypilot"
```

Sin `--target`, los comandos siguen usando Copilot. Usa `--target opencode` o `--target genie` para
instalar, actualizar y quitar en otro asistente; `--path` elige el proyecto. Cada destino tiene su lockfile.

**[Guía de múltiples asistentes](docs/multiples-asistentes.md)**: formatos, versiones y publicación desde
la terminal hacia Databricks (`cuypilot deploy --workspace-path ...`). En Genie, los agents se adaptan
como skills; las herramientas locales se ofrecen para Copilot y OpenCode.

En Copilot usa `/nombre`; en OpenCode pide la skill por nombre; en Genie usa `@nombre`. Puedes escribir en español.

| Comando | Qué hace |
|---|---|
| `cuypilot init` | Wizard: elige tu rol e instala lo sugerido |
| `cuypilot list` | Muestra el catálogo |
| `cuypilot add <nombre>...` | Instala piezas y sus dependencias (`--dry-run` para ver antes qué haría) |
| `cuypilot status` | Estado de lo instalado |
| `cuypilot update` | Actualiza a la versión del wheel; no pisa tus ediciones |
| `cuypilot remove <nombre>...` | Quita piezas |
| `cuypilot deploy --workspace-path <carpeta>` | Publica la instalación Genie usando la CLI de Databricks |

## Catálogo

| Piezas | Para qué |
|---|---|
| `python-standards`, `python-design`, `python-refactor`, `design-review` | Criterios del equipo: KISS, YAGNI, OOP con criterio, SOLID y patrones, para diseñar, refactorizar y revisar |
| `sphinx-docstrings`, `docs-writer` | Documentación técnica con Sphinx |
| `improve-prompt` | `/improve-prompt <pedido>`: mejora tu prompt antes de ejecutarlo |
| `pyspark-optimize`, `pyspark-testing`, `notebook-to-module` | PySpark en Databricks (15.4 LTS+): optimizar sin cambiar resultados, testear transformaciones, modularizar notebooks |
| `ml-review` | Revisión de ML: fuga de datos, splits, semillas, métricas, MLflow |
| `sphinx-setup`, `functional-docs` | Sphinx con secciones técnica y funcional; documentación funcional en español |
| `ponytail`, `ponytail-audit`, `ponytail-debt` | Menos código: solución mínima y auditoría de sobreingeniería ([ponytail](https://github.com/DietrichGebert/ponytail)) |
| `systematic-debugging`, `test-driven-development`, `verification-before-completion` | Metodología de [superpowers](https://github.com/obra/superpowers) |
| `spark-performance` | Agente de rendimiento PySpark ([awesome-copilot](https://github.com/github/awesome-copilot)) |
| `graphify`, `pyspark-antipattern` | Herramientas opcionales: grafo del repo ([graphify](https://github.com/Graphify-Labs/graphify)) y linter de PySpark ([pyspark-antipattern](https://github.com/skanderboudawara/pyspark-antipattern)) |

Detalle, ejemplos y combinaciones por rol: **[guía de usuario](docs/guia-usuario.md#4-qué-hay-en-el-catálogo)**.

## Desarrollo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e . --group dev   # pip ≥25.1; con un pip anterior: pip install -e . pytest ruff build
pytest                         # incluye la validación del catálogo, licencias y scripts
ruff check .
python -m build                # genera dist/cuypilot-X.Y.Z-py3-none-any.whl
```

- Contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Gobernanza del equipo: [lineamientos](docs/gobernanza.md), [responsables de revisión](.github/CODEOWNERS), [evaluación de los tres escenarios](docs/research/evaluacion-gobernanza-analytics.md) y [RFC-006 propuesto](docs/rfc/RFC-006-gobernanza-analytics.md).
- Cambios por versión: [`CHANGELOG.md`](CHANGELOG.md)
- Contratos: [`RFC.md`](RFC.md) (RFC-001, base) · [`RFC-002`](docs/rfc/RFC-002-integraciones-terceros.md) (scripts y terceros) · [`RFC-003`](docs/rfc/RFC-003-contenido-dominio.md) (PySpark, ML, docs)
- Investigación: [`docs/research/estado-del-arte.md`](docs/research/estado-del-arte.md)
- Múltiples asistentes: [`RFC-005`](docs/rfc/RFC-005-multiples-asistentes.md).
- Decisiones de seguridad y wizard: [`RFC-004`](docs/rfc/RFC-004-seguridad-wizard.md).
- Segundo cerebro: `luxitopp-vault/10-Projects/cuypilot/cuypilot.md` (ver [`PROJECT.md`](PROJECT.md))
