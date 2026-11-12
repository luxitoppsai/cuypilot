# Evaluación técnica de cuypilot

Fecha: 2026-11-12. Base revisada: commit `ef93a30`, paquete `0.5.1`.

**Registro histórico:** este informe describe la base previa a la estabilización. El estado de las
correcciones y los siguientes pasos se registran en [la entrega 0.6.0](../../estabilizacion-0.6.0.md).
Las reproducciones de defectos de esta carpeta corresponden a esa base; las regresiones actuales viven
en `tests/test_stability.py`, `tests/test_manifest.py`, `tests/test_deploy.py` y `tests/test_release.py`.

**Diagnóstico:** la arquitectura es adecuada para el problema y merece conservarse. La CLI tiene una
base probada, pero todavía hay fallos de integridad y recuperación que impiden considerarla estable para
un uso generalizado sin supervisión. La completitud debe medirse contra sus contratos: la RFC-008 está
aceptada y pendiente de implementación; la RFC-007 sigue en borrador. Añadir más piezas al catálogo
no resuelve estas brechas.

Esta entrega evalúa el estado actual y deja evidencia reproducible. No modifica el código de ejecución,
no declara aprobadas propuestas nuevas y no certifica comportamiento en asistentes reales.

## Alcance y evidencia

Se revisaron los siete módulos Python de la librería, las pruebas, los adaptadores, los scripts del
catálogo, los casos de evaluación, el empaquetado, CI y las RFC relevantes. El catálogo contiene
22 piezas: 17 skills, 2 agents, 1 instruction y 2 tools.

| Comprobación local | Resultado observado |
|---|---|
| `.venv/bin/python --version` | Python 3.14.2 |
| `.venv/bin/python -m pytest -q` | 205 pasan; 16 advertencias de revisión manual del catálogo |
| `.venv/bin/ruff check .` | Pasa sobre el repositorio original |
| `.venv/bin/ruff format --check .` | Pasa; 75 archivos en el repositorio original |
| `.venv/bin/python docs/reviews/2026-11-12/reproduce.py` | Confirma los cuatro defectos descritos abajo, usando carpetas temporales y Databricks simulado |
| `.venv/bin/python -m build --no-isolation --outdir /tmp/cuypilot-review-dist` | No se pudo construir: falta `hatchling` en el entorno local |

La limitación del build corresponde al entorno, no demuestra un defecto del paquete. No se instalaron
dependencias ni se construyó un wheel nuevo. No se ejecutaron aquí Python 3.11–3.13, Windows, Linux,
instaladores de tools, servicios remotos ni evals con un LLM. El workflow declara Python 3.11–3.13 sobre
Ubuntu; leerlo no prueba que sus ejecuciones remotas hayan pasado. No se midió cobertura de líneas o ramas.

## Puntos fuertes

- **Alcance y arquitectura simples.** Solo biblioteca estándar en ejecución; `argparse`, `tomllib`,
  dataclasses y ejecutores sustituibles. No hay necesidad de frameworks de agentes, un servidor ni un
  sistema nuevo de plugins para estabilizar el producto.
- **Catálogo único y versionado.** El wheel fija un conjunto coherente; los hashes del contenido adaptado
  detectan cambios aunque no cambie la versión fuente. Las tools tienen un hash de integración separado.
- **Protección del proyecto consumidor.** Validación del lockfile, pertenencia de rutas, rechazo de enlaces
  simbólicos, protección de archivos ajenos y ediciones locales; dependencias históricas guardadas para
  no eliminar una pieza requerida por otra.
- **Pruebas con riesgos reales.** Hay regresiones de colisiones, rollback por errores de disco, archivos
  modificados, coexistencia de destinos y errores remotos. La inyección del ejecutor permite comprobar
  escenarios de Databricks sin credenciales.
- **Procedencia de terceros.** Commits concretos, licencias conservadas y validaciones automáticas. Esto
  facilita revisar actualizaciones; no constituye una auditoría de seguridad completa.
- **Documentación y decisiones explícitas.** Guías de consumo y contribución, RFC y distinción entre
  generar archivos compatibles y comprobar su uso por un asistente. La RFC-004 documenta correctamente
  los límites del rollback ante efectos externos, concurrencia y terminación abrupta.

## Hallazgos priorizados

P1: corregir antes de recomendar uso generalizado. P2: cerrar durante la estabilización. No se observó
un defecto que justifique asignar P0 con la evidencia disponible.

### H1 · P1 · Un error UTF-8 evita el rollback y deja una instalación parcial

**Confirmado:** en Genie, instalar `python-standards`, modificar su archivo con bytes UTF-8 inválidos y
agregar `python-design` produce `UnicodeDecodeError` al regenerar `AGENTS.md`. La nueva skill queda
copiada y registrada en memoria, pero no en el lockfile del disco.

**Causa:** `Workspace._transaction` (`src/cuypilot/workspace.py:253`) restaura ante `OSError`,
`CuypilotError` y `KeyboardInterrupt`; no incluye `UnicodeError`. La CLI sí captura ese error y devuelve
1, haciendo que el fallo parezca controlado aunque la operación no se haya revertido.

