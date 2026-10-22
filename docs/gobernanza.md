# Lineamientos de uso, mantenimiento y aportes a cuypilot

Estos lineamientos orientan cómo contribuir, revisar y mantener el catálogo del equipo. No añaden
controles automáticos ni requieren implementar ahora la evolución técnica del RFC-006.

Hoy existen catálogo, versiones, locks, CI y plantilla
de PR; responsables, reglas del proveedor y canal de distribución deben configurarse con datos reales.
Consulta la [evaluación](research/evaluacion-gobernanza-analytics.md) para conocer las brechas y
[RFC-006](rfc/RFC-006-gobernanza-analytics.md) para la evolución propuesta.

## Alcance y responsabilidades

Aplica a quienes consumen el catálogo en sus proyectos y a quienes mantienen sus piezas,
adaptadores y CLI. La guía de usuario explica los comandos; este documento define cómo trabajar
con ellos en equipo. Son acuerdos de trabajo que requieren revisión humana.

| Rol | Responsabilidad |
|---|---|
| Usuario del catálogo | Elegir piezas, revisar los cambios y resultados del asistente, reportar problemas y mantener la instalación de su proyecto. |
| Autor de un aporte | Definir el problema, implementar el cambio mínimo, documentarlo y adjuntar verificaciones reproducibles. |
| Revisor de dominio | Evaluar utilidad, corrección, límites y convivencia con otras piezas; revisar evidencia de uso. |
| Mantenedor | Revisar integridad del catálogo y CLI, coordinar versiones, distribución, actualizaciones y retiradas. |
| Administrador del servicio | Configurar accesos y reglas del proveedor de Git o workspace cuando corresponda. |

Una persona puede cubrir varios roles, pero la revisión de un aporte debe hacerla alguien distinto
del autor. Cada proyecto consumidor decide quién coordina sus actualizaciones; no tiene que actualizar
automáticamente cada vez que se publique un wheel.

## Acuerdos de uso diario

- Instala solo las piezas necesarias para la tarea y usa la versión acordada en tu proyecto.
  Comprueba el destino: una adaptación entre asistentes puede cambiar la forma de invocación.
- Al pedir trabajo, indica objetivo, contexto, restricciones y cómo comprobar el resultado.
  Para cambios amplios, acuerda alcance y criterios de aceptación antes de implementar.
- Revisa el plan y los comandos que impliquen instalaciones, red, cambios de archivos o publicación.
  Las piezas orientan al asistente; no sustituyen los permisos ni la aprobación de acciones.
- Usa datos sintéticos o anonimizados para ejemplos y evaluaciones. No incluyas credenciales ni
  datos internos sensibles en prompts, reportes o evidencias del catálogo.
- Revisa el diff y ejecuta las comprobaciones pertinentes antes de aceptar código generado.
  La activación de una skill y una respuesta convincente no demuestran que el resultado sea correcto.
- Si necesitas adaptar una pieza localmente, conserva el cambio en Git y revisa `status` antes de
  actualizar. Propón al catálogo las mejoras reutilizables; no edites el lock para ocultar diferencias.
- Reporta resultados incorrectos, activaciones fuera de alcance e instrucciones contradictorias con
  un caso reproducible. Suspende el uso de la pieza en la tarea afectada si compromete el resultado.

## Responsables y contribución

[CONTRIBUTING.md](../CONTRIBUTING.md) explica cómo agregar y modificar piezas;
[CODEOWNERS](../.github/CODEOWNERS) contiene la plantilla de asignación de revisores.
El equipo debe completar esa plantilla con usuarios o equipos reales con acceso al repositorio.
Mientras solo contenga comentarios, no asigna revisores automáticamente.
La revisión obligatoria se configura por separado en el proveedor de Git.

## Usar el catálogo

1. Instala el wheel de la versión acordada en el entorno Python del proyecto; no necesitas instalar
  cuypilot dentro del cliente LLM. Sigue la [guía de los tres asistentes](multiples-asistentes.md).
2. Ejecuta `cuypilot init --target copilot`, `--target opencode` o `--target genie` en el proyecto.
  Elige solo piezas que necesitas; revisa dependencias y comandos de tools en el resumen.
