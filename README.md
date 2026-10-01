# cuypilot

Catálogo centralizado y versionado de **skills, agents e instructions para GitHub Copilot en VS Code**,
para desarrolladores, data scientists y ML engineers que trabajan con Python y PySpark (Databricks).

Se distribuye como **wheel** con una **CLI** (`cuypilot`) que instala en el workspace de cada proyecto
solo las piezas que necesita. Los archivos instalados se commitean en el repo del proyecto, así todo el
equipo los tiene, aunque no tenga instalada la CLI.

## Instalación (dependencia de desarrollo)

```bash
uv add --dev <ruta>/cuypilot-0.1.0-py3-none-any.whl
# o con pip, en requirements-dev.txt:
pip install <ruta>/cuypilot-0.1.0-py3-none-any.whl
```

> Nunca en el `requirements.txt` que se instala en el cluster de Databricks. Requiere Python ≥3.11.

## Uso

Desde la raíz del proyecto:

```bash
cuypilot list                         # catálogo disponible (* = instalada)
cuypilot add python-standards python-design design-review
cuypilot status                       # ok | desactualizada | modificada | retirada
cuypilot update                       # actualiza a la versión del wheel (no pisa ediciones locales)
cuypilot remove design-review
git add .github && git commit -m "chore: copilot customizations via cuypilot"
```

| Pieza | Tipo | Para qué |
|---|---|---|
| `python-standards` | instruction | Reglas base en todo `.py`: KISS, YAGNI, OOP con criterio, validar en los bordes, docstrings Sphinx |
| `python-design` | skill | Diseñar código nuevo: ¿función o clase?, SOLID, patrones solo si se justifican |
| `python-refactor` | skill | Refactorizar sin cambiar el comportamiento: borrar antes que agregar |
| `design-review` | skill | Revisar código sin editarlo, con hallazgos priorizados |
| `sphinx-docstrings` | skill | Docstrings Sphinx (reST) |
| `docs-writer` | agent | Documenta la API pública de un paquete (instala también `sphinx-docstrings`) |
| `improve-prompt` | skill | `/improve-prompt <pedido>`: convierte un pedido vago en un prompt completo |

Qué hace la CLI en tu repo:
- copia las piezas a `.github/skills/`, `.github/agents/` y `.github/instructions/`;
- registra versión y hashes en `.github/cuypilot.lock.json`;
- mantiene un bloque delimitado `<!-- cuypilot:start/end -->` en `.github/copilot-instructions.md`, sin tocar el resto del archivo.

Pregunta a Copilot en español; responde en tu idioma.

## Desarrollo

```bash
uv sync
uv run pytest        # incluye la validación del catálogo
uv run ruff check .
uv build             # genera dist/cuypilot-X.Y.Z-py3-none-any.whl
```

- Contribuir: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- Contratos: [`RFC.md`](RFC.md) (RFC-001 base, aceptado) · [`docs/rfc/RFC-002-integraciones-terceros.md`](docs/rfc/RFC-002-integraciones-terceros.md) (borrador)
- Investigación: [`docs/research/estado-del-arte.md`](docs/research/estado-del-arte.md)
- Segundo cerebro: `luxitopp-vault/10-Projects/cuypilot/cuypilot.md` (ver [`PROJECT.md`](PROJECT.md))
