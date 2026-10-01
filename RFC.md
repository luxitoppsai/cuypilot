---
type: rfc
proyecto: "cuypilot"
rfc: RFC-001
estado: borrador   # borrador | en-revision | aceptado | rechazado | superado
fecha: 2026-09-30
tags: [rfc, contrato]
---

# RFC-001 — Base de cuypilot: catálogo versionado + CLI de instalación

> Contrato de lo que se va a construir. **No se programa hasta que `estado: aceptado`.**
> Investigación de soporte: [`docs/research/estado-del-arte.md`](docs/research/estado-del-arte.md).

## 1. Contexto y problema

En el trabajo, los equipos de desarrollo, data science y ML engineering usan Python y PySpark
(Databricks) con GitHub Copilot en VS Code. Hoy cada quien arma (o no) sus propias instrucciones y
prompts. Eso trae tres problemas:

- No hay estándares compartidos.
- No hay control de versiones de qué personalización usa cada proyecto.
- No hay revisión de calidad ni de seguridad.

Copilot ya soporta personalizaciones en archivos (skills, agents, instructions). Lo que falta es
**centralizarlas, gobernarlas y distribuirlas**.

## 2. Objetivo

Un repositorio en GitHub Enterprise que:

1. Contenga un **catálogo** de skills, agents e instructions, cada pieza con su **versión** y su **dueño**.
2. Se publique como **wheel versionado** (la versión del repo es la versión del wheel).
3. Incluya una **CLI `cuypilot`** que, desde el workspace de un proyecto, instale, actualice, liste y
   quite piezas del catálogo en las rutas que VS Code Copilot lee.
4. Tenga un proceso de contribución con **validación automática** (CI) y **revisión** (CODEOWNERS + checklist).

**Hecho =** un desarrollador instala el wheel como dependencia de desarrollo, corre
`cuypilot add <pieza>` y la pieza aparece y funciona en Copilot Chat de VS Code. Además, el CI rechaza
una pieza mal formada.

Esta RFC cubre **la base**. El contenido por dominio (PySpark, ML, Sphinx funcional, etc.) se define en
RFCs posteriores.

## 3. Alcance

**Dentro:**
- Estructura del repo y formato del catálogo (`catalog.toml`).
- CLI con `list`, `add`, `remove`, `status`, `update`.
- Lockfile en el proyecto consumidor y detección de ediciones locales.
- Bloque gestionado en `.github/copilot-instructions.md` (instrucción base: responder en el idioma del usuario).
- Validación del catálogo con pytest, que el CI ejecuta.
- Gobernanza: `CODEOWNERS` (vacío en la v1), plantilla de PR con checklist (seguridad, evals, versión),
  `CONTRIBUTING.md` (en español), CHANGELOG y reglas de semver.
- Formato de evals por skill (casos declarados y ejecución manual en la v1).
- **Contenido inicial: principios de programación** (también sirve para probar el circuito completo con
  los tres tipos de pieza). Detalle en 4.10.
- Build del wheel (`uv build`) y distribución manual a una ruta compartida.

**Fuera (no-objetivos):**
- Contenido de dominio más allá del contenido inicial (optimización PySpark/Databricks, ML, doc funcional).
- Publicación en Artifactory (cuando esté listo será solo un paso extra de publicación; no cambia el diseño).
- Marketplace de Agent Plugins, Copilot CLI, agente en la nube, Claude Code.
- Hooks y MCP (no aparecen en el catálogo de la v1).
- Prompt files (están deprecados).
- Evals automatizadas contra Copilot (no hay forma estable de ejecutarlas headless en VS Code).
- Resolver versiones pieza por pieza: un solo wheel equivale a un conjunto coherente de piezas.

## 4. Propuesta

### 4.1 Estructura del repo

```
cuypilot/
  src/cuypilot/
    __init__.py
    cli.py                 # argparse (stdlib), sin dependencias de runtime
    catalog/               # se empaqueta como package data dentro del wheel
      catalog.toml         # registro: fuente de verdad de metadatos
      base/copilot-instructions.md
      skills/<name>/SKILL.md (+ recursos)
      agents/<name>.agent.md
      instructions/<name>.instructions.md
  evals/<name>.json        # casos de evaluación por pieza (no van en el wheel)
  tests/                   # tests de la CLI + validación del catálogo
  .github/
    CODEOWNERS
    pull_request_template.md
    workflows/ci.yml       # ruff + pytest (+ uv build en tags)
  CONTRIBUTING.md  CHANGELOG.md  README.md  PROJECT.md  RFC.md
```