3. Verifica `cuypilot status --target <destino>`. Abre el cliente y confirma que descubre la pieza.
  En Genie registra la carpeta adicional y usa un chat nuevo; AGENTS.md solo se hereda en su árbol.
4. Prueba un caso de uso real con datos sintéticos. Guarda el resultado y versiona archivos y lock.
5. Actualiza el wheel del entorno y luego `cuypilot update --target <destino>`. Revisa el diff y status.
  Si es Genie remoto, revisa `deploy --dry-run` y publica después. No cambies el lock manualmente.
6. Para retirar una pieza, revisa dependencias y usa `remove`. Archivos editados requieren revisar y
  aceptar explícitamente `--force`; respalda antes tus cambios. Para revertir, instala el wheel anterior,
  revisa status y actualiza; tools compartidas y publicación remota requieren revisión adicional.

## Proponer y promover una pieza

Se aceptan aportes de contenido, correcciones de CLI o adaptadores, documentación, casos de evaluación
y reportes de errores. No es necesario crear una pieza nueva para contribuir.

1. Revisa el catálogo y los RFC para evitar duplicados. Describe el problema, usuario afectado y
   resultado esperado en el PR o en un reporte del repositorio.
2. Para una función significativa o cambio de arquitectura, documenta primero problema, alcance,
   alternativas y criterios de aceptación en un RFC y acuerda su dirección. Para correcciones pequeñas
   o documentación, basta con un PR de alcance claro.
3. Trabaja en una rama y limita el cambio al objetivo. Sigue [CONTRIBUTING.md](../CONTRIBUTING.md)
   para rutas, versiones, licencias, scripts y comprobaciones.
4. Adjunta evidencia proporcional al cambio: una corrección de documentación no requiere ejecutar
   modelos; una pieza o adaptación necesita evaluar los destinos afectados. Marca lo no ejecutado.
5. Solicita revisión independiente y resuelve observaciones. El mantenedor incorpora el aporte cuando
   cumpla los criterios aplicables y coordina su publicación; fusionar un PR no actualiza instalaciones.

Para reportar un fallo, incluye versión de cuypilot y de la pieza, destino, entorno relevante,
pasos mínimos, resultado esperado y observado. Adjunta salida o diff sin secretos. Si se trata de
una exposición de datos, coordina primero un canal privado con el responsable del repositorio;
no publiques el contenido sensible en un issue.

Autor y responsable de dominio acuerdan una tarea concreta, límites y ejemplos. Mantén el contenido
fuente en catalog, versión/dependencias en catalog.toml y casos en evals. Para cada pieza documenta:

- Qué tarea resuelve, cuándo usarla y cuándo usar otra; un ejemplo completo de entrada y salida.
- Instalación e invocación por destino; recursos, dependencias y diferencias de comportamiento.
- Responsable real, licencia/procedencia, datos utilizados y efectos de scripts o tools.
- Criterios de éxito, restricciones, caso negativo y coexistencia con piezas cercanas.

La guía de usuario ya contiene inventario y combinaciones; amplíala con fichas cuando se modifique una
pieza. No añadas dependencias ni permisos hipotéticos. Las instrucciones no otorgan permisos.

Ejecuta primero validación automática; después, evals manuales en cada destino declarado. Un revisor
independiente examina contenido, cambios de versión, efectos y evidencia. La promoción estable necesita
CI verde, responsable, ficha y evidencia en los destinos publicados; no basta con que el instalador
copie archivos. Los estados de promoción todavía no son campos implementados ni filtros del wizard.

## Registrar evaluaciones

Adjunta al PR un archivo Markdown sin datos internos ni conversaciones con secretos. Usa esta ficha
por destino y pieza; `no ejecutado` significa pendiente, no aprobado:

```text
Pieza y versión:
Wheel y commit:
Asistente, versión del cliente y modelo (si está disponible):
Fecha y evaluador:
Contexto: proyecto sintético, otras piezas instaladas, permisos relevantes:
Caso de evals y entrada/fixture:
Invocación: descubrimiento, automática o manual:
Criterios observables:
Resultado: pasa / falla / no ejecutado:
Evidencia: salida, diff o artefacto anonimizado:
Comparación con versión anterior o sin skill:
Limitaciones y acciones pendientes:
```

