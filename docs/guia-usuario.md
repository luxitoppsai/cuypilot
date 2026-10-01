# Guía de usuario de cuypilot

cuypilot instala en tu proyecto **skills, agents, instructions y herramientas para GitHub Copilot en
VS Code**, elegidas y revisadas por el equipo. Esta guía explica cómo instalarlo, cómo usarlo en el día
a día y qué cambia en tu repositorio.

**Contenido**

1. [Requisitos](#1-requisitos)
2. [Instalación](#2-instalación)
3. [Primeros pasos (5 minutos)](#3-primeros-pasos-5-minutos)
4. [Qué hay en el catálogo](#4-qué-hay-en-el-catálogo)
5. [Combinaciones sugeridas por rol](#5-combinaciones-sugeridas-por-rol)
6. [Referencia de comandos](#6-referencia-de-comandos)
7. [Qué cambia en tu repositorio](#7-qué-cambia-en-tu-repositorio)
8. [Herramientas externas (graphify, pyspark-antipattern)](#8-herramientas-externas)
9. [Scripts dentro de las skills](#9-scripts-dentro-de-las-skills)
10. [Actualizar cuypilot](#10-actualizar-cuypilot)
11. [Solución de problemas](#11-solución-de-problemas)
12. [Seguridad y datos](#12-seguridad-y-datos)
13. [Preguntas frecuentes](#13-preguntas-frecuentes)

---

## 1. Requisitos

| Necesitas | Para qué |
|---|---|
| Python **3.11 o superior** | Ejecutar la CLI `cuypilot` y los scripts de las skills |
| VS Code con **GitHub Copilot Chat** | Usar lo que instala cuypilot |
| `uv` (recomendado) o `pip` | Instalar el wheel |
| `uv` | Solo si vas a instalar las herramientas `graphify` o `pyspark-antipattern` |
| Java (JDK 17) | Solo para correr tests de PySpark en tu máquina (`pyspark-testing`) |

Las skills de PySpark asumen **Databricks Runtime 15.4 LTS o superior** (Spark ≥3.5, Python ≥3.11).

## 2. Instalación

cuypilot se instala como **dependencia de desarrollo** del proyecto donde lo vas a usar. El wheel
está disponible en `<ruta>`.

**Con uv (recomendado):**

```bash
uv add --dev <ruta>/cuypilot-0.3.0-py3-none-any.whl
```

**Con pip:** agrega la ruta del wheel a tu `requirements-dev.txt` e instálalo:

```bash
pip install <ruta>/cuypilot-0.3.0-py3-none-any.whl
```

Comprueba que quedó instalado:

```bash
cuypilot --version      # con uv: uv run cuypilot --version
```

> ⚠️ **Nunca** lo pongas en el `requirements.txt` que se instala en el cluster de Databricks: es una
> herramienta para tu máquina de desarrollo, no para producción.

> Si usas `uv` y el comando `cuypilot` no aparece en tu terminal, antepón `uv run` (por ejemplo
> `uv run cuypilot list`) o activa el entorno virtual del proyecto.

## 3. Primeros pasos (5 minutos)

Desde **la raíz de tu repositorio**, ejecuta el wizard:

```bash
cuypilot init        # o simplemente `cuypilot` en un repo sin piezas instaladas
```

Verás el banner de cuypilot. El wizard te pregunta tu rol, te sugiere las piezas para ese rol, te ofrece
las herramientas opcionales y las instala:

```
                          _ __      __
  _______  ____  ______  (_) /___  / /_
 / ___/ / / / / / / __ \/ / / __ \/ __/
/ /__/ /_/ / /_/ / /_/ / / / /_/ / /_
\___/\__,_/\__, / .___/_/_/\____/\__/
          /____/_/  v0.3.0 · skills, agents y herramientas para GitHub Copilot

  ¿Cuál es tu rol?
    1) Desarrollador Python
    2) Data scientist
    3) ML engineer / data engineer (PySpark)
    4) Documentación (técnica y funcional)
    5) Elegir piezas a mano
  >
```

Sin preguntas (por ejemplo, en un script): `cuypilot init --role mle --yes`.

Si prefieres elegir pieza por pieza:

```bash
cuypilot list                                     # qué hay disponible
cuypilot add python-standards pyspark-optimize    # instala lo que elijas
cuypilot status                                   # verifica
```

En ambos casos, al terminar versiona lo instalado, así lo tiene todo el equipo:

```bash
git add .github .gitignore
git commit -m "chore: copilot customizations via cuypilot"
```

Después, en VS Code:

1. Abre Copilot Chat. Si ya estaba abierto, recarga la ventana con **Developer: Reload Window**.
2. Escribe `/` en el chat: deberías ver las skills instaladas (por ejemplo `/design-review`).
3. Prueba: `/design-review revisa src/mi_modulo.py`.

Puedes escribirle a Copilot en español: la instrucción base le pide responder en tu idioma.

## 4. Qué hay en el catálogo

`cuypilot list` muestra siempre la lista actualizada. Hay cuatro tipos de pieza, que se usan de forma
distinta:

| Tipo | Cómo se usa |
|---|---|
| **instruction** | Se aplica **sola**, sin que la invoques (por ejemplo, al editar archivos `.py`) |
| **skill** | Copilot la usa sola cuando tu pedido coincide, o la invocas con `/nombre` |
| **agent** | La eliges en el **selector de agentes** de Copilot Chat |
| **tool** | Un programa externo que cuypilot instala y conecta a VS Code |

### Piezas del equipo

| Pieza | Tipo | Para qué | Ejemplo de uso |
|---|---|---|---|
| `python-standards` | instruction | Reglas base en todo `.py`: KISS, YAGNI, OOP con criterio, validar en los bordes, docstrings Sphinx | Automática |
| `python-design` | skill | **Diseñar** código nuevo: ¿función o clase?, SOLID, patrones solo si se justifican | "¿Cómo estructuro un módulo que lea config de yaml y env?" |
| `python-refactor` | skill | **Cambiar** código existente sin alterar su comportamiento: borrar antes que agregar | "Refactoriza `etl.py`, tiene funciones de 200 líneas" |
| `design-review` | skill | **Revisar** código sin editarlo: hallazgos priorizados | `/design-review src/scoring/` |
| `sphinx-docstrings` | skill | Docstrings Sphinx (reST) en la API pública | "Documenta las funciones públicas de `features.py`" |
| `docs-writer` | agent | Documenta un paquete completo (instala también `sphinx-docstrings`) | Selector de agentes → "documenta `src/scoring`" |
| `improve-prompt` | skill (solo manual) | Convierte un pedido vago en un prompt completo, **sin ejecutarlo** | `/improve-prompt optimiza el job de ventas` |

### PySpark, notebooks y ML

| Pieza | Tipo | Para qué | Ejemplo de uso |
|---|---|---|---|
| `pyspark-optimize` | skill | Detecta y corrige anti-patrones de PySpark (UDFs, `collect`, `withColumn` en bucles…) **sin cambiar el resultado**, más guía para Databricks/Delta | "Este notebook es lento, optimízalo" |
| `pyspark-testing` | skill | Tests de transformaciones con una `SparkSession` local y `assertDataFrameEqual` | "Escribe tests para `calcular_neto`" |
| `notebook-to-module` | skill | Pasa la lógica de un notebook (`.py` o `.ipynb`) a un módulo testeable; el notebook queda como orquestador | "Modulariza `notebooks/ventas.py`" |
| `ml-review` | skill | Revisa código de ML sin editarlo: fuga de datos, splits, semillas, métricas, MLflow (scikit-learn, XGBoost, LightGBM, Spark ML) | "Revisa `train.py`, el AUC me sale demasiado alto" |

### Documentación con Sphinx

| Pieza | Tipo | Para qué | Ejemplo de uso |
|---|---|---|---|
| `sphinx-setup` | skill | Crea o repara `docs/` con dos secciones: **técnica** (generada de los docstrings) y **funcional** (páginas para negocio); tema `furo` | "Configura Sphinx en este repo" |
| `functional-docs` | skill | Documentación funcional en español de un pipeline o modelo (9 secciones); marca `[COMPLETAR]` lo que el código no dice | "Documenta para negocio el pipeline de clientes" |

Para documentar un proyecto de cero: `sphinx-setup` → `sphinx-docstrings` (o el agente `docs-writer`) → `functional-docs`.

### Piezas de terceros (revisadas y con versión fijada)

| Pieza | Origen | Para qué |
|---|---|---|
| `ponytail` | [ponytail](https://github.com/DietrichGebert/ponytail) | Modo "senior dev flojo": la solución más simple que funciona |
| `ponytail-audit` | ponytail | Auditoría de todo el repo buscando qué borrar o simplificar |
| `ponytail-debt` | ponytail | Junta los comentarios `ponytail:` en un registro de deuda técnica |
| `systematic-debugging` | [superpowers](https://github.com/obra/superpowers) | Depurar buscando la causa raíz antes de arreglar |
| `test-driven-development` | superpowers | TDD: test que falla → código mínimo → refactor |
| `verification-before-completion` | superpowers | No dar algo por terminado sin ejecutar la verificación |
| `spark-performance` | [awesome-copilot](https://github.com/github/awesome-copilot) | Agente ("PySpark Expert Agent") que diagnostica cuellos de botella de PySpark |
| `graphify` | [graphify](https://github.com/Graphify-Labs/graphify) | Herramienta: grafo de conocimiento del repo (ver [§8](#8-herramientas-externas)) |
| `pyspark-antipattern` | [pyspark-antipattern](https://github.com/skanderboudawara/pyspark-antipattern) | Herramienta: linter de PySpark con más de 60 reglas, que `pyspark-optimize` usa si está instalado |

## 5. Combinaciones sugeridas por rol

Son las que ofrece `cuypilot init`. Instala **solo lo que vayas a usar**: si hay demasiadas skills,
compiten entre sí y Copilot elige peor.

| Rol | Piezas |
|---|---|
| Desarrollador Python (`dev`) | `python-standards python-design python-refactor design-review test-driven-development verification-before-completion` |
| Data scientist (`ds`) | `python-standards python-refactor notebook-to-module ml-review sphinx-docstrings improve-prompt` |
| ML engineer / data engineer (`mle`) | `python-standards design-review pyspark-optimize pyspark-testing notebook-to-module ml-review spark-performance` |
| Documentación (`docs`) | `sphinx-setup sphinx-docstrings docs-writer functional-docs` |

Herramientas opcionales para cualquier rol: `graphify` (repos grandes o desconocidos) y `pyspark-antipattern`.

## 6. Referencia de comandos

| Comando | Qué hace |
|---|---|
| `cuypilot init [--role dev\|ds\|mle\|docs] [--yes]` | Wizard: elige tu rol e instala las piezas sugeridas |
| `cuypilot list [--type skill\|agent\|instruction\|tool]` | Muestra el catálogo; `*` marca lo ya instalado en este repo |
| `cuypilot add <nombre>... [--dry-run] [--yes] [--force]` | Instala piezas y sus dependencias |
| `cuypilot status` | Estado de cada pieza instalada |
| `cuypilot update [<nombre>...] [--yes] [--force]` | Actualiza a la versión del wheel instalado |
| `cuypilot remove <nombre>... [--yes]` | Quita piezas |
| `cuypilot --version` | Versión de cuypilot |

Opciones:

- `--dry-run` (solo en `add`): muestra qué se instalaría y qué comandos se ejecutarían, **sin cambiar nada**.
- `--yes`: no pide confirmación antes de ejecutar los comandos de una herramienta.
- `--force`: en `add`, sobrescribe archivos que existían y no eran de cuypilot; en `update`, pisa piezas que editaste a mano.

Estados que muestra `status`:

| Estado | Significa | Qué hacer |
|---|---|---|
| `ok` | Igual a la versión del wheel | Nada |
| `desactualizada` | El wheel trae una versión más nueva | `cuypilot update` |
| `modificada` | Alguien editó los archivos a mano | Revisar; `cuypilot update --force` la restaura |
| `retirada` | La pieza ya no existe en el catálogo | `cuypilot remove <nombre>` |
| `no instalada` | (Herramientas) El programa no está en tu máquina | `cuypilot update <nombre>` |

## 7. Qué cambia en tu repositorio

| Archivo | Qué es | ¿Se versiona? |
|---|---|---|
| `.github/skills/<nombre>/` | Skills (con sus scripts y licencias) | Sí |
| `.github/agents/<nombre>.agent.md` | Agentes | Sí |
| `.github/instructions/<nombre>.instructions.md` | Instructions | Sí |
| `.github/copilot-instructions.md` | cuypilot solo gestiona su bloque `## Team conventions … <!-- cuypilot:start -->` … `<!-- cuypilot:end -->` | Sí |
| `.github/cuypilot.lock.json` | Qué está instalado, en qué versión y con qué hash | Sí |
| `.gitignore` | Líneas que agregan las herramientas (por ejemplo `graphify-out/`) | Sí |

- **Todo lo que está fuera del bloque gestionado en `copilot-instructions.md` es tuyo:** cuypilot no lo toca.
- Al versionar `.github/`, tus compañeros reciben las mismas piezas **aunque no tengan cuypilot instalado**.

## 8. Herramientas externas

### graphify

`graphify` convierte el repositorio en un grafo de conocimiento que Copilot consulta en vez de leer
archivo por archivo. Es útil en repos grandes o que no conoces.

```bash
cuypilot add graphify --dry-run    # mira qué se va a ejecutar
cuypilot add graphify              # pide confirmación y lo instala
```

Qué ocurre:

1. Si no tienes la versión aprobada, se ejecuta `uv tool install graphifyy==<versión>`.
2. Se ejecuta `graphify vscode install`. Esto instala la skill `/graphify` **en tu usuario**
   (`~/.copilot/skills/graphify`) y agrega una sección `## graphify` a `.github/copilot-instructions.md`.
3. Se agregan `graphify-out/` y `graph.json` al `.gitignore`.
4. Se agrega al bloque de cuypilot la regla de uso seguro (ver abajo).

Para construir el grafo, escribe `/graphify` en Copilot Chat.

**Uso seguro:** el código se procesa **localmente** (tree-sitter). Pero si ejecutas `graphify extract`
desde la terminal sin opciones, graphify envía la documentación, los PDF y las imágenes al proveedor de
LLM cuya API key encuentre en tu entorno, que puede estar fuera del país. Usa siempre:

```bash
graphify extract . --code-only
```

**Quitarlo:** `cuypilot remove graphify` ejecuta `graphify vscode uninstall`. Ten en cuenta que ese
comando quita la skill de **tu usuario**, así que graphify deja de estar disponible en todos tus
proyectos. El programa `graphify` sigue instalado; para quitarlo del todo: `uv tool uninstall graphifyy`.

### pyspark-antipattern

Linter de PySpark (más de 60 reglas) que complementa al script de `pyspark-optimize`. Solo se usa desde
la terminal, así que no hay que conectarlo a VS Code:

```bash
cuypilot add pyspark-antipattern                   # uv tool install pyspark-antipattern==<versión>
pyspark-antipattern check src/                     # también puedes usarlo tú directamente
```

## 9. Scripts dentro de las skills

Algunas skills traen **scripts** que hacen el análisis repetitivo sin gastar tokens del LLM. Copilot los
ejecuta primero y después lee solo lo que el script reporta. También puedes ejecutarlos tú:

```bash
# ¿Qué funciones públicas no tienen docstring o lo tienen incompleto?
python .github/skills/sphinx-docstrings/scripts/docstring_audit.py src/

# ¿Dónde se concentra la complejidad? (funciones largas, anidamiento, except silenciosos…)
python .github/skills/design-review/scripts/code_metrics.py src/

# Resumen del proyecto en ~20 líneas
python .github/skills/improve-prompt/scripts/workspace_context.py .

# Anti-patrones de PySpark (módulos, notebooks .py de Databricks e .ipynb)
python .github/skills/pyspark-optimize/scripts/spark_lint.py src/ notebooks/

# Estructura de un notebook, celda por celda (para modularizarlo)
python .github/skills/notebook-to-module/scripts/notebook_outline.py notebooks/ventas.py

# Tablas leídas/escritas, parámetros y columnas nuevas (para la documentación funcional)
python .github/skills/functional-docs/scripts/data_flow.py src/pipeline/
```

Todos son **solo lectura**, usan solo la librería estándar de Python y no acceden a la red. Aceptan
`--json` si quieres la salida en formato máquina.

## 10. Actualizar cuypilot

Cuando haya una versión nueva del wheel:

```bash
uv add --dev <ruta>/cuypilot-<nueva-versión>-py3-none-any.whl   # o pip install …
cuypilot status       # mira qué cambió
cuypilot update       # actualiza lo instalado
git add .github && git commit -m "chore: update cuypilot pieces"
```

`update` **no pisa** las piezas que editaste a mano (estado `modificada`); para forzarlo, usa `--force`.
Los cambios de cada versión están en el [`CHANGELOG.md`](../CHANGELOG.md).

## 11. Solución de problemas

| Problema | Solución |
|---|---|
| La skill no aparece al escribir `/` en Copilot Chat | Recarga la ventana (**Developer: Reload Window**) y verifica que exista `.github/skills/<nombre>/SKILL.md` |
| `cuypilot: command not found` | Usa `uv run cuypilot …` o activa el entorno virtual del proyecto |
| `Estos archivos ya existen y no son de cuypilot` | Ya tenías un archivo con ese nombre. Revísalo; si quieres reemplazarlo, `--force` |
| `` `X` depende de Y `` al hacer `remove` | Quita también la pieza que depende (por ejemplo `remove docs-writer sphinx-docstrings`) |
| La red bloquea la instalación de graphify | `cuypilot add graphify --dry-run` muestra los comandos; ejecútalos por la vía que tengas disponible y luego repite `cuypilot add graphify` |
| Los tests de PySpark fallan con "Java gateway process exited" o "Unable to locate a Java Runtime" | Instala un JDK 17 (por ejemplo Temurin) y vuelve a correr `pytest` |
| El proyecto usa `databricks-connect` y no hay `SparkSession` local | `databricks-connect` reemplaza a `pyspark` y no tiene motor local: corre los tests unitarios en un entorno con `pyspark==3.5.*` (ver `pyspark-testing`) |
| `sphinx-build -W` falla por un docstring | El mensaje indica el archivo y la línea; corrige el formato reST (o usa `sphinx-docstrings`) |
| `graphify: command not found` tras instalarlo | Ejecuta `uv tool update-shell` y abre una terminal nueva |
| Aviso "este directorio no es la raíz de un repo git" | Ejecuta cuypilot desde la raíz del repositorio |

## 12. Seguridad y datos

- Todo el contenido del catálogo pasa por **revisión en un PR**, con un checklist de seguridad.
- Las piezas de terceros están fijadas a un **commit exacto** que fue revisado, con su licencia incluida.
- cuypilot **solo ejecuta comandos** de herramientas definidas en el catálogo, **siempre te los muestra
  antes** y pide confirmación, y no usa un shell.
- Los scripts de las skills son solo lectura y no usan la red.
- Revisa los comandos que Copilot te propone ejecutar en la terminal antes de aprobarlos.

## 13. Preguntas frecuentes

**¿Tengo que escribirle a Copilot en inglés?**
No. Las piezas están escritas en inglés (el modelo las sigue mejor), pero Copilot te responde en tu idioma.

**¿Puedo editar una pieza instalada?**
Sí, pero `status` la marcará como `modificada` y no se actualizará automáticamente. Si la mejora le sirve a
todo el equipo, propónla en un PR al repo de cuypilot (ver [`CONTRIBUTING.md`](../CONTRIBUTING.md)).

**¿Mis compañeros necesitan instalar cuypilot?**
Solo quien quiera **agregar, actualizar o quitar** piezas. Los demás reciben las piezas al hacer `git pull`.

**¿Funciona en Windows?**
Sí. La CLI y los scripts son Python puro. Usa `py` en lugar de `python` si tu instalación lo requiere.

**¿Puedo proponer una pieza nueva?**
Sí: lee [`CONTRIBUTING.md`](../CONTRIBUTING.md).