Los archivos del catálogo usan **solo el frontmatter estándar** de VS Code. Versión, dueño y
dependencias viven en `catalog.toml`, para no meter claves que VS Code no reconoce.

### 4.2 `catalog.toml`

```toml
[items.sphinx-docstrings]
type = "skill"
version = "1.0.0"
owner = ""            # opcional; vacío en la v1
description = "Escribe/corrige docstrings Sphinx (reST) en código Python."
requires = []

[items.docs-writer]
type = "agent"
version = "0.1.0"
description = "..."
requires = ["sphinx-docstrings"]
```

- `type` ∈ {`skill`, `agent`, `instruction`}.
- `requires`: dependencias entre piezas. `add` las instala junto con la pieza pedida, sin resolución de versiones.
- TOML porque se edita a mano (admite comentarios) y Python ≥3.11 lo lee con `tomllib` (stdlib). El
  lockfile sí es JSON, porque la CLI lo escribe y `tomllib` solo lee.

### 4.3 Dónde instala la CLI (en el workspace consumidor)

| type | destino |
|---|---|
| skill | `.github/skills/<name>/` (carpeta completa) |
| agent | `.github/agents/<name>.agent.md` |
| instruction | `.github/instructions/<name>.instructions.md` |
| base | bloque `<!-- cuypilot:start -->…<!-- cuypilot:end -->` en `.github/copilot-instructions.md` |

El mapeo vive en **un único lugar** del código: si Copilot cambia sus rutas (como pasó con los prompt
files), se toca una sola tabla. Los archivos instalados **se commitean** en el repo consumidor, así todo
el equipo los tiene aunque no haya instalado la CLI.

### 4.4 Lockfile: `.github/cuypilot.lock.json`

```json
{
  "cuypilot_version": "0.1.0",
  "items": {
    "sphinx-docstrings": {
      "type": "skill", "version": "1.0.0",
      "files": {".github/skills/sphinx-docstrings/SKILL.md": "sha256:..."}
    }
  }
}
```

### 4.5 Comandos

| Comando | Comportamiento |
|---|---|
| `cuypilot list [--type T]` | Catálogo del wheel instalado: nombre, tipo, versión, descripción, y si ya está instalado. |
| `cuypilot add <name>...` | Copia la pieza y sus `requires`, actualiza el lockfile y escribe o refresca el bloque base. Si el destino existe y no es de cuypilot, aborta (`--force` para sobrescribir). |
| `cuypilot remove <name>...` | Borra los archivos registrados en el lockfile. Avisa si otra pieza instalada depende de esta. |
| `cuypilot status` | Por cada pieza: `ok`, `desactualizada` (el catálogo tiene una versión más nueva) o `modificada` (el hash no coincide). |
| `cuypilot update [<name>...]` | Actualiza a la versión del wheel. **No pisa piezas `modificada`** salvo con `--force`. |

Se trabaja sobre el directorio actual. Si no hay `.git`, se avisa, pero no se bloquea.

### 4.6 Versionado

- **Wheel/repo:** semver con tag `vX.Y.Z`.
  - MAJOR: se quita o renombra una pieza, o hay un cambio incompatible en la CLI o el lockfile.
  - MINOR: pieza nueva o comando nuevo.
  - PATCH: correcciones.
- **Pieza:** su `version` en `catalog.toml` se sube cuando cambia su contenido. Se controla con el
  checklist del PR (sin verificación automática en la v1).
- `CHANGELOG.md` por release, con secciones por pieza.

### 4.7 Validación (pytest, la corre el CI)

- Cada pieza de `catalog.toml` tiene sus archivos, y no hay archivos sin registrar.
- `name` de la skill = nombre de la carpeta, cumple `^[a-z0-9-]{1,64}$` y `description` tiene ≤1024 caracteres.
- Frontmatter mínimo por tipo: skill (`name`, `description`), agent (`description`), instruction (`applyTo`).
- `requires` apunta a piezas existentes y no tiene ciclos.
- Escaneo simple de riesgos: no hay patrones de secretos; las URLs, `curl`/`requests` y scripts incluidos
  quedan marcados para revisión manual.
