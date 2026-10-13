---
rfc: RFC-005
estado: aceptado
fecha: 2026-10-08
---

# RFC-005 — Un wheel para Copilot, OpenCode y Genie Code

El usuario solicita y confirma soporte para GitHub Copilot en VS Code, OpenCode y Genie Code de
Databricks desde la misma CLI, con versiones de skills, agents, tools e instructions.

## Problema y alcance

El catálogo y su contenido están acoplados a `.github`. Copiarlo a otras carpetas no adapta rutas,
frontmatter ni invocaciones. El estado actual compara contenido pero puede ignorar cambios de versión.

## Decisión

- Mantener un catálogo y un wheel, sin dependencias de runtime. Un módulo de destinos adapta rutas,
  frontmatter e instrucciones. La versión de la pieza identifica el contenido fuente; hashes identifican
  lo instalado, incluida su adaptación. Un cambio de adaptación se detecta por contenido.
- CLI con `--target copilot|opencode|genie`, después del subcomando, y `--path` para elegir proyecto.
  Copilot sigue como valor por defecto para mantener el uso existente. El wizard permite elegir destino.
- Lockfile por destino: `.github/cuypilot.lock.json`, `.opencode/cuypilot.lock.json` y
  `.assistant/cuypilot.lock.json`. Conservar compatibilidad con locks existentes de Copilot.
  Registrar destino, versión del wheel, versión de pieza, tipo original, dependencias y hashes.
  Para tools, registrar además el hash de configuración e instrucciones de integración por destino.
- Copilot mantiene sus archivos. OpenCode recibe skills en `.opencode/skills`, agents Markdown en
  `.opencode/agents` e instructions en un bloque propio de `AGENTS.md`, además de archivos trazables.
- Genie recibe skills en `.assistant/skills`. Al no haber formato documentado equivalente a custom
  agents, adaptar esos workflows a skills explícitamente identificadas como tales; mantener su tipo
  original y versión en el lock. Instructions en un bloque propio de `AGENTS.md`.
- Para skills de uso manual, dejar explícito el requisito en el cuerpo; no asumir que otros asistentes
  respetan `disable-model-invocation` de Copilot. Adaptar referencias y comandos de scripts.
- Tools: compatibilidad declarada por herramienta. Graphify usa su integración VS Code en Copilot
  y exclusivamente su CLI local en OpenCode, sin instalar ni quitar skills del usuario de Copilot.
  pyspark-antipattern puede instalarse localmente para Copilot/OpenCode. Genie no instala herramientas
  locales como si estuvieran disponibles en un cluster remoto. Rechazar operaciones incompatibles antes
  de mutar. Las dependencias guardadas se usan al quitar piezas; status compara versión y hashes.
- Instalación Genie: preparar archivos localmente en un Git folder sincronizable; añadir despliegue por
  la CLI oficial `databricks` a una carpeta explícita del workspace, con perfil opcional. No almacenar
  credenciales. La carpeta de skills del Git folder debe registrarse una vez en Settings de Genie Code;
  no hay API de registro documentada. No modificar instrucciones globales del administrador.
- Mantener rechazo de symlinks, conflictos, protección de ediciones locales y rollback local.

## Alternativas

Tres catálogos duplicarían mantenimiento. Una carpeta universal no cubre agents/instructions.
Un framework de plugins y el SDK Databricks no son necesarios: destinos concretos y CLI oficial bastan.
No resolver versiones arbitrarias desde internet: cada wheel define un conjunto aprobado. Varias
versiones de tools requieren entornos Python separados; status detecta la deriva del entorno compartido.

## Criterios de aceptación

- Un proyecto puede instalar y actualizar los tres destinos sin alterar los otros locks o bloques.
- Skills y scripts usan rutas correctas; agents OpenCode y adaptación Genie tienen frontmatter válido.
- Versiones, cambios locales y dependencias se detectan incluso con contenido idéntico o wheel anterior.
- Herramientas incompatibles y conflictos abortan antes de ejecutar comandos.
- Wizard muestra destino y compatibilidad; modo no interactivo conserva comportamiento determinista.
- Despliegue Genie valida destino, muestra plan, respeta archivos ajenos y modificaciones remotas.
- Regresiones, lint, build y prueba del wheel aislado; integración real con asistentes/Databricks se
  distingue de pruebas con ejecutores simulados.

## Fuentes verificadas

- https://opencode.ai/docs/skills/
- https://opencode.ai/docs/agents/
- https://opencode.ai/docs/rules/
- https://docs.databricks.com/aws/en/genie-code/skills
- https://docs.databricks.com/aws/en/genie-code/instructions
- https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands

## Verificación de entrega

- 199 pruebas pasan; `ruff check`, `ruff format --check` y `git diff --check` pasan.
- Wheel 0.5.0 instalado sin dependencias en un venv limpio: las 20 piezas de archivo se instalan en
  los tres destinos, con init/add/status/update/remove, convivencia de bloques y wizard Genie interactivo.
- Publicación Databricks probada con CLI simulada: perfiles, RAW, conflictos, hashes, eliminación de
  archivos registrados, errores de autenticación y fallos parciales.
- No hay OpenCode/Databricks CLI disponibles en este entorno y no se ejecutaron sesiones LLM ni un
  despliegue autenticado. Los formatos se contrastaron con fuentes oficiales; esa integración real
  permanece como verificación de uso, sin afirmar que se haya ejecutado.