**Corrección propuesta:** validar el texto necesario antes de escribir y cubrir sus errores de
codificación en la transacción, manteniendo visible la causa. No ocultar excepciones con una captura
general. Convertir la reproducción en una regresión que exija igualdad de archivos y locks antes/después,
tanto en memoria como al abrir un `Workspace` nuevo; cubrir OpenCode y Genie.

### H2 · P1 · Un bloque con marcadores y sin lockfile se sobrescribe sin adopción explícita

**Confirmado:** con un `copilot-instructions.md` que contiene un bloque `cuypilot:start/end`, pero sin
lockfile, `add python-design` reemplaza su contenido sin `--force`. Puede ocurrir por un lock eliminado
o una copia parcial del proyecto. Se conserva el texto exterior, pero se pierde el interior sin aviso.

**Causa:** `Workspace._write_block` (`src/cuypilot/workspace.py:571`) reemplaza por marcadores; la
protección de `_transaction` requiere un `managed_hash` previo. El despliegue remoto ya rechaza un bloque
sin lock salvo adopción con `--force`; la operación local carece de esa protección.

**Corrección propuesta:** tratar el bloque huérfano como conflicto de propiedad y exigir `--force` para
adoptarlo. Probar los tres destinos y la conservación exacta del archivo si se rechaza la operación.

### H3 · P2 · Un despliegue parcial no se recupera con el reintento sugerido

**Confirmado con ejecutor simulado:** falla la segunda importación, después de publicar un primer archivo.
El lock remoto no se publica, como está previsto. Al reintentar, el primer archivo se considera ajeno y
se exige `--force`, aunque procede del intento anterior.

**Causa:** `GenieDeployment.deploy` (`src/cuypilot/deploy.py:72`) publica el lock al final, sin un registro
intermedio que acredite los archivos ya subidos. El mensaje sugiere volver a desplegar, pero el reintento
por defecto encuentra un conflicto. Las pruebas actuales fallan la primera importación, sin comprobar
recuperación tras una escritura exitosa.

**Corrección propuesta:** primero documentar recuperación y probar fallos en cada fase. Comparar una
adopción explícita que solo acepte bytes idénticos con un mecanismo de staging; elegir el más simple
que preserve archivos ajenos. No desactivar la comprobación general de propiedad para facilitar reintentos.
La política de adopción o staging necesita una decisión documentada antes de implementarse.

### H4 · P2 · La deriva de las instrucciones base queda fuera de `status` y del informe de `update`

**Confirmado:** instalar una skill y cambiar únicamente `base/copilot-instructions.md` en una copia del
catálogo mantiene `status: ok`. `update` informa que la pieza está al día, pero modifica el archivo de
instrucciones del consumidor al ejecutar `_save`.

**Causa:** `_status` compara el bloque instalado con su hash histórico, pero no con el bloque que
generaría el wheel actual. `_write_block` sí toma la base del catálogo nuevo. Falta representar el cambio
del bloque compartido como parte del estado y del resultado de la operación.

**Corrección propuesta:** comparar también el bloque esperado y reportar su actualización sin atribuirla
artificialmente a todas las piezas. Reutilizar esa comparación en el plan de `update --dry-run` de RFC-008.
Exigir que todo archivo modificado aparezca explicado en el plan o informe.

### H5 · P1 · La recuperación de una Release incompleta puede publicar un checksum incoherente

**Riesgo inferido del workflow; no ejecutado contra GitHub:** `.github/workflows/ci.yml:66–73` calcula
`SHA256SUMS` desde el wheel de esta ejecución. Si la Release ya contiene un wheel, lo conserva por nombre;
si falta el checksum, sube el recién calculado. Si el nuevo build tiene bytes distintos, ese checksum no
describe el wheel que realmente está publicado. El caso inverso también requiere verificar coherencia.

**Corrección propuesta:** al completar una Release, verificar hashes de los assets existentes y generar
el checksum sobre los bytes que se publicarán o ya están publicados. Ante una discrepancia, fallar con
un diagnóstico sin sobrescribir assets. Probar estados de Release vacía, completa y parcialmente creada
con un ejecutor simulado. Alinear README/CONTRIBUTING/gobernanza: actualmente dicen que una Release
existente no se modifica, pero CI sí agrega los assets que faltan.

## Brechas para una librería completa y mantenible

