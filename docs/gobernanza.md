# Cómo trabajamos con cuypilot

Este documento describe cómo se usa, se mejora y se mantiene el catálogo en equipo. La
[guía de usuario](guia-usuario.md) explica los comandos y [CONTRIBUTING.md](../CONTRIBUTING.md) explica
cómo se escribe una pieza.

## Roles

| Rol | Responsabilidad |
|---|---|
| Usuario del catálogo | Elegir piezas, revisar lo que genera el asistente, reportar problemas y mantener la instalación de su proyecto. |
| Autor de un aporte | Definir el problema, implementar el cambio mínimo, documentarlo y adjuntar verificaciones reproducibles. |
| Revisor de dominio | Evaluar utilidad, corrección, límites y convivencia con otras piezas. |
| Mantenedor | Revisar la integridad del catálogo y la CLI, coordinar versiones, publicar y retirar piezas. |
| Administrador del servicio | Configurar accesos, protección de ramas y reglas del proveedor de Git. |

Una persona puede cubrir varios roles, pero la revisión de un aporte la hace alguien distinto de su autor.
Cada proyecto consumidor decide quién coordina sus actualizaciones y cuándo: no tiene que actualizar cada
vez que se publique un wheel.

`.github/CODEOWNERS` define quién revisa cada ruta del repositorio. En este repositorio trae la plantilla
comentada; al alojarlo en la organización se completa con los equipos reales y se activa la revisión
obligatoria en la protección de rama, que es lo que hace efectivo el requisito de revisión independiente.

## Uso diario

- Instala solo las piezas que necesitas y usa la versión acordada en tu proyecto. Muchas skills activas
  compiten entre sí y el asistente elige peor.
- Al pedir trabajo, indica objetivo, contexto, restricciones y cómo comprobar el resultado. Para cambios
  amplios, acuerda el alcance antes de implementar (`/improve-prompt` ayuda a armar el pedido).
- Revisa los comandos que impliquen instalar paquetes, usar la red, modificar archivos o publicar. Las piezas
  orientan al asistente: no sustituyen los permisos ni la aprobación de cada acción.
- Usa datos sintéticos o anonimizados en ejemplos y evaluaciones. No pongas credenciales ni datos internos
  en prompts, reportes o evidencias.
- Revisa el diff y ejecuta las pruebas antes de aceptar código generado. Que una skill se active y la
  respuesta suene convincente no demuestra que el resultado sea correcto.
- Si adaptas una pieza localmente, el cambio queda en Git y `status` la marca `modificada`. Si la mejora
  sirve a todos, propónla al catálogo. No edites el lockfile para ocultar diferencias.
- Reporta resultados incorrectos, activaciones fuera de alcance e instrucciones contradictorias con un caso
  reproducible. Si una pieza compromete el resultado de tu tarea, deja de usarla en esa tarea.

## Usar el catálogo en un proyecto

1. Instala el wheel acordado en el entorno virtual del proyecto (no en el cliente del asistente) y agrégalo
   a `requirements-dev.txt`.
2. Ejecuta `cuypilot init --target copilot`, `opencode` o `genie`. Elige solo las piezas necesarias y revisa
   las dependencias y los comandos de herramientas en el resumen.
3. Comprueba con `cuypilot status --target <destino>`, abre el asistente y confirma que descubre la pieza.
   En Genie registra la carpeta de skills y abre un chat nuevo; `AGENTS.md` se hereda solo dentro de su carpeta.
4. Prueba un caso real con datos sintéticos y haz commit de los archivos instalados y del lockfile: es el
   registro de qué piezas y versiones usa el proyecto.
5. Para actualizar: instala el wheel nuevo en una rama, ejecuta `cuypilot update --target <destino>`, revisa
   `status` y el diff, y abre un PR. En Genie remoto, revisa `deploy --dry-run` y publica después.
6. Para retirar una pieza usa `remove`. Si tiene archivos editados, exige `--force` tras revisar y respaldar
   tus cambios. Para volver atrás, instala el wheel anterior, revisa `status` y ejecuta `update`.

## Proponer y publicar una pieza

Se aceptan piezas nuevas, correcciones de contenido, de la CLI o de los adaptadores, documentación y casos de
evaluación.

1. Revisa el catálogo para no duplicar. Describe el problema, a quién afecta y el resultado esperado.
2. Si el cambio es una función significativa o de arquitectura, documenta primero el problema, el alcance, las
   alternativas y los criterios de aceptación, y acuérdalo con el equipo. Una corrección pequeña o de
   documentación solo necesita un PR de alcance claro.
