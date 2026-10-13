# Lineamientos de gobernanza del catálogo de analytics

Estos lineamientos orientan cómo contribuir, revisar y mantener el catálogo del equipo. No añaden
controles automáticos ni requieren implementar ahora la evolución técnica del RFC-006.

Hoy existen catálogo, versiones, locks, CI y plantilla
de PR; responsables, reglas del proveedor y canal de distribución deben configurarse con datos reales.
Consulta la [evaluación](research/evaluacion-gobernanza-analytics.md) para conocer las brechas y
[RFC-006](rfc/RFC-006-gobernanza-analytics.md) para la evolución propuesta.

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

El mantenedor publica un wheel inmutable por versión con CHANGELOG y checksum en el canal acordado.
Hoy CI deja un artifact en tags; todavía falta definir retención y acceso del equipo. Conserva la
versión anterior para reversión y separa piloto de adopción general. No publiques experimental como
aprobado. Un incidente debe identificar wheel, pieza, destino, síntoma, mitigación y fix o retirada.
Reevalúa cuando cambien fuente, adaptador, cliente, permisos o modelo relevante.

Configura responsables reales en CODEOWNERS y protección de rama con CI y revisión obligatorios.
La plantilla de PR documenta el acuerdo, pero no activa estos controles. Para Genie compartido,
coordina ubicación y ACL con el administrador; no uses un deploy de proyecto a /Workspace como
atajo para gobernar todo el workspace.
