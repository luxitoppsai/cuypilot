# Mejora de UX/UI de la CLI

Implementada sobre la versión candidata 0.6.0. El alcance es la presentación del flujo existente:
jerarquía visual, lectura en terminal, estados y acciones siguientes. Se conservan comandos, formatos
persistidos, selección e instalación; no se añaden dependencias.

## Problemas encontrados

- `--version` pasaba el logo ASCII a argparse, que colapsaba sus espacios y lo convertía en varias
  líneas desordenadas. Ahora imprime únicamente `cuypilot 0.6.0`.
- El catálogo mezclaba nombre, tipo, versión y descripción en una sola línea larga. Ahora agrupa por
  tipo y coloca la descripción debajo, ajustada al ancho disponible.
- El destino aparecía dos veces en `list`. Ahora hay un único encabezado; las consultas por destino
  conservan su contexto.
- `outdated` no explicaba un resultado vacío. Ahora distingue instalación vacía de instalación al día
  respecto al wheel actual, sin implicar que se haya consultado un registro remoto.
- Las ediciones locales se mezclaban alfabéticamente con piezas correctas. Ahora los problemas se
  muestran primero, con resumen y acciones concretas.
- Los informes de actualización necesitaban distinguir entre éxito, vista previa y piezas protegidas.
  Ahora usan `[OK]`, `[PLAN]` y `[!]`, además del motivo textual.

## Criterios visuales

- Encabezado: qué se está consultando y en qué asistente.
- Resumen: cuántas piezas/cambios hay y si algo requiere atención.
- Detalle: un nombre/estado por entrada; versión y explicación en una segunda línea cuando ayuda.
- Acción: comando siguiente completo y copiable. Nombres, rutas y comandos largos no se cortan para
  forzarlos a una columna; las descripciones sí se ajustan. No se promete ajustar cualquier ruta arbitraria.
- Color: cian para contexto/plan, verde para estado correcto y amarillo para atención. El significado
  permanece en el texto, con salida sin ANSI al redirigir, con `NO_COLOR` o con `TERM=dumb`.
- Wizard: logo solo con ancho suficiente, selección sugerida cuantificada, resumen de piezas nuevas
  y comandos externos, y cierre con resultado y siguientes pasos.
- Ayuda: recorrido inicial con cuatro comandos; `--version` siempre breve y sin decoración.

Se evita añadir una TUI con navegación por flechas, animaciones, tablas con bordes y frameworks: el
flujo numérico existente funciona en terminal y automatización. Esta decisión puede revisarse si se
observan problemas de uso reales. Los mensajes siguen siendo salida humana, sin contrato de parsing.

## Ejemplo de catálogo

Salida real con `COLUMNS=60 cuypilot list --type agent`, sin color:

```text
Catálogo · GitHub Copilot (VS Code)
  2 piezas · 0 instaladas · * instalada · ! no compatible

  Agentes (2)
    docs-writer  1.0.0
      Agente que documenta la API pública de un paquete
      Python con docstrings Sphinx.
    spark-performance  1.0.0
      Agente que diagnostica cuellos de botella de PySpark y
      propone reescrituras Spark-native (awesome-copilot).

  Instalar una pieza:
    cuypilot add <nombre>
  Filtrar catálogo:
    cuypilot list --type skill
```

## Verificación

Pruebas específicas de salida en 48/80 columnas, nombres y comandos íntegros, precedencia de cambios
locales, estados vacíos, ausencia de encabezados duplicados, versión de una línea y color por stream.
Se inspeccionaron salidas de ayuda, catálogo y estado en terminal y captura. La suite completa y el smoke
del wheel comprueban que la presentación conviva con los flujos de instalación existentes.
No se realizó todavía una prueba de usabilidad con usuarios ni una inspección visual en Windows.
