# cuypilot

Catálogo versionado y revisado de **skills, agents, instructions y herramientas** para asistentes de
programación con IA: **GitHub Copilot en VS Code**, **OpenCode** y **Genie Code de Databricks**. Está
pensado para desarrolladores, data scientists y ML engineers que trabajan con Python y PySpark en Databricks.

Versión preparada: **0.6.0**, pendiente de publicación. El flujo con manifiesto se describe en
[instalación reproducible y CI](docs/flujo-reproducible.md).

Se distribuye como un **wheel de Python** con una CLI (`cuypilot`). Cada proyecto instala solo las piezas
que necesita; los archivos quedan en su propio repositorio, versionados con Git.

## Cómo funciona

1. El catálogo vive dentro del wheel (`src/cuypilot/catalog/`) y se versiona con él.
2. En tu proyecto instalas el wheel y ejecutas `cuypilot init` (o `cuypilot add <pieza>`).
3. La CLI copia las piezas a las carpetas del asistente elegido (`.github/`, `.opencode/` o `.assistant/`)
   y registra en un lockfile qué instaló, en qué versión y con qué hash.
4. Haces commit de lo instalado: queda constancia de qué piezas usa el proyecto y todo el equipo las recibe.
5. Para actualizar, instalas un wheel nuevo y ejecutas `cuypilot update`. Las piezas que editaste a mano no se pisan.
6. `init` declara la selección en `cuypilot.toml`; `install` la reproduce y `install --frozen` verifica deriva en CI.

## Instalación

Requisitos: Python 3.11 o superior y pip. No necesita uv ni pipx.

cuypilot es una **dependencia de desarrollo**: se instala en el entorno virtual del proyecto donde lo vas a usar.
Cada versión publicada deja su wheel y un archivo `SHA256SUMS` como archivos de su **Release** en GitHub
(pestaña *Releases* de este repositorio). Descárgalos a una carpeta; esa carpeta es `<ruta-del-wheel>`:

```bash
gh release download v0.5.1 --pattern '*' --dir <ruta-del-wheel>    # o desde la página de la Release
```

```bash
python -m venv .venv                 # si el proyecto aún no tiene uno
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install <ruta-del-wheel>/cuypilot-0.5.1-py3-none-any.whl
cuypilot --version
```

Para comprobar la integridad antes de instalar: `cd <ruta-del-wheel> && shasum -a 256 -c SHA256SUMS`
(en Linux, `sha256sum -c SHA256SUMS`).

Agrega esa misma línea a `requirements-dev.txt` para que el resto del equipo instale la misma versión.
No lo pongas en el `requirements.txt` que se instala en el cluster de Databricks.

## Uso rápido

Desde la raíz de tu repositorio, el wizard pregunta el asistente, tu rol y qué piezas instalar, muestra un
resumen y pide una confirmación antes de cambiar nada:

```bash
cuypilot init
cuypilot init --target opencode --role dev --yes     # sin preguntas
```

O pieza por pieza:

```bash
cuypilot list                                        # catálogo; * marca lo instalado
cuypilot add python-standards python-design design-review
cuypilot status                                      # ok | desactualizada | modificada | retirada
git add .github cuypilot.toml && git commit -m "chore: piezas de cuypilot"
```

Sin `--target`, se usan los destinos del manifiesto o se detectan los existentes; sin señales, Copilot.
`--path` elige el proyecto. Cada destino tiene su propio lockfile y los tres pueden convivir.
Con manifiesto, `add/remove` cambian la selección común de todos sus destinos.

| Comando | Qué hace |
|---|---|
| `cuypilot init [--role dev\|ds\|mle\|docs] [--yes]` | Wizard: asistente, rol, selección editable, resumen e instalación |
| `cuypilot list [--type skill\|agent\|instruction\|tool]` | Muestra el catálogo |
| `cuypilot add <nombre>... [--dry-run]` | Instala piezas y sus dependencias |
| `cuypilot status` | Estado de lo instalado |
| `cuypilot update [<nombre>...] [--dry-run]` | Actualiza o muestra el plan |
| `cuypilot remove <nombre>...` | Quita piezas |
| `cuypilot install [--frozen]` | Reproduce el manifiesto o verifica sin escribir |
| `cuypilot audit --ci` | Verifica integridad de archivos, locks y bloques |
| `cuypilot outdated` / `cuypilot why <nombre>` | Consulta actualizaciones y dependencias |
| `cuypilot deploy --workspace-path <carpeta>` | Publica la instalación de Genie en un workspace de Databricks |