| Área | Estado observado | Mejora concreta |
|---|---|---|
| Reproducibilidad del consumidor | RFC-008 aceptada; no hay manifiesto, `install`, `--frozen`, `outdated`, `why`, `update --dry-run` ni `audit --ci` | Implementar el contrato existente, conservando proyectos sin manifiesto y locks por destino |
| Seguridad del contenido | Regex de secretos, advertencias y reglas AST parciales; RFC-007 en borrador | Resolver el alcance de la RFC-007 antes de implementar sus funciones; separar contenido informativo de consistencia con salida de error |
| Reglas de scripts | El AST inspecciona nombres y ciertos módulos; no es una restricción de ejecución | Añadir regresiones para modos `r+`/`rb+`, aliases y llamadas dinámicas relevantes. Hoy `open` permite cualquier modo que contenga `r`, incluidos modos que escriben |
| Evaluación del catálogo | Se valida que existan JSON de casos; no se ejecutan sus expectativas con un modelo | Versionar evidencia de una selección crítica por destino, con cliente/modelo, caso, resultado y límites; ampliar según cambios |
| Aprobación y responsables | 0 de 22 piezas tiene `owner`; CODEOWNERS solo contiene ejemplos comentados | Asignar responsables reales y verificar reglas en el proveedor. El repositorio solo permite constatar que faltan las asignaciones locales |
| Distribución | Tests desde instalación editable; build solo en tags; sin smoke test del wheel en CI | Construir e instalar el wheel en un entorno limpio en PR y verificar catálogo, recursos y ciclo add/status/update/remove para los tres destinos |
| Compatibilidad | `requires-python >=3.11` sin techo; CI solo Ubuntu con 3.11–3.13; guías mencionan Windows | Publicar una matriz comprobada e incluir al menos Windows y una versión reciente de Python si se declaran compatibles |
| Dependencias de desarrollo | Sin versiones fijadas ni restricciones; hatchling tiene solo mínimo | Fijar un conjunto de desarrollo/CI reproducible con actualización deliberada; conservar runtime sin dependencias |
| Automatización | `status` imprime texto y termina 0 aunque detecte modificaciones | Usar los códigos y comprobaciones de RFC-008; añadir JSON solo donde haya una necesidad real de integración |
| Contrato Python | Hay clases públicas, pero no se define una API Python estable | Mantener inicialmente el compromiso en la CLI y formatos persistidos; documentar qué imports son internos antes de prometer estabilidad de API |
| Procesos externos | `subprocess.run` captura toda la salida y no tiene timeout | Evaluar tiempos máximos por tipo de operación y mensajes de recuperación; no imponer el mismo límite a consultas y a instalaciones largas |
| Metadatos | Falta una licencia propia en la raíz y metadatos de proyecto como URLs | Decidir licencia del código propio y completar metadatos antes de ampliar distribución; conservar licencias de terceros |

La ausencia de evidencia versionada no prueba que nunca se hayan ejecutado evals manuales. Tampoco se
verificaron protecciones de rama, permisos remotos, vigencia de documentación de proveedores ni versiones
externas. Estas observaciones se limitan al contenido disponible en el repositorio.

## Secuencia recomendada y aceptación

1. **Integridad y recuperación, manteniendo la arquitectura.** Resolver H1 y H2 con regresiones;
   corregir H5 y añadir escenarios de Release parcial; definir y probar H3 y H4. Ninguna operación fallida
   debe dejar cambios locales gestionados sin registrar. Cada cambio aplicado debe tener un informe fiel.
   Los efectos externos de pip y tools siguen fuera del rollback según RFC-004.
2. **Distribución verificable.** Añadir smoke tests del wheel construido en un venv limpio, con un proyecto
   sintético por destino. Comprobar scripts, assets y licencias empaquetados; probar actualización desde
   una instalación anterior y conservación de cambios locales. Acordar la matriz y fijar herramientas de CI.
3. **Reproducibilidad, según RFC-008 ya aceptada.** Entregar manifiesto, instalación y validación frozen,
   detección de destinos, gestión del manifiesto en add/remove/init y comandos de consulta. Comprobar
   fallos sin mutaciones, dependencias transitivas y rollback entre destinos. Separar `audit --ci` de
   cualquier decisión aún pendiente sobre escaneo de contenido de RFC-007.
4. **Evidencia operativa del catálogo.** Registrar pruebas de descubrimiento, activación, no activación y
   coexistencia para piezas críticas en cada asistente; probar tools en venv aislado y Genie en un workspace
   sintético autorizado. Resolver responsables y el alcance pendiente de RFC-007.

Una versión candidata puede considerarse estable cuando los defectos P1 estén cerrados, las regresiones
de recuperación y las pruebas del wheel pasen en la matriz acordada, la documentación refleje capacidades
implementadas y la evidencia real de compatibilidad esté identificada. Para considerarla completa dentro
del alcance aprobado, deben cumplirse además los siete criterios de RFC-008. No hace falta convertirla
en una plataforma ni ampliar el catálogo para conseguirlo.

## Cómo volver a comprobar los defectos

```bash
.venv/bin/python docs/reviews/2026-11-12/reproduce.py
```

El script conserva los defectos como evidencia histórica mediante asserts del estado observado. No es una
suite que deba seguir pasando al corregirlos. Cada arreglo debe trasladar el escenario a `tests/` con
aserciones del comportamiento correcto. No usa red, no instala herramientas y no escribe fuera de
carpetas temporales. Las cifras iniciales de pruebas corresponden a la base revisada, antes de añadir
esta documentación.
