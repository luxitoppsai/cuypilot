# cuypilot

Catálogo centralizado, versionado y revisado de **skills, agents, instructions y herramientas para
GitHub Copilot en VS Code**, pensado para desarrolladores, data scientists y ML engineers que trabajan
con Python y PySpark (Databricks).

Se distribuye como **wheel** con una CLI (`cuypilot`). Cada proyecto instala **solo las piezas que
necesita**, que quedan versionadas en su propio repositorio.

📘 **[Guía de usuario](docs/guia-usuario.md)**: instalación, uso, catálogo completo, solución de problemas.

## Instalación

Requisitos: Python ≥3.11 y VS Code con GitHub Copilot Chat.

cuypilot se instala como **dependencia de desarrollo** del proyecto donde lo vas a usar:

```bash
# con uv (recomendado)
uv add --dev <ruta>/cuypilot-0.2.0-py3-none-any.whl

# o con pip (en tu requirements-dev.txt)
pip install <ruta>/cuypilot-0.2.0-py3-none-any.whl

cuypilot --version
```

> ⚠️ No lo pongas en el `requirements.txt` que se instala en el cluster de Databricks.

## Uso rápido

Desde la raíz de tu repo:

```bash
cuypilot list                                          # catálogo (* = instalada)
cuypilot add python-standards python-design design-review
cuypilot status                                        # ok | desactualizada | modificada | retirada
git add .github .gitignore && git commit -m "chore: copilot customizations via cuypilot"
```

Después, en Copilot Chat, escribe `/` para ver las skills instaladas. Puedes escribirle en español.

| Comando | Qué hace |
|---|---|
| `cuypilot list` | Muestra el catálogo |
| `cuypilot add <nombre>...` | Instala piezas y sus dependencias (`--dry-run` para ver antes qué haría) |
| `cuypilot status` | Estado de lo instalado |
| `cuypilot update` | Actualiza a la versión del wheel; no pisa tus ediciones |
| `cuypilot remove <nombre>...` | Quita piezas |

## Catálogo

| Piezas | Para qué |
|---|---|
| `python-standards`, `python-design`, `python-refactor`, `design-review` | Criterios del equipo: KISS, YAGNI, OOP con criterio, SOLID y patrones, para diseñar, refactorizar y revisar |
| `sphinx-docstrings`, `docs-writer` | Documentación técnica con Sphinx |
| `improve-prompt` | `/improve-prompt <pedido>`: mejora tu prompt antes de ejecutarlo |
| `ponytail`, `ponytail-audit`, `ponytail-debt` | Menos código: solución mínima y auditoría de sobreingeniería ([ponytail](https://github.com/DietrichGebert/ponytail)) |
| `systematic-debugging`, `test-driven-development`, `verification-before-completion` | Metodología de [superpowers](https://github.com/obra/superpowers) |
| `spark-performance` | Agente de rendimiento PySpark ([awesome-copilot](https://github.com/github/awesome-copilot)) |
| `graphify` | Herramienta: grafo de conocimiento del repo ([graphify](https://github.com/Graphify-Labs/graphify)) |

Detalle, ejemplos y combinaciones por rol: **[guía de usuario](docs/guia-usuario.md#4-qué-hay-en-el-catálogo)**.

## Desarrollo

```bash
uv sync
uv run pytest        # incluye la validación del catálogo, licencias y scripts
uv run ruff check .
uv build             # genera dist/cuypilot-X.Y.Z-py3-none-any.whl
```

- Contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Cambios por versión: [`CHANGELOG.md`](CHANGELOG.md)
- Contratos: [`RFC.md`](RFC.md) (RFC-001, base) · [`docs/rfc/RFC-002-integraciones-terceros.md`](docs/rfc/RFC-002-integraciones-terceros.md) (scripts y terceros)
- Investigación: [`docs/research/estado-del-arte.md`](docs/research/estado-del-arte.md)
- Segundo cerebro: `luxitopp-vault/10-Projects/cuypilot/cuypilot.md` (ver [`PROJECT.md`](PROJECT.md))
