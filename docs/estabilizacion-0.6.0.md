# Entrega de estabilización 0.6.0 y siguientes pasos

Fecha: 2026-11-12. Estado: implementación local preparada; pendiente de revisión, CI remoto y publicación.
Alcance autorizado: puntos 1–3 de la [evaluación inicial](reviews/2026-11-12/README.md).
Contratos: [RFC-008](rfc/RFC-008-manifiesto-y-flujo-reproducible.md) y
[RFC-009](rfc/RFC-009-estabilizacion.md).

## Entregado

| Punto | Resultado |
|---|---|
| 1. Integridad y recuperación | Rollback ante UTF-8 inválido y cierre de entrada; bloques huérfanos con adopción explícita; estado y plan propios del bloque base; `deploy --resume` limitado a igualdad de bytes; Releases parciales con checksum sobre los assets publicados |
| 2. Distribución verificable | Sdist y wheel construidos; smoke en venv limpio fuera del checkout, sin red; actualización real desde wheel 0.5.1; build y smoke configurados en PR y tags; herramientas directas y backend fijados |
| 3. RFC-008 | Manifiesto, reconciliación, modo frozen, edición transaccional entre destinos, migración, detección, consultas, dry-run y auditoría de integridad; guía y ejemplo de CI consumidor |

La CLI preserva su funcionamiento histórico sin manifiesto; `init` lo genera e `install` migra los locks.
La selección común, rangos admitidos y comportamiento de herramientas se explican en
[flujo reproducible](flujo-reproducible.md). No hay dependencias nuevas de ejecución.

## Evidencia local

- Python 3.14.2: **282 pruebas pasan**, con las 16 advertencias ya existentes de revisión manual del
  catálogo. `ruff check`, `ruff format --check` y `git diff --check` pasan.
- La mejora posterior de [UX/UI de terminal](diseno-cli.md) amplía la suite a **290 pruebas**; mantiene
  los mismos comandos y formatos persistidos.
- `python -m build --no-isolation` construye `cuypilot-0.6.0.tar.gz` y
  `cuypilot-0.6.0-py3-none-any.whl`; el wheel se construye desde el sdist.
- Smoke del wheel con Python 3.14 y Python 3.12: instalación local sin índice y sin dependencias,
  import desde site-packages del venv, catálogo/recursos/licencias incluidos y ciclo CLI en Copilot,
  OpenCode y Genie. Se verifica frozen, detección de ediciones, restauración explícita y retirada.
- Actualización real 0.5.1 → 0.6.0 en venv limpio con Python 3.14: el wheel anterior se construyó
  desde el commit base `ef93a30`; se instalaron piezas en los tres destinos, se actualizó el paquete,
  se migraron los locks y frozen pasó conservando instrucciones propias.
- Databricks y publicación de Releases se probaron con ejecutores simulados: fallos tras escrituras
  exitosas, reintento con lock antiguo, borrados parciales, conflictos ajenos y estados incompletos de assets.

No se ejecutaron aquí GitHub Actions, Windows, Python 3.11/3.13, herramientas externas reales,
Databricks real ni evaluaciones con LLM. La matriz remota configurada es Ubuntu Python 3.11–3.14
y smoke del wheel en Windows 3.11/3.14. Las simulaciones no acreditan permisos o compatibilidad del
servicio real. Los pins directos de desarrollo no son un lock de todas sus dependencias transitivas.

## Tags, artefactos y Release

Al subir un tag `vX.Y.Z`, el workflow valida que coincida con `pyproject.toml`, ejecuta pruebas,
construye sdist/wheel y guarda ambos en el artefacto **cuypilot-dist** de esa ejecución. El wheel lleva
su versión en el nombre. Después del smoke, el job de Release adjunta el wheel y `SHA256SUMS`.
También hay artefacto en PR; los artefactos de Actions tienen retención y la Release es el lugar de
distribución por versión. La publicación efectiva se verifica cuando el flujo corra en GitHub.

Crear un tag solo en local no activa el workflow. El repositorio no contiene un generador automático
de tags. Si en el futuro se agrega uno dentro de Actions, el push hecho con el `GITHUB_TOKEN` del
repositorio no genera otra ejecución de este CI: habrá que integrar las etapas en ese flujo o configurar
una invocación explícita/autenticación adecuada. Véase la
[documentación oficial de GitHub](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Siguientes pasos fuera de los puntos 1–3

1. **Revisión independiente y CI remoto.** Revisar especialmente migraciones, adopción `--force/--resume`,
   selección común y publicación. Ejecutar el PR en la matriz configurada y corregir cualquier diferencia
   de plataforma antes del tag. Verificar reglas de protección y permisos del job de Release en el proveedor.
   Terminado: checks requeridos verdes y revisión registrada.
2. **Piloto con asistentes reales.** En proyectos sintéticos, comprobar descubrimiento, activación,
   no activación y coexistencia para piezas críticas; probar instalación/retirada de tools en un venv
   desechable y deploy Genie en una carpeta de prueba autorizada. Registrar cliente/modelo, versión,
   caso, salida y limitaciones según `docs/gobernanza.md`. Terminado: evidencia versionada por destino,
   con fallos y destinos no ejecutados identificados.
3. **Resolver RFC-007 de contenido.** Acordar su alcance antes de implementar el escaneo: Unicode
   oculto, instrucciones sospechosas, capacidades y reglas AST. Añadir fixtures adversariales y reforzar
   modos de apertura/aliases en scripts. Conservar la separación entre hallazgos informativos y errores de
   integridad. Terminado: RFC acordada e informe evaluado contra fixtures y catálogo real.
4. **Asignar mantenimiento y completar distribución.** Definir owners del catálogo, activar CODEOWNERS
   y revisión requerida con equipos reales, decidir licencia propia y completar metadatos del paquete.
   Acordar revisión de terceros y cadencia de reevaluación. Terminado: responsables efectivos y proceso
   verificable en el proveedor, además de documentos accesibles en el repositorio.
5. **Adopción gradual y publicación.** Tras CI y piloto, publicar la versión acordada, verificar la descarga
   de wheel/checksum y migrar primero un consumidor con `install --frozen` y `audit --ci` como checks.
   Medir fallos, recuperación y facilidad de actualización antes de extender al equipo. Terminado: un
   consumidor reproducible y un procedimiento de actualización/retorno probado.

Después de esa evidencia se decidirá si hacen falta JSON para integraciones, tiempos máximos de procesos
o un contrato de API Python estable. No se añaden como requisitos hipotéticos de esta entrega.
