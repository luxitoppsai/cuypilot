---
type: rfc
proyecto: "cuypilot"
rfc: RFC-003
estado: aceptado   # borrador | en-revision | aceptado | rechazado | superado
fecha: 2026-09-30
tags: [rfc, contrato, pyspark, ml, documentacion]
---

# RFC-003 — Contenido de dominio: PySpark, notebooks, ML y documentación técnica/funcional

> Extiende RFC-001 y RFC-002. **No se programa hasta que `estado: aceptado`.**

## 1. Contexto y problema

El catálogo actual cubre buenas prácticas generales de Python (diseño, refactor, revisión, docstrings) y
algunas piezas de terceros. Pero el trabajo diario del equipo (DS, MLE y DE sobre Databricks) tiene
necesidades propias que nada del catálogo resuelve todavía:

- **PySpark:** UDFs de Python innecesarias, `collect()`/`toPandas()` sobre datos grandes, `withColumn`
  dentro de bucles, joins sin estrategia, particionado y caché mal usados. El agente `spark-performance`
  diagnostica cuando hay evidencia (Spark UI, `explain()`), pero falta algo que **detecte y corrija el
  código**.
- **Notebooks:** mucho código vive en notebooks de Databricks y nunca pasa a módulos testeables.
- **Tests de PySpark:** casi no se escriben, porque montar la `SparkSession` local y comparar
  DataFrames tiene fricción.
- **ML:** fuga de datos (*leakage*), splits mal hechos, falta de semillas y registro inconsistente en MLflow.
- **Documentación:** el objetivo original incluye documentación **técnica** (API) y **funcional** (qué
  hace un pipeline o modelo, para el negocio) con **Sphinx**. Hoy solo cubrimos docstrings.

Estado del arte revisado (2026-09-30):