En Copilot invoca las skills con `/nombre`; en OpenCode pídelas por nombre; en Genie usa `@nombre`.
Puedes escribirle al asistente en español.

## Catálogo

| Piezas | Para qué |
|---|---|
| `python-standards`, `python-design`, `python-refactor`, `design-review` | Criterios del equipo (KISS, YAGNI, OOP con criterio, SOLID, patrones) para diseñar, refactorizar y revisar |
| `sphinx-docstrings`, `docs-writer` | Docstrings Sphinx y documentación técnica de la API |
| `improve-prompt` | `/improve-prompt <pedido>`: convierte un pedido vago en un prompt completo, sin ejecutarlo |
| `pyspark-optimize`, `pyspark-testing`, `notebook-to-module` | PySpark en Databricks (15.4 LTS o superior): optimizar sin cambiar resultados, testear transformaciones, modularizar notebooks |
| `ml-review` | Revisión de ML: fuga de datos, splits, semillas, métricas, MLflow |
| `sphinx-setup`, `functional-docs` | Sphinx con secciones técnica y funcional; documentación funcional en español |
| `ponytail`, `ponytail-audit`, `ponytail-debt` | Código mínimo y auditoría de sobreingeniería ([ponytail](https://github.com/DietrichGebert/ponytail)) |
| `systematic-debugging`, `test-driven-development`, `verification-before-completion` | Metodología de [superpowers](https://github.com/obra/superpowers) |
| `spark-performance` | Agente de rendimiento PySpark ([awesome-copilot](https://github.com/github/awesome-copilot)) |
| `graphify`, `pyspark-antipattern` | Herramientas opcionales: grafo del repo ([graphify](https://github.com/Graphify-Labs/graphify)) y linter de PySpark ([pyspark-antipattern](https://github.com/skanderboudawara/pyspark-antipattern)) |

Las piezas de terceros están fijadas a un commit revisado y conservan su licencia. Detalle, ejemplos y
combinaciones por rol: [guía de usuario](docs/guia-usuario.md#4-qué-hay-en-el-catálogo).

## Documentación

- [Guía de usuario](docs/guia-usuario.md): instalación, uso, catálogo, herramientas, scripts y solución de problemas.
- [Varios asistentes](docs/multiples-asistentes.md): qué instala cada destino, versiones, y publicación en Genie Code.
- [Flujo reproducible](docs/flujo-reproducible.md): manifiesto, migración, frozen y workflow para consumidores.
- [Cómo trabajamos](docs/gobernanza.md): roles, uso diario, revisión de aportes, publicación y mantenimiento.
- [Contribuir](CONTRIBUTING.md): cómo agregar o modificar piezas, scripts, terceros y herramientas.
- [Cambios por versión](CHANGELOG.md).

## Desarrollo

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e . --group dev   # pip ≥25.1; con uno anterior: pip install -e . pytest ruff build
pytest                         # incluye la validación del catálogo, licencias y scripts
ruff check . && ruff format --check .
python -m build                # genera dist/cuypilot-X.Y.Z-py3-none-any.whl
```

El CI configura pruebas con Python 3.11–3.14 en Ubuntu y construye sdist/wheel también en PR.
Comprueba el wheel en venv limpio con Ubuntu 3.11–3.14 y Windows 3.11/3.14 para los tres destinos.
Al publicar un tag `vX.Y.Z`, crea la Release con el wheel y su `SHA256SUMS` después de esas comprobaciones
(ver [CONTRIBUTING](CONTRIBUTING.md#versionado)). Las versiones anteriores permanecen en sus Releases.
