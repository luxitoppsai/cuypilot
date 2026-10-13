# RFC-006: catálogo gobernado para analytics

Estado: propuesta posterior a la evaluación del 2026-10-08. No implementada como sistema de promoción.

Acuerdo del 2026-10-12: mantener la gobernanza como [lineamientos Markdown](../gobernanza.md)
para lectura y adopción por el equipo. Las ampliaciones técnicas de este RFC permanecen como
opciones futuras; no son compromiso de implementación ni controles activos.

## Problema y alcance

El catálogo multiasistente distribuye piezas, pero no diferencia aprobación de compatibilidad ni
registra evidencia por destino. El equipo necesita responsables, instrucciones de uso, promoción,
actualización y retirada trazables. Abarca skills, agents, tools e instructions; conserva wheel, CLI,
Git y adaptadores actuales. No introduce un framework de agentes ni un servicio de catálogo.

## Alternativas

1. Solo checklist: sencillo, pero no impide publicar contenido sin evidencia ni responsables.
2. Metadatos y controles en repo, más configuración del proveedor: opción recomendada, incremental.
3. Plataforma central de gobernanza: descartada por complejidad sin necesidad demostrada.

## Propuesta

- Añadir ciclo de vida experimental/estable/deprecated en catalog.toml y ficha de uso por pieza.
  El contenido existente no se declara estable retrospectivamente sin evidencia.
- Hacer owner obligatorio para promoción estable; emplear identidades existentes y CODEOWNERS real.
- Registrar compatibilidad y evidencia por destino por separado. Un agent convertido a skill no es
  equivalencia nativa; registrar las pérdidas de alcance o permisos.
- Validar en CI metadatos, fichas, enlaces locales, referencias a evidencia y cambios de versión.
  La presencia de un registro no demuestra por sí misma su veracidad: sigue requiriendo revisión.
- Construir e instalar el wheel en PR; distribuir versiones inmutables con checksum desde el canal
  acordado. Mantener versión previa y procedimiento de reversión probado.
- Hacer visible estado y diferencias en list/wizard. Diseñar doctor solo para observaciones que el
  entorno permita comprobar, indicando qué requiere verificación manual en el cliente.
- Diseñar publicación Genie de skills de workspace separada de deploy de proyecto: alcance explícito,
  permisos administrativos, lock propio y protección de archivos ajenos; no publicar AGENTS global
  por accidente. No modificar controles remotos automáticamente.

## Criterios de aceptación

- Ninguna pieza estable sin dueño, ficha, licencia cuando corresponda y evidencia por destino declarado.
- No promocionar como verificado un destino con resultado pendiente o fallido.
- Un consumidor instala una versión acordada y conoce sus diferencias sin leer el código.
- Wheel y archivos coinciden en un entorno limpio; actualización y retirada protegen cambios locales.
- Un mantenedor reproduce promoción y reversión sin inventar rutas ni editar locks a mano.
- Evaluación de coexistencia resuelve solapamientos Python/PySpark y metodología de tests.
- Publicación Genie distingue personal, proyecto y workspace y documenta alcance de instrucciones.

## Decisiones que requieren datos del equipo

Responsables e identidades del proveedor, canal de wheels y política de acceso/retención, tareas de
analytics prioritarias, clientes/modelos soportados y permisos de workspace. No son bloqueantes para
corregir bugs o mejorar documentación; sí para afirmar gobernanza efectiva y desplegar globalmente.

## Secuencia

1. Guía y evidencia manual por destino, correcciones de integridad de archivos (esta revisión).
2. Dueños y reglas reales; piloto de dos o tres tareas frecuentes con casos sintéticos.
3. Metadatos, controles de promoción y wheel en PR; canal de distribución acordado.
4. Mejoras de wizard/diagnóstico y publicación workspace Genie, basadas en el piloto.

Fuentes y hallazgos: [evaluación](../research/evaluacion-gobernanza-analytics.md).