3. Trabaja en una rama y limita el cambio a su objetivo. [CONTRIBUTING.md](../CONTRIBUTING.md) fija rutas,
   versiones, licencias, scripts y comprobaciones.
4. Adjunta evidencia proporcional: una corrección de documentación no requiere ejecutar modelos; una pieza o
   una adaptación se prueba en cada destino afectado. Lo que no se probó se marca como `no ejecutado`.
5. Un revisor distinto del autor examina el contenido, la versión, los efectos y la evidencia. El mantenedor
   incorpora el aporte cuando cumple los criterios y coordina la publicación. Fusionar un PR no actualiza las
   instalaciones existentes.

Una pieza queda lista para publicarse cuando el CI está verde, tiene responsable, una descripción que indica
cuándo usarla y cuándo no, casos de evaluación, y evidencia en los destinos que declara.

Para cada pieza se documenta qué tarea resuelve y cuándo usar otra, cómo se invoca en cada destino, qué
dependencias y efectos tiene (scripts, herramientas), su licencia y procedencia, y cómo convive con piezas
cercanas. El contenido fuente va en el catálogo, la versión y las dependencias en `catalog.toml` y los casos
en `evals/`.

### Reportar un fallo

Incluye la versión de cuypilot y de la pieza, el destino, el entorno, los pasos mínimos, el resultado esperado
y el observado, y la salida o el diff sin secretos. Si el problema expone datos, usa un canal privado con el
responsable del repositorio en lugar de un issue público.

## Registrar evaluaciones

Cada PR que agrega o cambia una pieza adjunta una ficha Markdown por destino y pieza, sin datos internos ni
conversaciones con secretos:

```text
Pieza y versión:
Wheel y commit:
Asistente, versión del cliente y modelo (si está disponible):
Fecha y evaluador:
Contexto: proyecto sintético, otras piezas instaladas, permisos relevantes:
Caso de evals y entrada o fixture:
Invocación: descubrimiento, automática o manual:
Criterios observables:
Resultado: pasa / falla / no ejecutado:
Evidencia: salida, diff o artefacto anonimizado:
Comparación con la versión anterior o sin la skill:
Limitaciones:
```

Las herramientas se prueban además instalando y desconectando en un entorno aislado y comprobando sus efectos.
Las instructions deben aparecer en el contexto esperado y no afectar casos fuera de su alcance. En Genie se
valida con un notebook real bajo la carpeta prevista: registrar una skill desde otra carpeta no prueba que se
hereden las instrucciones. Si el modelo no revela qué skill cargó, se registra esa limitación.

## Mantener y publicar versiones

| Momento | Acción | Registro |
|---|---|---|
| Ante un reporte | Reproducir, determinar el alcance, priorizar por impacto e indicar una mitigación. | Reporte o PR con versión y estado |
| Cada mes | Revisar fallos recurrentes, duplicados, piezas sin uso y cambios de terceros; reevaluar lo que cambió. | Decisión en el repositorio |
| Antes de publicar | Revisar versiones, licencias, CHANGELOG, documentación y evidencia; CI en verde. | PR revisado |
| Al publicar | Subir la versión en `pyproject.toml`, actualizar el CHANGELOG y crear el tag `vX.Y.Z`. El CI construye el wheel, lo guarda en `whl/` con su `SHA256SUMS` y conserva las versiones anteriores. | Tag y wheel en `whl/` |
| En cada proyecto consumidor | Leer las notas de versión, actualizar en una rama, revisar `status` y el diff, probar y abrir un PR. | PR de actualización con archivos y lockfile |

El CI ejecuta `ruff check .`, `ruff format --check .` y `pytest -q` con Python 3.11, 3.12 y 3.13. Cuando
cambian el empaquetado, la CLI, las herramientas o las adaptaciones, además se instala y actualiza desde el
wheel en un proyecto aislado.

Se publica un wheel inmutable por versión en `whl/`. Lo experimental no se publica como aprobado. Un incidente identifica
wheel, pieza, destino, síntoma, mitigación y corrección o retirada. Se reevalúa cuando cambian la fuente, el
adaptador, el cliente, los permisos o el modelo.

Para Genie compartido, la ubicación y los permisos de la carpeta del workspace se acuerdan con su administrador:
un `deploy` de proyecto no es una forma de gobernar todo el workspace.

Si una pieza falla, se registra el alcance conocido y se recomienda la versión anterior o su retirada. Se
corrige y se reevalúa antes de volver a recomendarla. Si deja de mantenerse, se documenta el motivo, la
alternativa y el efecto sobre sus dependencias, y se quita siguiendo las reglas de versionado. Retirar una
pieza del catálogo no borra las copias ya instaladas: cada proyecto ejecuta `update` o `remove`.
