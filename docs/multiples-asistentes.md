# Usar el mismo wheel con varios asistentes

cuypilot 0.5.1 distribuye un catálogo versionado para **GitHub Copilot en VS Code**, **OpenCode** y
**Genie Code de Databricks**. La CLI se ejecuta en tu terminal. Cada instalación pertenece al proyecto
que indiques con `--path` (por defecto, el directorio actual).

## Instalar y elegir destino

En el entorno virtual de desarrollo:

```bash
pip install <ruta>/cuypilot-0.5.1-py3-none-any.whl
cuypilot init
```

El wizard pregunta el asistente antes del rol. También puedes instalar sin preguntas:

```bash
cuypilot init --target copilot --role dev --yes
cuypilot init --target opencode --role mle --yes
cuypilot init --target genie --role docs --yes
```

Los tres pueden convivir en un proyecto. Los comandos existentes sin `--target` siguen usando Copilot.
Para operar desde otra carpeta:

```bash
cuypilot add python-standards python-design docs-writer --target opencode --path ./mi-proyecto
cuypilot list --target genie
cuypilot status --target opencode
cuypilot update --target opencode
cuypilot remove docs-writer --target opencode
```

`--target` y `--path` también pueden ir antes del subcomando. `list` identifica las herramientas
incompatibles; intentar agregarlas aborta antes de ejecutar instaladores o copiar archivos.

## Qué instala cada asistente

| Pieza | Copilot | OpenCode | Genie Code |
|---|---|---|---|
| Skill y recursos | `.github/skills/<nombre>/` | `.opencode/skills/<nombre>/` | `.assistant/skills/<nombre>/` |
| Agent | `.github/agents/<nombre>.agent.md` | `.opencode/agents/<nombre>.md`, modo `all` | Workflow adaptado a `.assistant/skills/<nombre>/SKILL.md` |
| Instruction | `.github/instructions/<nombre>.instructions.md` | `.opencode/instructions/<nombre>.md`, contenido incluido en `AGENTS.md` | `.assistant/instructions/<nombre>.md`, contenido incluido en `AGENTS.md` |
| Bloque base | `.github/copilot-instructions.md` | Bloque propio en `AGENTS.md` | Bloque propio en `AGENTS.md` |
| Lockfile | `.github/cuypilot.lock.json` | `.opencode/cuypilot.lock.json` | `.assistant/cuypilot.lock.json` |

Versiona estas carpetas y `AGENTS.md` cuando corresponda. Las adaptaciones conservan scripts, recursos,
licencias y dependencias. Los ejemplos de scripts cambian al destino correcto; ejecuta los comandos de
esos ejemplos desde la raíz del proyecto. Los archivos del catálogo original permanecen intactos.

Copilot usa sus skills con `/nombre` y agents con el selector. En OpenCode pide la skill por nombre;
sus agents están disponibles con `@nombre` y en el selector. En Genie usa `@nombre` para skills,
incluidos los workflows adaptados de agents. Esta adaptación conserva propósito, tipo original y
versión en el lock; no crea un agente nativo independiente en Genie.

El frontmatter exclusivo de Copilot se adapta. Por ejemplo, el uso manual de `improve-prompt` se
expresa en el cuerpo para otros asistentes; no se presupone que respeten `disable-model-invocation`.
Las condiciones de instructions como `**/*.py` se expresan en texto en `AGENTS.md`; fuera de Copilot,
su aplicación por tipo de archivo depende del asistente, no de un filtro nativo equivalente.

