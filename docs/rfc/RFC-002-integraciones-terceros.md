---
type: rfc
proyecto: "cuypilot"
rfc: RFC-002
estado: aceptado   # borrador | en-revision | aceptado | rechazado | superado
fecha: 2026-09-30
tags: [rfc, contrato, terceros, scripts]
---

# RFC-002 — Scripts dentro de las skills e integraciones de terceros

> Extiende RFC-001 (`RFC.md`). **No se programa hasta que `estado: aceptado`.**

## 1. Contexto y problema

Dos necesidades:

1. **Gastar menos tokens en lo que es determinista.** Hoy el LLM tiene que leer todo el código para
   saber, por ejemplo, qué funciones no tienen docstring o cuáles son demasiado largas. Un script que
   analiza el AST de Python lo resuelve en milisegundos, y le entrega al LLM solo la lista de cosas que
   hay que atender.
2. **Reutilizar piezas externas muy probadas** sin que cada persona las instale a mano, con versiones
   distintas, sin revisión de seguridad ni de licencia, y sin controlar qué datos salen.

Investigación del 2026-09-30 (estrellas y licencia consultadas con la API de GitHub):

| Proyecto | ★ | Licencia | Decisión |
|---|---|---|---|
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | 149k | MIT | **Entra.** Sus skills se copian al catálogo, **sin `ponytail-review`** (se solapa con `design-review`) y **sin hooks** |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | 123k | Apache-2.0 | **Entra** como `tool` |
| [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | 73k | MIT | **Fuera:** se solapa con graphify, requiere Node y trae telemetría |
| [obra/superpowers](https://github.com/obra/superpowers) | 294k | MIT | **Entran 3 skills** copiadas al catálogo |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | 40k | MIT | **Entra** el agente `spark-performance`, copiado al catálogo |
| [anthropics/skills](https://github.com/anthropics/skills) | 179k | Mixta | **Entra** `skill-creator` (para quienes contribuyen), si su licencia lo permite |
| [databricks/databricks-agent-skills](https://github.com/databricks/databricks-agent-skills) | oficial | Databricks License | **Fuera** (decidido el 2026-09-30: enseñan a operar la plataforma, no aportan al trabajo de código del equipo; ver §4.4) |

## 2. Objetivo

1. Skills con **scripts deterministas** que se instalan con la skill y que el LLM ejecuta en lugar de leer
   todo el código.
2. **Piezas de terceros copiadas al catálogo** con origen, commit y licencia trazables, que se instalan
   igual que las propias.
3. Un tipo **`tool`** para herramientas externas (graphify): cuypilot ejecuta su instalador oficial, con
   confirmación y versión aprobada.

**Hecho =**
- `cuypilot add sphinx-docstrings` trae su script, y Copilot lo usa para encontrar qué documentar.
- `cuypilot add ponytail graphify` deja todo funcionando en VS Code.
- `cuypilot status` informa el estado de todo lo instalado.

## 3. Alcance

**Dentro:**
- Reglas, tests y validación para scripts dentro de las skills, y los 3 primeros scripts (§4.1).
- Metadatos `upstream` y validación de licencias (§4.2).
- Tipo `tool` en la CLI (§4.3) y `graphify` como primera herramienta.
- Piezas de terceros: ponytail (sin `-review`), 3 de superpowers, `spark-performance` y `skill-creator` (§4.5).

**Fuera (no-objetivos):**
- codegraph, `ponytail-review` y las skills de Databricks (decidido).
- Hooks de terceros (ejecución arbitraria de código, Node).
- Skills de `anthropics/skills` con licencia propietaria (docx, xlsx, pdf, pptx).
- Sincronización automática con los repos originales: cada actualización entra por PR.
- Paquetes por rol (`--bundle`): más adelante, con uso real.
- Skills propias de optimización de PySpark: van en la RFC de contenido de dominio.

## 4. Propuesta

### 4.1 Scripts dentro de las skills

Ubicación: `skills/<name>/scripts/*.py`. La CLI ya copia la carpeta completa, así que **se instalan con
`add`**, quedan con hash en el lockfile y se actualizan con `update`. No hace falta cambiar la CLI.

Reglas (validadas en el CI y exigidas en el PR):
- **Solo stdlib, Python ≥3.11.** Corren con el `python` del proyecto, sin instalar nada.
- **Solo lectura por defecto:** analizan y reportan; no modifican archivos. Las ediciones las hace el LLM.
- **Sin red.**
- **Salida compacta pensada para el LLM:** una línea por hallazgo (`ruta:línea  tipo  nombre — problema`)
  y un resumen al final, con `--json` opcional.
- **Cada script tiene tests** en `tests/scripts/` y el CI los corre.
- El `SKILL.md` indica cuándo y cómo ejecutarlo, por ejemplo
  `python .github/skills/sphinx-docstrings/scripts/docstring_audit.py src/`, y le dice al LLM que lea
  **solo** los archivos o funciones reportados.

Primeros scripts:

| Skill | Script | Qué reporta |
|---|---|---|
| `sphinx-docstrings` | `docstring_audit.py` | Módulos, clases y funciones públicas sin docstring; `:param:` faltantes o sobrantes respecto de la firma; falta `:returns:` cuando la función retorna algo |
| `design-review` | `code_metrics.py` | Funciones largas, con muchos parámetros, anidamiento profundo o muchas ramas; clases que deberían ser funciones (solo `__init__` + un método); ABCs con una sola implementación; `except:` desnudos o `except … : pass`. Ordenado por severidad. `python-refactor` lo usa si está instalado |
| `improve-prompt` | `workspace_context.py` | Resumen del proyecto en ~20 líneas: versión de Python, dependencias principales, `databricks.yml`/bundles, notebooks, carpeta de tests, layout `src/` y piezas de cuypilot instaladas |

Más adelante, la RFC de dominio añadirá un script de anti-patrones de PySpark (UDFs, `collect()`, `toPandas()`, loops de `withColumn`).

### 4.2 Piezas de terceros copiadas al catálogo

Son skills, agents o instructions normales, con un bloque `upstream` en `catalog.toml`:

```toml
[items.ponytail-audit]
type = "skill"
version = "1.0.0"
description = "..."
[items.ponytail-audit.upstream]
repo = "DietrichGebert/ponytail"
ref = "<sha de 40 caracteres>"      # commit exacto revisado
path = "skills/ponytail-audit"
license = "MIT"
adapted = false                     # true si se ajustó para Copilot (se describe en el PR)
```

- La carpeta de la pieza incluye el `LICENSE` original, porque MIT y Apache exigen conservar el aviso.
- El CI valida:
  - `upstream` completo;
  - LICENSE presente;
  - licencia dentro de la lista permitida: `MIT`, `Apache-2.0`, `BSD-2-Clause`, `BSD-3-Clause`.
- **Adaptación mínima:** algunas skills mencionan herramientas que solo existen en Claude Code (por
  ejemplo `TodoWrite` o subagentes `Task`). Se ajustan lo indispensable, con `adapted = true`.
- **Actualizar desde el original:** un PR que cambia `ref`, con el diff a la vista y el checklist de seguridad.

### 4.3 Tipo `tool` (graphify)

```toml
[items.graphify]
type = "tool"
version = "0.9.2"
description = "Grafo de conocimiento del repo para Copilot (tree-sitter, local)."
license = "Apache-2.0"
install = [["uv", "tool", "install", "graphifyy==0.9.2"]]
configure = [["graphify", "vscode", "install"]]
check = ["graphify", "--version"]
uninstall = [["graphify", "vscode", "uninstall"]]
gitignore = ["graphify-out/", "graph.json"]
```

- **`add`:**
  1. Muestra los comandos exactos y pide confirmación (`--yes` la omite).
  2. Ejecuta `install` solo si `check` falla o la versión no coincide.
  3. Ejecuta `configure`.
  4. Agrega las líneas `gitignore`.
  5. Registra la herramienta y su versión en el lockfile, **sin hashes**: los archivos los gestiona la
     propia herramienta.
- **`--dry-run`:** solo muestra los comandos.
- **`status`:** `ok` / `desactualizada` / `no instalada`, según `check`.
- **`remove`:** ejecuta `uninstall`. La herramienta global se deja, y se indica cómo quitarla.
- Los comandos son listas de argumentos que vienen del catálogo (revisado por PR). Se ejecutan con
  `subprocess.run` y **sin shell**.
- **Uso seguro en la empresa:** el `SKILL.md` que instala graphify no lo controla cuypilot, así que el
  bloque base de `copilot-instructions.md` agrega, mientras graphify esté instalado, una regla: usar
  `graphify extract --code-only` salvo que se haya configurado un `--backend` aprobado. La razón es que
  el pase semántico sobre documentos envía su contenido a un LLM, y elige el proveedor según la API key
  que encuentre en el entorno.

### 4.4 Skills de Databricks: descartadas

Se evaluaron las 31 skills oficiales (2026-09-30). Su licencia permitía copiarlas, pero se descartan.
Enseñan a **operar la plataforma** (CLI, bundles, jobs, serving, apps) y no aportan a la calidad ni a la
optimización del código PySpark, que es el foco de cuypilot. Además, harían que el agente ejecute
comandos `databricks` reales con las credenciales del desarrollador. Se puede reconsiderar si aparece una
necesidad concreta.

### 4.5 Resto de piezas de terceros

| Pieza | Origen | Notas |
|---|---|---|
| `ponytail` (modo siempre activo), `ponytail-audit`, `ponytail-debt`, `ponytail-help` | ponytail | Sin `-review` ni hooks. Las evals de coexistencia con `python-refactor` y `design-review` son obligatorias |
| `systematic-debugging`, `test-driven-development`, `verification-before-completion` | superpowers | Revisar si mencionan herramientas exclusivas de Claude; adaptar lo mínimo |
| `spark-performance` (agent) | awesome-copilot | Revisar su calidad antes de incluirlo |
| `skill-creator` | anthropics/skills | Solo si su licencia es Apache-2.0; está pensado para quienes contribuyen a cuypilot |

## 5. Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Marketplaces originales (ponytail, superpowers) | Mismas razones de ADR-001: instalación por persona, sin versión en el repo, red externa |
| Descargar del repo original al instalar | Depende de GitHub.com y no garantiza que lo instalado sea lo revisado |
| Que el LLM haga los análisis deterministas leyendo el código | Más tokens, más lento y menos fiable que un script de AST |
| Usar herramientas externas para las métricas (radon, interrogate, pydocstyle) | Agregan dependencias al proyecto del usuario; con `ast` de la stdlib alcanza para lo que necesitamos |

## 6. ¿Agente LLM?

No. Todo sigue siendo determinista: se copian archivos, se ejecutan comandos aprobados y los scripts analizan el AST.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Demasiadas skills compiten entre sí (catálogo ≈ 30 piezas) | Instalación selectiva; evals de coexistencia; el README sugiere combinaciones por rol |
| Licencias | Lista permitida en el CI, LICENSE copiado y `upstream.license` obligatorio |
| Una pieza de terceros cambia de forma maliciosa | `ref` fijado a un commit; cada actualización es un PR revisado |
| Scripts con efectos laterales | Solo lectura, solo stdlib, sin red, con tests; el CI los marca para revisión manual |
| La red bloquea una instalación | `--dry-run` y resolverlo caso por caso; Artifactory más adelante |

## 8. Plan de entrega

1. Scripts: `docstring_audit.py`, `code_metrics.py`, `workspace_context.py` + tests + actualizar sus `SKILL.md` (sube a MINOR la versión de cada pieza).
2. `upstream` + validación de licencias en el CI.
3. Copiar al catálogo ponytail, superpowers (3), `spark-performance` y `skill-creator`, con evals.
4. Tipo `tool` en la CLI (`add`/`status`/`remove`, `--yes`, `--dry-run`) + tests con comandos simulados.
5. `graphify` + la regla `--code-only` en el bloque base.
6. README (combinaciones sugeridas por rol), CHANGELOG y `v0.2.0`.

## 9. Criterios de aceptación

- [ ] `cuypilot add sphinx-docstrings` instala también `scripts/docstring_audit.py`, y en VS Code Copilot lo ejecuta antes de documentar.
- [ ] Los 3 scripts tienen tests, son solo stdlib y no escriben archivos.
- [ ] El CI falla si una pieza de terceros no tiene `upstream`, no tiene LICENSE o su licencia no está permitida.
- [ ] `cuypilot add ponytail-audit` instala la skill con su LICENSE.
- [ ] `cuypilot add graphify --dry-run` no ejecuta nada; `cuypilot add graphify` pide confirmación y deja graphify utilizable en Copilot Chat.
- [ ] `cuypilot status` muestra las herramientas con su versión instalada y la aprobada.
- [ ] Los comandos de las herramientas se ejecutan sin shell y solo si vienen del catálogo.

## 10. Preguntas abiertas

Ninguna bloqueante. Decisiones cerradas el 2026-09-30:

1. Solo graphify (sin codegraph); sin `ponytail-review`; la CLI ejecuta los instaladores con confirmación.
2. Skills de Databricks descartadas (§4.4).
3. Los 3 scripts iniciales aprobados.
4. Verificado durante la implementación (2026-09-30):
   - **`skill-creator` queda fuera:** sus scripts dependen de la CLI de Claude (no funcionan desde
     Copilot) y no cumplen las reglas de scripts (§4.1).
   - **ponytail:** entran `ponytail`, `ponytail-audit` y `ponytail-debt`. También quedan fuera
     `ponytail-help` (ayuda para instalarlo en Claude Code) y `ponytail-gain` (marcador de su benchmark).
   - **superpowers:** sin menciones a herramientas exclusivas de Claude. En `systematic-debugging` se
     excluyen `find-polluter.sh` y el ejemplo `.ts` (son de JS), con las referencias ajustadas (`adapted`).
   - **`spark-performance`:** entra adaptado: sin marcas de citas rotas y con el reporte escrito solo a pedido.
   - **graphify:** versión aprobada **0.9.73** (la investigación decía 0.9.2). `graphify vscode install`
     instala la skill a nivel de usuario (`~/.copilot/skills`) y agrega una sección `## graphify` a
     `copilot-instructions.md`; su uninstall la quita también a nivel de usuario. Esto se documenta en la
     guía de usuario.
   - **Bug de convivencia encontrado en la prueba real:** el uninstall de graphify se llevaba el marcador
     de inicio del bloque de cuypilot. Se corrigió poniendo el marcador en la línea del encabezado H2
     (ver CHANGELOG 0.2.0).

## Enmienda 2026-10-01: solo pip (sin uv ni pipx)

En el entorno de trabajo **no se pueden usar uv ni pipx**. Cambios:

- **Herramientas:** el catálogo ya no guarda comandos de instalación, sino el paquete fijado
  (`package = "graphifyy==0.9.73"`). cuypilot lo instala con
  `python -m pip install <paquete>` usando **el mismo Python con el que corre cuypilot**, es decir, el
  entorno virtual del proyecto. Para encontrar los ejecutables de las herramientas (`graphify`,
  `pyspark-antipattern`), busca también en la carpeta `bin`/`Scripts` de ese entorno, aunque no esté
  activado.
- **Consecuencia:** cada herramienta queda instalada en el entorno virtual del proyecto, no a nivel de
  usuario. Copilot la encuentra en las terminales de VS Code que tengan ese entorno activado (la extensión
  de Python lo activa por defecto).
- **Build y desarrollo de cuypilot:** el backend pasa de `uv_build` a `hatchling` (estándar, desde PyPI; se probó `setuptools`, pero da advertencias con las carpetas de datos que contienen `.py`). El build se hace con
  `python -m build` y el desarrollo con `pip install -e . --group dev`.
- **CI:** `actions/setup-python` + pip (funciona también en runners de GitHub Enterprise).