- Spark estable: 4.1.x. En Databricks, liquid clustering reemplaza a ZORDER y al particionado para tablas nuevas.
- Linters de PySpark existentes:
  - [pyspark-antipattern](https://github.com/skanderboudawara/pyspark-antipattern): MIT, más de 60 reglas, Rust; 31★, adopción baja.
  - [databricks-labs-pylint](https://github.com/databrickslabs/pylint-plugin): 37★, depende de pylint y del SDK de Databricks.
  - spark-perf-lint: 0★, licencia propietaria.

## 2. Objetivo

Que un miembro del equipo pueda, desde Copilot:

1. Detectar y corregir anti-patrones de PySpark con un script que no gasta tokens, y aplicar las correcciones de forma segura.
2. Pasar un notebook de Databricks a un módulo con funciones testeables.
3. Escribir tests de transformaciones PySpark con fricción mínima.
4. Revisar código de ML buscando *leakage*, problemas de reproducibilidad y de evaluación.
5. Montar un proyecto Sphinx con dos secciones, **técnica** (autodoc) y **funcional** (páginas para
   negocio), y redactar la documentación funcional de un pipeline o modelo a partir del código.

## 3. Alcance

**Dentro (propuesta; la §10 define qué entra):**

| Pieza | Tipo | Script | Para qué |
|---|---|---|---|
| `pyspark-optimize` | skill | `spark_lint.py` | Detectar anti-patrones de PySpark y reescribirlos de forma Spark-native, preservando el resultado |
| `pyspark-testing` | skill | — | Tests de transformaciones: fixture de `SparkSession` local, DataFrames pequeños, `assertDataFrameEqual` |
| `notebook-to-module` | skill | `notebook_outline.py` | Extraer la lógica de un notebook de Databricks a funciones `DataFrame -> DataFrame` + tests |
| `ml-review` | skill | — | Revisión de código ML: *leakage*, splits, semillas, métricas, registro en MLflow |
| `sphinx-setup` | skill | — (plantillas en `assets/`) | Crear o reparar `docs/` con Sphinx: autodoc, autosummary, MyST, secciones técnica y funcional |
| `functional-docs` | skill | `data_flow.py` | Documentación funcional de un pipeline o modelo: propósito, entradas y salidas, reglas de negocio, parámetros, calendario |
| `pyspark-antipattern` | tool | — | Linter externo opcional (60+ reglas) que complementa a `spark_lint.py` |
| `cuypilot init` | CLI | — | Wizard de bienvenida con banner ASCII: elige tu rol y te sugiere qué instalar (§4.8) |

**Fuera (no-objetivos):**
- Ejecutar código en clusters o leer la Spark UI (no hay acceso desde el editor). El diagnóstico con
  evidencia lo sigue haciendo el agente `spark-performance`.
- Optimización de pandas (podría entrar en otra RFC si hay demanda).
- Publicar la documentación (hosting, CI de docs): queda en manos de cada proyecto.

## 4. Propuesta

### 4.1 `pyspark-optimize` + `spark_lint.py`

**Script** (stdlib, AST, solo lectura; mismas reglas que en RFC-002 §4.1). Solo reglas **de alta
confianza**, para que el LLM no persiga falsos positivos:

| Código | Detecta | Sugerencia |
|---|---|---|
| `SP001` | UDF de Python (`@udf`, `F.udf`, `spark.udf.register`) | Funciones de `pyspark.sql.functions`; si no hay, `pandas_udf` |
| `SP002` | `.collect()` / `.toPandas()` | Verificar el volumen; preferir agregación o `limit` en Spark |
| `SP003` | `withColumn` dentro de un `for`/`while` | Un solo `select` o `withColumns` |
| `SP004` | Acciones (`count`, `collect`, `show`, `first`) dentro de bucles | Reestructurar para una sola acción |
| `SP005` | `.rdd` / `.rdd.map` | Equivalente en la API de DataFrame |
| `SP006` | `repartition(1)` / `coalesce(1)` | Evitar cuellos de botella en un solo nodo |
| `SP007` | `cache()` / `persist()` sin `unpersist()` en el mismo módulo | Liberar o justificar la caché |
| `SP008` | `crossJoin` | Confirmar que es intencional |
| `SP009` | `spark.sql(f"...")` con f-string | Parámetros (`spark.sql(query, args=...)`): riesgo de inyección y peor reutilización del plan |
| `SP010` | `display(...)` / `.show()` olvidados en módulos (no en notebooks) | Quitar del código productivo |
| `SP011` | `inferSchema=True` en lecturas | Esquema explícito en pipelines productivos |
| `SP012` | `for row in df.collect()` / `iterrows()` sobre resultados de Spark | Transformación distribuida |

**Skill:**
1. Ejecutar el script.
2. Priorizar los hallazgos.
3. Reescribir **una regla a la vez**, preservando el resultado: si hay tests, correrlos; si no, proponer
   antes un test con `pyspark-testing`.
4. Guía breve de optimización para Databricks: broadcast joins y *skew*, AQE, particionado vs. liquid
   clustering, predicate pushdown, tamaño de archivos, Photon.

**Coexistencia con `spark-performance`:**
- `pyspark-optimize` cambia **código** (estática).
- `spark-performance` diagnostica con **evidencia** de ejecución.

Las descripciones lo dejan explícito y las evals lo prueban.

### 4.2 `pyspark-testing`

- Fixture de pytest con una `SparkSession` local (`local[1]`, UI deshabilitada, `shuffle.partitions`
  bajo), en un `conftest.py` de ejemplo (en `assets/`).
- `pyspark.testing.assertDataFrameEqual` (Spark ≥3.5) para comparar DataFrames, sin dependencias extra.
- Patrón: **una transformación = una función** `DataFrame -> DataFrame`, probada con 3–10 filas
  construidas en el test (casos normales, nulos, duplicados, bordes).
- Qué **no** testear localmente: lecturas y escrituras a Unity Catalog. Se mantienen en el borde (I/O separado).

### 4.3 `notebook-to-module` + `notebook_outline.py`

**Script:** lee un notebook de Databricks (`.py` con `# COMMAND ----------` o `.ipynb`) y lista, por celda:
- tipo (código, `%sql`, `%md`, `%run`, `%pip`);
- funciones definidas;
- tablas leídas y escritas;
- widgets (`dbutils.widgets`);
- `display()`;
- variables globales usadas entre celdas.

**Skill:**
1. Propone el módulo destino: transformaciones puras, I/O en el borde y parámetros explícitos en vez de widgets.
2. Extrae una función a la vez.
3. El notebook queda como orquestador fino que importa el módulo.
4. Agrega tests con `pyspark-testing`.

### 4.4 `ml-review`

Revisión sin edición (mismo formato de salida que `design-review`), con foco en ML:

- **Leakage:** `fit`/`fit_transform` antes del split, features derivadas del target, información del
  futuro en series temporales, split aleatorio donde corresponde uno temporal.
- **Reproducibilidad:** semillas (`random_state`, `seed`), versiones de los datos, dependencias fijadas.
- **Evaluación:** métrica adecuada al problema (desbalance → PR-AUC/F1, no accuracy), validación en
  hold-out, *baseline*.
- **MLflow:** experimento explícito, parámetros, métricas y firma del modelo registrados; modelo con alias.
- **PySpark ML / pandas:** escala adecuada (no `toPandas()` de todo el dataset para entrenar).

### 4.5 `sphinx-setup` (plantillas en `assets/`)

Crea o repara `docs/` con:
- `conf.py`: `sphinx.ext.autodoc`, `autosummary`, `viewcode`, `intersphinx` (Python, PySpark) y `myst_parser`
  para escribir las páginas funcionales en Markdown; tema configurable.
- Estructura:

```
docs/
  conf.py
  index.md            # portada: qué es el proyecto
  funcional/          # para negocio: un .md por pipeline/modelo (lo llena functional-docs)
    index.md
  tecnica/            # API: autosummary sobre los paquetes
    index.md
```

- Dependencias que agrega al grupo `docs` del proyecto: `sphinx`, `myst-parser` y el tema. Lo propone; no
  las instala sin confirmación.
- Verificación: `sphinx-build -W -b html docs docs/_build` sin warnings.

### 4.6 `functional-docs` + `data_flow.py`

**Script:** sobre un archivo, paquete o notebook, extrae lo determinista para la documentación funcional:
- tablas y rutas leídas (`spark.table`, `spark.read...`, `spark.sql` con `FROM`/`JOIN` literales) y escritas
  (`saveAsTable`, `insertInto`, `write...save`, `MERGE`);
- parámetros (widgets, argumentos de CLI y de job);
- funciones públicas en orden de ejecución;
- columnas creadas (`withColumn`, `alias`).

**Skill:** con esa salida, redacta una página `docs/funcional/<pipeline>.md` siguiendo una plantilla:

1. Propósito de negocio (1 párrafo).
2. Entradas (tablas, con su descripción).
3. Salidas.
4. Reglas de negocio (una por transformación relevante, en lenguaje de negocio).
5. Parámetros.
6. Frecuencia y dependencias.
7. Calidad de datos y supuestos.
8. Limitaciones conocidas.
9. Responsables.

Lo que el código no revela (propósito, responsables, calendario) **lo pregunta o lo deja marcado como
`[COMPLETAR]`; nunca lo inventa**. Por defecto en español.

### 4.7 Compatibilidad con los runtimes del equipo

El runtime mínimo del equipo es **Databricks Runtime 15.4 LTS** (Spark 3.5.0, Python 3.11). Las skills
asumen Spark ≥3.5 y Python ≥3.11, lo que coincide con el mínimo de cuypilot (RFC-001). Por eso:

- `pyspark.testing.assertDataFrameEqual` está disponible.
- `spark.sql(query, args={...})` acepta valores Python (consultas parametrizadas).
- Liquid clustering es GA: es la recomendación para tablas Delta nuevas, en lugar de particionado o ZORDER.

Si un proyecto usa un runtime más nuevo (Spark 4.x), las skills lo detectan por las dependencias
(`pyspark` / `databricks-connect`) y mencionan las diferencias relevantes (por ejemplo, ANSI SQL activado
por defecto en Spark 4).

### 4.8 `cuypilot init`: wizard con banner

pip no puede ejecutar código al instalar un wheel. Por eso la "instalación" visible es un wizard que se
ejecuta con `cuypilot init`, o con `cuypilot` sin argumentos, si el repo todavía no tiene piezas instaladas:

```
   ___  _   _  _   _  ____   ___  _      ___  _____
  / __|| | | || | | ||  _ \ |_ _|| |    / _ \|_   _|
 | (__ | |_| || |_| || |_) | | | | |__ | (_) | | |
  \___| \___/  \__, ||  __/ |___||____| \___/  |_|
               |___/ |_|            v0.3.0 · Copilot toolkit

  ¿Cuál es tu rol?
    1) Desarrollador Python
    2) Data scientist
    3) ML engineer / data engineer (PySpark)
    4) Elegir piezas a mano
  > 3

  Te sugiero: python-standards, python-refactor, design-review, pyspark-optimize,
              pyspark-testing, spark-performance, systematic-debugging
  ¿Agregar herramientas opcionales? graphify [s/N], pyspark-antipattern [s/N]
  ¿Instalar? [S/n]
```

- Solo stdlib (`input()`, colores ANSI). Sin colores si la salida no es una terminal o si existe `NO_COLOR`.
- Las combinaciones por rol viven en `catalog.toml` (`[roles.<rol>]`) para no duplicarlas en el código y la guía.
- Al final usa el mismo `add` de siempre (lockfile, confirmación de herramientas) y recuerda hacer commit.
- `--role <rol> --yes` lo deja no interactivo (para CI o scripts).
- El banner también aparece en `cuypilot --version`.

### 4.9 `pyspark-antipattern` (tool opcional)

Se instala con `uv tool install pyspark-antipattern==<versión>` y no necesita conectarse a VS Code.
`pyspark-optimize` lo ejecuta si está instalado (`pyspark-antipattern check <path>`). Como es una
herramienta de solo terminal, `configure` pasa a ser **opcional** para el tipo `tool`.

### 4.10 Evals y versión

- Cada skill con evals, incluyendo coexistencia:
  - `pyspark-optimize` vs `spark-performance` vs `python-refactor`;
  - `ml-review` vs `design-review`;
  - `functional-docs` vs `sphinx-docstrings` y `docs-writer`.
- Cada script con tests sobre fixtures (código PySpark de ejemplo; **no requiere pyspark instalado**,
  porque es análisis de AST).
- Release `v0.3.0`.

## 5. Alternativas consideradas

| Alternativa | Por qué no (por ahora) |
|---|---|
| Usar `pyspark-antipattern` como `tool` en vez de `spark_lint.py` | Más reglas (60+), pero 31★ (adopción baja), binario compilado (requiere aprobación) y otra dependencia. Nuestro script cubre las 12 reglas de mayor impacto sin instalar nada. Queda como opción si se piden más reglas (§10) |
| `databricks-labs-pylint` | Depende de pylint y del SDK de Databricks; su foco son las APIs de Databricks, no el rendimiento |
| Que solo el LLM detecte anti-patrones | Más tokens y menos consistente; el script da la lista y el LLM corrige |
| Ampliar `spark-performance` (tercero) | Habría que reescribirlo; la adaptación debe ser mínima (RFC-002) |
| Documentación funcional fuera de Sphinx (Confluence, Word) | El objetivo inicial pide Sphinx; MyST permite escribirla en Markdown dentro del mismo sitio |

## 6. ¿Agente LLM?

No. Scripts deterministas y skills; el agente es Copilot.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Falsos positivos de `spark_lint.py` (por ejemplo, `collect()` sobre datos ya agregados) | Solo reglas de alta confianza; la skill pide confirmar el volumen antes de cambiar nada |
| Una "optimización" que cambia el resultado | Una regla a la vez, con tests antes del cambio (`pyspark-testing`) |
| Documentación funcional inventada | `[COMPLETAR]` en lo que el código no revela; la skill lo prohíbe explícitamente |
| Demasiadas skills de "revisión" compitiendo (`design-review`, `ml-review`, `ponytail-audit`, `pyspark-optimize`) | Descripciones con "cuándo sí / cuándo no" y evals de coexistencia; combinaciones por rol en la guía |
| Diferencias entre versiones de Spark | Mínimo 15.4 LTS (Spark 3.5); las diferencias con Spark 4.x se mencionan cuando se detectan |

## 8. Plan de entrega

1. `spark_lint.py` + tests → `pyspark-optimize` + evals.
2. `pyspark-testing` (+ `assets/conftest.py`) + evals.
3. `notebook_outline.py` + tests → `notebook-to-module` + evals.
4. `ml-review` + evals.
5. `sphinx-setup` (+ plantillas) + evals; verificar `sphinx-build -W` sobre un proyecto de ejemplo.
6. `data_flow.py` + tests → `functional-docs` + evals.
7. Guía de usuario (catálogo, combinaciones por rol), CHANGELOG y `v0.3.0`.

## 9. Criterios de aceptación

- [ ] `spark_lint.py` detecta las 12 reglas sobre fixtures, sin falsos positivos en código correcto equivalente.
- [ ] `notebook_outline.py` y `data_flow.py` funcionan con notebooks de Databricks (`.py` y `.ipynb`) y con módulos normales.
- [ ] `sphinx-setup` deja un proyecto donde `sphinx-build -W` pasa, con secciones técnica y funcional.
- [ ] `functional-docs` produce una página con las 9 secciones y marca `[COMPLETAR]` en lo que no se deduce del código.
- [ ] Evals de coexistencia definidas para los pares de §4.7.
- [ ] Todos los scripts cumplen las reglas de RFC-002 §4.1 (verificado por el CI).

## 10. Preguntas abiertas

Decisiones del 2026-09-30:
- Entran las 6 skills.
- Runtime mínimo: Databricks Runtime 15.4 LTS (Spark 3.5, Python 3.11); cuypilot mantiene Python ≥3.11 (§4.7).
- Notebooks `.py` e `.ipynb`.
- Documentación funcional con la plantilla de §4.6, siempre en español.
- Docstrings Sphinx (reST), sin tema corporativo → `furo` por defecto.
- `pyspark-antipattern` como tool opcional.
- ML: scikit-learn, XGBoost y LightGBM con MLflow, y también Spark ML.
- Nuevo: wizard `cuypilot init` con banner (§4.8).

Sin preguntas pendientes.