Formatos contrastados con la documentación oficial de [skills OpenCode](https://opencode.ai/docs/skills/),
[agents OpenCode](https://opencode.ai/docs/agents/), [reglas OpenCode](https://opencode.ai/docs/rules/),
[skills Genie Code](https://docs.databricks.com/aws/en/genie-code/skills) e
[instructions Genie Code](https://docs.databricks.com/aws/en/genie-code/instructions).

## Versiones y actualizaciones

Hay tres niveles diferentes:

- **Wheel:** versión del conjunto distribuido. Actualizar el paquete no cambia los archivos del proyecto.
- **Pieza:** versión fuente de skill, agent, instruction o programa externo; el lock conserva la instalada.
- **Archivo adaptado:** hash de lo instalado para el destino, incluidos recursos. Permite detectar cambios
  locales y cambios de adaptación sin inventar versiones distintas de la pieza fuente.
  Para tools también se guarda un hash de sus comandos, instrucciones y dependencias de integración:
  cambiar la integración se detecta aunque la versión del programa sea la misma.

`status` muestra instalada y catálogo, destino y estado. Compara versión **y** contenido, además de
las dependencias registradas. Por eso un cambio de versión con contenido idéntico se actualiza.
`update` actúa sobre un solo destino y mantiene las ediciones locales salvo `--force`. No descarga
versiones arbitrarias de piezas: para otro conjunto instala el wheel correspondiente y luego actualiza.
También puede restaurar el conjunto de un wheel anterior; revisa `status` antes de aplicar el cambio.

Las dependencias se guardan con la instalación y se usan al quitar piezas, incluso si el wheel nuevo
cambió sus dependencias. Los locks antiguos de Copilot siguen siendo legibles; las tools sin hash de integración se marcan
para actualizar su configuración. Donde falten metadatos
históricos se usa el catálogo disponible como antes.

Los bloques gestionados de `AGENTS.md` son independientes y preservan el contenido exterior y el bloque
del otro destino. Se registra su hash: si editas su interior, la operación se detiene. Para restaurarlo,
usa `update --force`; edita fuera del bloque para conservar instrucciones propias.

## Herramientas y entorno Python

| Herramienta | Copilot | OpenCode | Genie |
|---|---|---|---|
| `graphify` 0.9.73 | Integración VS Code e índice local | CLI e índice local; no cambia la integración de usuario de Copilot | No compatible |
| `pyspark-antipattern` 0.4.1 | CLI local | CLI local | No compatible |

Los paquetes se instalan con el mismo Python que ejecuta cuypilot y su versión queda fijada.
No se agregan automáticamente con `init --yes`: elige explícitamente las herramientas.
El wizard muestra los comandos y pide una confirmación. La CLI busca primero el ejecutable del entorno
Python actual y luego en `PATH`.

Los locks están separados, pero el programa de una tool se comparte si ejecutas ambos destinos en el
mismo entorno Python. Una actualización cambia ese programa compartido; `status` detecta su deriva.
Si necesitas versiones distintas al mismo tiempo, usa entornos Python diferentes.
`remove` protege archivos editados y exige `--force` para eliminarlos tras revisarlos.
`update` también protege recursos nuevos que colisionen con archivos ajenos.
`remove` desconecta la integración de ese destino y conserva el paquete instalado.
No se presenta una herramienta de tu portátil como instalada dentro de Databricks.

## Instalar en Genie Code desde la terminal

Tienes dos caminos:

1. Instala con `--target genie` en tu repositorio, haz commit y sincroniza su Databricks Git folder.
2. Publica los archivos gestionados en una carpeta del workspace con `deploy`.

Para publicar, necesitas la **CLI oficial de Databricks** y su autenticación configurada. cuypilot no
la instala, no guarda tokens y no modifica perfiles. El destino es la raíz del proyecto/notebooks donde
quieres que `AGENTS.md` se aplique, o tu carpeta de usuario para instrucciones heredadas desde ella.

```bash
cuypilot init --target genie --role mle --yes
cuypilot deploy --workspace-path /Workspace/Users/<usuario>/mi-proyecto --profile <perfil> --dry-run
cuypilot deploy --workspace-path /Workspace/Users/<usuario>/mi-proyecto --profile <perfil>
```

`deploy` usa Genie por defecto. `--target genie` también es válido; otros destinos se rechazan.
`--dry-run` consulta el remoto y muestra el plan sin publicar. Después de ver el plan, confirma la
publicación o usa `--yes` en automatización autorizada.

La CLI consulta el lock remoto, compara hashes y conserva archivos ajenos. Rechaza archivos modificados,
conflictos y bloques mal formados. `--force` permite sobrescribir conflictos remotos revisados; no omite
la validación de rutas. Se usan importaciones **RAW** para conservar `.py` como archivos y mantener
nombres y extensiones; no se hace `import-dir` de notebooks ni se borra ningún directorio recursivamente.

**Una vez en Genie Code**, abre Settings y registra la carpeta:

```text
/Workspace/Users/<usuario>/mi-proyecto/.assistant/skills
```

Es el registro de carpetas adicionales documentado por Databricks; no hay API de registro documentada
que esta CLI pueda automatizar. Si usas tu carpeta de usuario predeterminada `.assistant/skills`, Genie
ya la descubre. Abre un chat nuevo después de actualizar y, si quedan metadatos antiguos, refresca la
página. `AGENTS.md` se descubre al abrir notebooks o archivos debajo de su carpeta; registrar skills
no extiende esas instrucciones a notebooks de otros proyectos.

Para actualizar: instala el nuevo wheel, ejecuta `update --target genie` y vuelve a ejecutar `deploy`.
Para quitar: usa `remove --target genie` y luego `deploy`, que elimina solo los archivos previamente
registrados y conserva las instrucciones ajenas.

El despliegue remoto no es una transacción atómica. Publica el lock al final y reporta fallos parciales;
si falla, revisa el remoto y el nuevo plan. Una publicación parcial puede requerir `--force` tras revisar
los cambios. No ejecutes dos publicaciones simultáneas al mismo destino. El rollback de archivos locales
no revierte paquetes pip ni cambios remotos.

Comandos verificados contra la [referencia oficial de Workspace CLI](https://docs.databricks.com/aws/en/dev-tools/cli/reference/workspace-commands).