- Cada skill tiene su archivo en `evals/`.

### 4.8 Evals (v1)

`evals/<name>.json` con `should_trigger`, `should_not_trigger` y `edge_cases` (3–5 prompts en total)
y lo que se espera del resultado. En la v1 se ejecutan **a mano** en VS Code antes de aprobar el PR, y se
marca en el checklist. Automatizarlas queda para otra RFC.

### 4.9 Gobernanza

- `CODEOWNERS`: el archivo existe pero queda **vacío en la v1**. Cuando haya más contribuyentes, cada
  carpeta del catálogo tendrá dueño y el autor no podrá aprobarse a sí mismo.
- Plantilla de PR con checklist: seguridad (scripts, red, credenciales, instrucciones adversariales,
  rutas), evals ejecutadas, versión subida y CHANGELOG actualizado.
- Idioma:
  - Contenido para el modelo (skills, agents, instructions): **inglés**.
  - Documentación para personas: **español**.
  - La instrucción base indica responder en el idioma del usuario.

### 4.10 Contenido inicial: principios de programación

Los criterios de trabajo (OOP con criterio, SOLID, KISS, YAGNI, patrones de diseño, robustez en los
bordes, nombres claros, docstrings Sphinx) pasan a ser piezas. Se separan por **momento de uso**
(crear / cambiar / evaluar) para que las descripciones no compitan entre sí al activarse:

| Pieza | Tipo | Cuándo actúa | Contenido |
|---|---|---|---|
| `python-standards` | instruction (`applyTo: **/*.py`) | Siempre, al tocar `.py` | Versión corta y directiva: KISS, YAGNI, OOP solo cuando hay estado + comportamiento, funciones puras para lógica simple, validar solo en los bordes (sin `try/except` defensivos), nombres claros, funciones cortas, docstrings Sphinx en lo público. |
| `python-design` | skill | **Diseñar** código nuevo (módulo, clase, API) | ¿Función o clase? ¿Hace falta una abstracción? SOLID como guía; patrones de diseño **solo si resuelven un problema presente**, prefiriendo alternativas pythónicas (funciones de primera clase, `dataclass`, `Protocol`, módulos) antes que las jerarquías GoF. Incluye un catálogo breve de patrones con "úsalo cuando / no lo uses cuando". |
| `python-refactor` | skill | **Cambiar** código existente | Refactor que preserva el comportamiento: asegurar tests antes, pasos pequeños, eliminar código muerto y abstracciones especulativas, aplanar jerarquías innecesarias, extraer funciones. Prioridad: borrar antes que agregar. |
| `design-review` | skill | **Evaluar** código sin modificarlo | Revisión contra los principios: sobreingeniería (qué borrar), violaciones de SOLID, acoplamiento, defensas innecesarias. Devuelve hallazgos priorizados; no edita. |
| `sphinx-docstrings` | skill | Documentar API Python | Docstrings reST (`:param:`, `:returns:`, `:raises:`) en módulos, clases y funciones públicas. |
| `docs-writer` | agent | Documentación técnica de un paquete | Usa `sphinx-docstrings` (`requires`); prueba el camino agent + dependencias. |

Las evals de estas piezas incluyen **casos de coexistencia** entre `python-design`, `python-refactor` y
`design-review`. Por ejemplo, "revisa este módulo" debe activar `design-review` y no `python-refactor`.

### 4.11 Instalación por parte de los usuarios

```bash
# mientras se configura Artifactory: wheel en ruta compartida
uv add --dev <ruta>/cuypilot-0.1.0-py3-none-any.whl
# o: pip install <ruta>/cuypilot-0.1.0-py3-none-any.whl  (en requirements-dev.txt)
cuypilot list
cuypilot add python-standards python-design design-review
git add .github && git commit -m "chore: add copilot customizations via cuypilot"
```

Es dependencia de **desarrollo**: nunca va en el `requirements.txt` que se instala en el cluster de Databricks.

## 5. Alternativas consideradas