Las tools necesitan además instalación/desconexión y verificación de efectos en entorno aislado.
Las instructions deben aparecer en el contexto esperado y no afectar un caso fuera de alcance.
En Genie valida el notebook real bajo la raíz prevista; una skill registrada desde otra carpeta no
prueba herencia de instructions. Si el modelo no revela qué skill cargó, registra esa incertidumbre.

## Mantener y distribuir

### Rutina de mantenimiento

Como pauta inicial, revisa mensualmente los reportes y piezas en uso, y antes de cada publicación
revisa todos los cambios incluidos. El equipo puede ajustar esta frecuencia según uso e incidencias.

| Momento | Acción | Registro esperado |
|---|---|---|
| Ante un reporte | Reproducir, determinar alcance y priorizar por impacto; indicar mitigación si existe. | Reporte o PR con versión y estado. |
| Revisión periódica | Revisar fallos recurrentes, duplicados, piezas sin uso y cambios de terceros; comprobar si requieren reevaluación. | Decisión y pendientes en el repositorio. |
| Antes de publicar | Revisar versiones, licencias, CHANGELOG, documentación y evidencia; ejecutar las comprobaciones de CI. | PR revisado con resultados y limitaciones. |
| Al publicar | Comprobar tag y versión, construir el wheel, calcular checksum y conservar la versión anterior. | Versión y artefactos identificables en el canal acordado. |
| En cada proyecto consumidor | Revisar notas de versión, actualizar en una rama, comprobar estado, diff y tareas habituales antes de integrar. | PR de actualización con archivos y locks afectados. |

Las comprobaciones actuales de CI son `ruff check .`, `ruff format --check .` y `pytest -q`.
La construcción por tag se describe en [CONTRIBUTING.md](../CONTRIBUTING.md#versionado).
Además de las pruebas automáticas, verifica instalación y actualización desde el wheel en un proyecto
aislado cuando cambien el empaquetado, la CLI, las herramientas o las adaptaciones.

### Publicación, incidentes y retirada

El mantenedor publica un wheel inmutable por versión con CHANGELOG y checksum en el canal acordado.
Hoy CI deja un artifact en tags; todavía falta definir retención y acceso del equipo. Conserva la
versión anterior para reversión y separa piloto de adopción general. No publiques experimental como
aprobado. Un incidente debe identificar wheel, pieza, destino, síntoma, mitigación y fix o retirada.
Reevalúa cuando cambien fuente, adaptador, cliente, permisos o modelo relevante.

Configura responsables reales en CODEOWNERS y protección de rama con CI y revisión obligatorios.
La plantilla de PR documenta el acuerdo, pero no activa estos controles. Para Genie compartido,
coordina ubicación y ACL con el administrador; no uses un deploy de proyecto a /Workspace como
atajo para gobernar todo el workspace.

Si una pieza falla, registra el alcance conocido y recomienda una versión anterior o su retirada
según el impacto. Corrige y reevalúa el caso antes de recomendar su adopción nuevamente. Si deja
de mantenerse, documenta el motivo, la alternativa y el efecto sobre dependencias; aplica las reglas
de versionado para quitarla del catálogo. La retirada del catálogo no borra copias ya instaladas:
cada consumidor debe revisar y ejecutar la actualización o eliminación correspondiente.

## Acuerdos pendientes del equipo

Antes de anunciar adopción general, deja registrados aquí o mediante enlaces a documentos del
repositorio los siguientes acuerdos. Hasta entonces no se consideran configurados:

- Mantenedores y revisores de dominio reales, con asignaciones en CODEOWNERS.
- Canal de distribución de wheels y checksums, acceso, retención y ubicación de versiones anteriores.
- Versiones de clientes y destinos evaluados, tareas del piloto y evidencia resultante.
- Canal de soporte y contacto privado para incidentes con datos sensibles.
- Responsables de actualización por proyecto y, si aplica, ubicación y permisos del workspace Genie.
