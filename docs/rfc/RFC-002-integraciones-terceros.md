---
type: rfc
proyecto: "cuypilot"
rfc: RFC-002
estado: borrador   # borrador | en-revision | aceptado | rechazado | superado
fecha: 2026-09-30
tags: [rfc, contrato, terceros]
---

# RFC-002 — Integraciones de terceros: skills externas y herramientas (graphify, codegraph, ponytail…)

> Extiende RFC-001 (`RFC.md`). **No se programa hasta que `estado: aceptado`.**

## 1. Contexto y problema

Fuera del equipo ya existen piezas muy probadas que resuelven bien parte de lo que queremos. Instalarlas
a mano en cada proyecto trae problemas:

- cada persona usa una versión distinta;
- nadie revisa la seguridad ni la licencia;
- algunas mandan datos fuera (telemetría, LLM externo) sin que se note.

Hay que ofrecerlas desde cuypilot con el mismo nivel de gobernanza que las piezas propias.

Investigación del 2026-09-30 (estrellas y licencia consultadas con la API de GitHub):

| Proyecto | ★ | Licencia | Qué es | Soporte Copilot VS Code |
|---|---|---|---|---|
| [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) | 149k | MIT | Modo "senior dev flojo": menos código, YAGNI, stdlib primero. Skills `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`… + hooks en Node | Reglas siempre activas (`copilot-instructions.md`). Sus `SKILL.md` son estándar, así que deberían funcionar como skills (hay que verificarlo) |
| [Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) | 123k | Apache-2.0 | CLI Python (`graphifyy`) que convierte el repo en un grafo de conocimiento consultable (tree-sitter, 40+ lenguajes) | `graphify vscode install` |
| [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) | 73k | MIT | Índice de código pre-construido con sincronización automática, expuesto como MCP | `codegraph install --target=copilot-vscode` + `codegraph init` por proyecto |
| [obra/superpowers](https://github.com/obra/superpowers) | 294k | MIT | Metodología en skills: `systematic-debugging`, `test-driven-development`, `verification-before-completion`, `writing-plans`… | Oficialmente solo para Copilot CLI; los `SKILL.md` son estándar |
| [anthropics/skills](https://github.com/anthropics/skills) | 179k | Mixta (por skill) | `skill-creator` (crear y evaluar skills), `mcp-builder`… | `SKILL.md` estándar |
| [github/awesome-copilot](https://github.com/github/awesome-copilot) | 40k | MIT | Incluye `spark-performance.agent.md` y `tdd-refactor.agent.md` | Nativo |
| [databricks/databricks-agent-skills](https://github.com/databricks/databricks-agent-skills) | 0.3k (oficial) | **Databricks License** | 31 skills oficiales (jobs, DABs, Unity Catalog, MLflow, Model Serving, pipelines…) | Soporta Copilot |

## 2. Objetivo

Desde la misma CLI, instalar con versión fijada y revisión previa:

1. **Piezas de terceros incluidas en el catálogo** (skills, agents, instructions copiadas de su repo
   original): se instalan igual que las propias, con lockfile y hashes.
2. **Herramientas externas** (graphify, codegraph): cuypilot ejecuta su instalador oficial con una
   versión aprobada y una configuración segura para la empresa, y deja constancia en el lockfile.

**Hecho =** `cuypilot add ponytail graphify` deja ponytail funcionando como skills en Copilot y graphify
instalado y conectado a VS Code. Además, `cuypilot status` informa su estado.

## 3. Alcance

**Dentro:**
- Metadatos de origen para piezas de terceros y validación de licencia en el CI.
- Un tipo nuevo de pieza, `tool`, con instalación delegada al instalador oficial.
- Piezas iniciales (propuesta, sujeta a las decisiones de la §10):

| Pieza cuypilot | Origen | Tipo |
|---|---|---|
| `ponytail` (+ `ponytail-review`, `ponytail-audit`, `ponytail-debt`) | ponytail | skills incluidas en el catálogo (**sin hooks**) |
| `systematic-debugging`, `test-driven-development`, `verification-before-completion` | superpowers | skills incluidas en el catálogo |
| `spark-performance` | awesome-copilot | agent incluido en el catálogo |
| `skill-creator` | anthropics/skills | skill incluida en el catálogo, **para quienes contribuyen a cuypilot** (verificar su licencia) |
| `graphify` | graphify | tool |
| `codegraph` | codegraph | tool |

**Fuera (no-objetivos):**
- Hooks de terceros: ponytail los trae en Node, y un hook es ejecución arbitraria de código.
- Skills de `anthropics/skills` con licencia propietaria (docx, xlsx, pdf, pptx).
- Copiar las skills de Databricks dentro del catálogo (su licencia lo restringe; ver §10).
- Sincronización automática con los repos originales: las actualizaciones entran por PR.
- Paquetes por rol (`--bundle data-engineer`): queda para más adelante, cuando haya uso real.

## 4. Propuesta

### 4.1 Piezas de terceros incluidas en el catálogo

Son skills, agents o instructions normales del catálogo, con un bloque `upstream` en `catalog.toml`:

```toml
[items.ponytail-review]
type = "skill"
version = "1.0.0"                     # versión cuypilot de la pieza
description = "..."
[items.ponytail-review.upstream]
repo = "DietrichGebert/ponytail"
ref = "<commit sha>"                  # commit exacto revisado
path = "skills/ponytail-review"
license = "MIT"
adapted = false                       # true si se modificó para Copilot (se documenta qué)
```

- La carpeta de la pieza incluye el `LICENSE` original (MIT y Apache-2.0 exigen conservar el aviso).
- Validación nueva en el CI:
  - `upstream` completo (`repo`, `ref` de 40 caracteres, `license`);
  - archivo de licencia presente;
  - licencia dentro de una lista permitida (`MIT`, `Apache-2.0`, `BSD-*`).
- **Adaptación:** algunas skills de terceros mencionan herramientas que solo existen en Claude Code
  (por ejemplo `TodoWrite` o subagentes `Task`). Si hay que adaptarlas, se marca `adapted = true` y el
  cambio se describe en el PR. Lo mínimo indispensable; no se reescriben.
- **Actualizar desde el original:** un PR que cambia `ref`, muestra el diff y pasa el checklist de seguridad.

### 4.2 Tipo `tool`

```toml
[items.graphify]
type = "tool"
version = "0.9.2"                      # versión aprobada de la herramienta
description = "Grafo de conocimiento del repo para Copilot (tree-sitter, local)."
license = "Apache-2.0"
install = ["uv tool install graphifyy==0.9.2"]
configure = ["graphify vscode install"]
check = "graphify --version"
uninstall = ["graphify vscode uninstall"]
gitignore = ["graphify-out/", "graph.json"]
notes = "Usar --code-only: el pase semántico sobre docs envía contenido a un LLM."
```

Comportamiento:
- **`cuypilot add graphify`**:
  1. Muestra exactamente los comandos que va a ejecutar y pide confirmación (`--yes` la omite).
  2. Ejecuta `install` solo si `check` falla o la versión no coincide.
  3. Ejecuta `configure` en el workspace.
  4. Agrega las líneas `gitignore` a `.gitignore`.
  5. Registra en el lockfile la herramienta y su versión, **sin hashes**: los archivos los gestiona la
     propia herramienta (graphify, por ejemplo, refresca sus skills al actualizarse).
- **`--dry-run`:** solo muestra los comandos. Sirve cuando la red de la empresa bloquea la instalación y
  hay que hacerla por otra vía.
- **`status`:** ejecuta `check` y compara la versión instalada con la aprobada (`ok` / `desactualizada` / `no instalada`).
- **`remove`:** ejecuta `uninstall` (la configuración del proyecto). La herramienta global se deja, y se
  avisa cómo quitarla.
- Los comandos los define el catálogo, que pasa revisión por PR; el usuario no puede inyectar comandos.
  Se ejecutan con `subprocess.run` y lista de argumentos (sin shell).

### 4.3 Valores por defecto seguros para la empresa (en `notes` y en la instrucción de cada pieza)

| Herramienta | Riesgo | Valor por defecto |
|---|---|---|
| graphify | Al documentar, el pase semántico envía el contenido a un LLM, y elige el proveedor según la API key que encuentre en el entorno (incluye proveedores fuera del país) | Documentar `--code-only`; si se necesitan docs, `--backend` explícito y aprobado |
| codegraph | Telemetría anónima activada por defecto; aumenta el contexto que queda cargado (~80% más, según su propio benchmark) | Desactivar la telemetría en `configure`; documentar el costo de contexto |
| ponytail / superpowers | Instrucciones de terceros que el modelo sigue | Revisión con el checklist de seguridad; sin hooks |

## 5. Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Instalar desde los marketplaces de plugins originales (ponytail y superpowers los tienen) | Se descarta por las mismas razones de ADR-001: instalación por persona, sin versión en el repo, red externa. |
| Descargar del repo original al momento de instalar | Depende de GitHub.com desde la red de la empresa y no garantiza que lo instalado sea lo revisado. |
| Copiar el contenido de graphify/codegraph en vez de usar su instalador | Ambas tienen binarios, MCP y su propia gestión de versiones; copiarlas sería un fork difícil de mantener. |
| Solo documentar en el README cómo instalarlas a mano | Es simple, pero no hay versión fijada, ni estado, ni valores seguros. Sigue disponible con `--dry-run`. |

## 6. ¿Agente LLM?

No. Se mantiene determinista: se copian archivos y se ejecutan comandos aprobados.

## 7. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Demasiadas skills activas compiten entre sí (ponytail + superpowers + propias ≈ 15) | Instalación selectiva; evals de coexistencia. En particular, `ponytail-review` y `design-review` se solapan (ver §10). |
| Licencias | Lista permitida en el CI, LICENSE copiado y `upstream.license` obligatorio. Databricks queda fuera del catálogo. |
| Una pieza de terceros cambia de forma maliciosa | `ref` fijado a un commit; cada actualización es un PR revisado. |
| La red de la empresa bloquea npm, PyPI o GitHub | `--dry-run`; cuando Artifactory esté listo, los `install` apuntan al proxy. |
| Las herramientas cambian sus comandos de instalación | Fijar la versión; `check` detecta desajustes; probar en cada actualización. |
| codegraph necesita Node o descargar un binario | Prerrequisito documentado; si no se puede, se queda fuera. |

## 8. Plan de entrega

1. Modelo `upstream` + validación de licencias en el CI.
2. Incluir ponytail (sin hooks) y probarlo en VS Code; evals de coexistencia con `design-review`.
3. Incluir las 3 skills de superpowers y `spark-performance`; adaptarlas solo si hace falta.
4. Tipo `tool` en la CLI (`add`/`status`/`remove`, `--dry-run`, `--yes`) + tests con comandos simulados.
5. `graphify` y `codegraph` en el catálogo con sus valores seguros; probarlos en VS Code.
6. CHANGELOG, README y release `v0.2.0`.

## 9. Criterios de aceptación

- [ ] El CI falla si una pieza de terceros no tiene `upstream`, no tiene LICENSE o su licencia no está en la lista permitida.
- [ ] `cuypilot add ponytail-review` instala la skill con su LICENSE, y aparece como `/ponytail-review` en VS Code.
- [ ] `cuypilot add graphify --dry-run` muestra los comandos y no ejecuta nada.
- [ ] `cuypilot add graphify` (con confirmación) deja graphify utilizable desde Copilot Chat y `graphify-out/` en `.gitignore`.
- [ ] `cuypilot status` muestra la versión instalada y la aprobada de cada herramienta.
- [ ] Los comandos de una herramienta se ejecutan sin shell y solo si vienen del catálogo.
- [ ] Las evals de coexistencia entre `ponytail-review`, `design-review` y `python-refactor` están documentadas, y sus resultados registrados.

## 10. Preguntas abiertas

1. **¿Qué es "codepgrah"?** Asumo [colbymchenry/codegraph](https://github.com/colbymchenry/codegraph) (73k★). La alternativa sería [CodeGraphContext](https://github.com/CodeGraphContext/CodeGraphContext) (4k★, MCP + base de grafos).
2. **graphify y codegraph se solapan** (los dos dan un grafo del código a Copilot). ¿Ofrecemos ambas o elegimos una? Recomiendo **graphify** para empezar: es Python (`uv tool`), sin Node y sin telemetría.
3. **`ponytail-review` y `design-review` se solapan.** Opciones: (a) mantener ambas y dejar que las evals decidan; (b) quedarnos con `ponytail-review` y orientar `design-review` solo a SOLID y PySpark; (c) no incluir `ponytail-review`.
4. **¿La CLI ejecuta los instaladores (con confirmación) o solo los muestra?** Recomiendo ejecutar con confirmación + `--dry-run`.
5. **Skills oficiales de Databricks:** su licencia no permite copiarlas con seguridad en el catálogo. ¿Las tratamos como `tool`, delegando en su instalador oficial (hay que verificar el comando), o se quedan fuera?
6. **¿La red de la empresa permite instalar desde PyPI, npm y GitHub releases?** Esto define si graphify y codegraph son viables desde el día 1.