| Alternativa | Por qué no (por ahora) |
|---|---|
| Marketplace de Agent Plugins | Se configura por usuario, falla en silencio, lo instalado no queda versionado en el repo del proyecto y no es el flujo natural del equipo (`pip`/`uv`). Se puede reconsiderar en el futuro **además** de la CLI (generar `marketplace.json` desde el mismo catálogo). |
| Nivel organización (`.github-private`, instrucciones de org) | Depende de administradores de la empresa, solo cubre agents/instructions globales y no permite elegir por proyecto. Es complementario. |
| Copiar a mano / plantilla cookiecutter | Sin versión, sin actualización y con deriva garantizada. |
| Git submodule | Fricción alta para DS/MLE y no permite elegir piezas. |
| No hacer nada | Es el estado actual: cada quien por su lado. |

## 6. ¿Agente LLM? (LangChain/LangGraph)

**No.** cuypilot es una herramienta determinista que copia archivos. El "agente" es Copilot. No hay
dependencia de ningún framework de LLM.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Copilot cambia rutas o formatos (ya pasó con los prompt files) | Mapeo de destinos centralizado. Se revisa en cada release mayor de VS Code. |
| Ediciones locales que se pierden al actualizar | Hashes en el lockfile y `update` que no pisa sin `--force`. |
| Demasiadas skills instaladas, que se estorban al activarse | Instalación selectiva; las evals de coexistencia van en la RFC de contenido. |
| Pieza maliciosa o con secretos | Validación en CI, checklist de seguridad, CODEOWNERS y separación de funciones. |
| Python antiguo en algunos entornos | Python ≥3.11 como mínimo (decidido) y solo stdlib en runtime. |
| Distribución manual del wheel (ruta compartida) | Temporal: Artifactory se suma sin cambiar el diseño. |

## 8. Plan de entrega

1. Estructura del repo, `catalog.toml` y tests de validación del catálogo.
2. CLI: `list` → `add` (con lockfile y bloque base) → `status` → `update` → `remove`. Tests sobre directorios temporales.
3. Contenido inicial (4.10): `python-standards`, `python-design`, `python-refactor`, `design-review`, `sphinx-docstrings`, `docs-writer`, con sus evals.
4. Gobernanza: CODEOWNERS (vacío), plantilla de PR, CONTRIBUTING, CHANGELOG y workflow de CI.
5. `uv build` → `v0.1.0` → instalar el wheel en un proyecto real y probarlo en VS Code (**MVP demostrable**).

## 9. Criterios de aceptación

- [ ] `uv build` genera un wheel que incluye el catálogo, y el wheel se instala en un venv limpio con Python 3.11.
- [ ] `cuypilot add sphinx-docstrings` crea `.github/skills/sphinx-docstrings/SKILL.md` y el lockfile; la skill aparece como `/sphinx-docstrings` en Copilot Chat de VS Code.
- [ ] `cuypilot add docs-writer` instala también `sphinx-docstrings` (`requires`), y el agente aparece en el selector.
- [ ] `python-standards` se aplica al editar un `.py` (visible en las referencias de la respuesta).
- [ ] Al editar a mano un archivo instalado, `status` lo marca `modificada` y `update` no lo pisa sin `--force`.
- [ ] `remove` deja el workspace sin rastros de la pieza, salvo el bloque base si quedan otras piezas.
- [ ] El contenido de `copilot-instructions.md` fuera del bloque gestionado nunca se modifica.
- [ ] Las evals de coexistencia de `python-design` / `python-refactor` / `design-review` pasan (ejecución manual).
- [ ] El CI falla ante: frontmatter inválido, nombre ≠ carpeta, `requires` roto, pieza sin evals o pieza no registrada.
- [ ] Docstrings Sphinx en el código público; `ruff` limpio; tests verdes.

## 10. Preguntas abiertas

Ninguna bloqueante. Decisiones cerradas el 2026-09-30:

1. Python **≥3.11** como mínimo → el catálogo pasa a TOML (`tomllib`).
2. `CODEOWNERS` vacío en la v1.
3. La subida de versión de una pieza se controla con el checklist del PR, sin verificación en el CI.
4. Ruta del wheel: `<ruta>` en el README; la completa Luis.
5. Contenido inicial: piezas de principios de programación (4.10) + `sphinx-docstrings` + `docs-writer`.
