---
rfc: RFC-008
estado: aceptado   # borrador | en-revision | aceptado | rechazado | superado
fecha: 2026-11-10
---

# RFC-008 — Manifiesto declarativo y flujo de instalación reproducible

## Problema

cuypilot instala piezas y registra en un lockfile lo que instaló, pero no hay un lugar donde un proyecto
**declare** qué quiere. El flujo actual depende de que alguien ejecute `init` o `add` a mano, y no existe una
forma de comprobar en el CI de un proyecto que lo instalado coincide con lo acordado.

Proyectos con el mismo problema ya lo resolvieron. [APM](https://microsoft.github.io/apm/) (Microsoft, MIT) es
el más completo; no es utilizable en nuestro entorno, pero sirve de referencia. Comparación de capacidades,
según su documentación oficial al 2026-11-10 (el contrato de su manifiesto figura como "working draft"):

| Capacidad en APM | En cuypilot hoy | Esta RFC |
|---|---|---|
| Manifiesto `apm.yml` con lo que el proyecto necesita | No existe; solo el lockfile de lo instalado | Sí: `cuypilot.toml` |
| `apm install` reproduce la instalación desde el manifiesto | `init` y `add` son manuales | Sí: `cuypilot install` |
| `apm install --frozen`: instalación para CI que falla si hay deriva | `status` informa, pero no sirve como puerta en CI | Sí: `install --frozen` |
| Lockfile con commit resuelto, hash del paquete y hash por archivo desplegado | Versión y hash por archivo | Ya existe |
| Varios asistentes en un mismo manifiesto, con detección automática | Un destino por comando y un lockfile por destino | Sí: `targets` y detección |
| `apm outdated` y `apm update --dry-run` | `update` sin vista previa; no hay `outdated` | Sí |
| `apm deps why` explica por qué hay una dependencia | `remove` falla indicando quién depende | Sí: `cuypilot why` |
| `apm install <pkg>` agrega la entrada al manifiesto y revierte si falla | `add` instala y revierte archivos, sin manifiesto | Sí: `add` y `remove` editan el manifiesto |
| `apm audit --ci`: comprobaciones de consistencia sin configuración | — | Sí: `audit --ci` (ver RFC-007) |
| Escaneo de Unicode oculto en cada instalación | — | Solo en `audit` (RFC-007); `install` no escanea |
| `apm-policy.yml`: permitir o denegar fuentes, exigir piezas, heredado por organización | — | No entra (decisión 2) |
| Fuentes git arbitrarias, registros y marketplaces | El catálogo viaja en el wheel | No entra |

## Decisión propuesta

### 1. Manifiesto `cuypilot.toml` en la raíz del proyecto

Se versiona con el proyecto, junto al lockfile. Es solo declarativo:

```toml
cuypilot = ">=0.6,<0.7"        # versiones del wheel con las que se probó este manifiesto
targets = ["copilot", "genie"] # opcional; por defecto, se detectan por las carpetas existentes
pieces = ["python-standards", "design-review", "pyspark-optimize"]
tools = ["pyspark-antipattern"]
```

- Los nombres son los del catálogo. No hay versión por pieza: el wheel instalado fija todas (un solo catálogo
  por wheel). La versión de una pieza se ve en el lockfile.
- Las dependencias entre piezas se resuelven desde el catálogo, como hoy.
- `cuypilot` es una restricción de versión del wheel: si no se cumple, la CLI avisa y no instala.

### 2. Comandos

| Comando | Qué hace |
|---|---|
| `cuypilot install` | Instala lo declarado en el manifiesto para cada destino y actualiza los lockfiles |
| `cuypilot install --frozen` | No cambia nada: **falla** si algún archivo instalado difiere del lockfile o del manifiesto. Pensado para el CI del proyecto |
| `cuypilot add` / `remove` | Instalan o quitan y **editan el manifiesto**; si la operación falla, el manifiesto se restaura |
| `cuypilot outdated` | Lista piezas instaladas con una versión distinta a la del wheel actual |
| `cuypilot update --dry-run` | Muestra qué cambiaría sin tocar nada |
| `cuypilot why <pieza>` | Indica qué piezas dependen de ella |
| `cuypilot audit --ci` | Comprobaciones de consistencia (archivos presentes, hashes coherentes con el lockfile, bloques gestionados íntegros) con código de salida; el contenido lo cubre la RFC-007 |

`init` sigue siendo el wizard: al terminar escribe el manifiesto. Un proyecto sin manifiesto sigue funcionando
con los comandos actuales; `cuypilot install` crea el manifiesto a partir de lo ya instalado si no existe.

### 3. Puerta en el CI de cada proyecto

Con `install --frozen` y `audit --ci` un proyecto puede exigir en sus PRs que las piezas commiteadas no se
hayan editado a mano ni se hayan quitado, y que coincidan con el manifiesto. Con `master` y `develop`
protegidas y checks requeridos, es lo que hace efectiva la constancia de qué piezas se usan. La guía incluye un
fragmento de workflow listo para copiar; descarga el wheel de la Release con el token del repositorio o de la
organización, que un repo privado necesita.

### 4. Detección de destinos

Sin `targets` en el manifiesto ni `--target`, los destinos se deducen de las carpetas existentes (`.github/` con
piezas de cuypilot, `.opencode/`, `.assistant/`). `init` sigue preguntando.

## Alcance

**Entra:** manifiesto, `install` y `install --frozen`, `add`/`remove` que lo editan, `outdated`,
`update --dry-run`, `why`, `audit --ci`, detección de destinos, fragmento de CI para consumidores, pruebas y guía.

**No entra:**
- Instalar piezas desde repos git o registros externos, marketplaces y niveles de confianza.
- Versión independiente por pieza en el manifiesto.
- Rangos semver de piezas y resolución transitiva entre fuentes.
- Avisar automáticamente a los proyectos de que hay un wheel nuevo.
- Bloquear instalaciones por hallazgos de contenido (la RFC-007 es informativa).

## Alternativas descartadas

- **Adoptar APM:** no es utilizable en el entorno de trabajo y no cubre Genie Code.
- **Manifiesto YAML o JSON:** TOML ya se usa en el catálogo y `tomllib` es de la librería estándar; para
  escribirlo se genera el texto a mano, ya que el manifiesto es corto.
- **Solo ampliar `status`:** informa, pero no declara intención ni reproduce una instalación desde cero.

## Criterios de aceptación

1. En un proyecto vacío, `cuypilot install` con un manifiesto produce los mismos archivos y lockfile que `init`
   con las mismas piezas.
2. `install --frozen` termina con éxito cuando todo coincide y falla (con la lista de diferencias) si se edita,
   borra o agrega un archivo gestionado.
3. `add` y `remove` actualizan el manifiesto; si fallan, el manifiesto y los archivos quedan como estaban.
4. Un wheel fuera de la restricción `cuypilot` del manifiesto produce un error claro antes de cambiar nada.
5. `outdated`, `update --dry-run` y `why` no modifican archivos.
6. Los proyectos sin manifiesto siguen funcionando con los comandos existentes.
7. `pytest`, `ruff check` y `ruff format --check` pasan; las guías documentan el manifiesto y el fragmento de CI.

## Decisiones tomadas

1. **Nombre y lugar:** `cuypilot.toml` en la raíz del proyecto. Es el mismo formato que `catalog.toml`, se lee
   con la librería estándar y su nombre dice quién lo usa.
2. **Política:** queda fuera de esta RFC. Con el catálogo dentro del wheel, "qué piezas se permiten" ya lo decide
   qué wheel se instala y qué pide el manifiesto de cada proyecto; una política heredada por organización aporta
   cuando hay varias fuentes. Se retoma si aparecen fuentes adicionales.
3. **Lockfiles:** se mantiene uno por destino (`.github/`, `.opencode/`, `.assistant/`) con un solo manifiesto.
   No rompe instalaciones existentes, cada destino sigue siendo independiente y `install --frozen` los revisa
   todos.
