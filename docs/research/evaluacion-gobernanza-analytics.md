# Evaluación de cuypilot para un equipo de analytics

Fecha: 2026-10-08. Alcance: código, catálogo, README, RFC, CI, documentación y formatos oficiales.

## Dictamen

cuypilot tiene una buena base para distribuir un catálogo por proyecto: un wheel, runtime sin
dependencias externas, selección de piezas, dependencias, versiones y hashes por asistente.
Todavía no demuestra una gobernanza efectiva del catálogo de todo un equipo. Tener una pieza
instalable, una descripción y casos de evaluación no demuestra que esté aprobada ni que funcione
igual en tres clientes. El usuario reportó haberlo probado; falta incorporar evidencia reproducible
de esas pruebas al repositorio.

## Los tres escenarios

| Escenario | Lo que está bien | Diferencia o limitación | Uso recomendado para el equipo |
|---|---|---|---|
| Copilot en VS Code | Skills, agents e instructions en sus ubicaciones nativas; selección por proyecto | Depende de descubrimiento y activación del cliente; una instrucción de solo revisión no restringe permisos | Versionar instalación y lock en cada proyecto; verificar descubrimiento y ejecución en el cliente del equipo |
| OpenCode | Skills y agents nativos; reglas incorporadas en AGENTS.md | Agents en modo all sin permisos específicos; glob de instructions pasa a texto; uso manual pasa a recomendación | Configurar permisos del cliente según la tarea; probar activación automática y manual por separado |
| Genie Code | Skills compatibles y publicación mediante CLI oficial; conserva recursos y versiones | Agents se convierten en workflows de skills; tools del portátil no se instalan; directorios adicionales requieren registro | Para un proyecto, Git folder o deploy más registro; para todo el workspace, skills compartidas con administración y permisos explícitos |

Las skills compartidas de Genie están en `Workspace/.assistant/skills/`; las personales en
`/Users/{username}/.assistant/skills/`. El despliegue actual publica la raíz de un proyecto con
AGENTS.md y lock, por lo que no se recomienda apuntarlo a `/Workspace` para imitar una instalación
global: mezclaría instrucciones de proyecto con distribución de workspace. Esa publicación necesita
un modo propio y revisión administrativa. Registrar una carpeta adicional no hace global AGENTS.md.
Fuentes: [Databricks skills](https://docs.databricks.com/aws/en/genie-code/skills) e
[instructions](https://docs.databricks.com/aws/en/genie-code/instructions).

Las rutas de skills usadas son compatibles con la documentación de
[VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills) y
[OpenCode](https://opencode.ai/docs/skills/). Compatibilidad de archivos no significa equivalencia de
activación, permisos ni resultados. Cuypilot es un instalador determinista ejecutado desde terminal;
el cliente LLM ejecuta las tareas. Las tools actuales son programas CLI, no un registro general de
servidores MCP, credenciales ni permisos de herramientas.

## Hallazgos y prioridades

| Prioridad | Evidencia observada | Mejora y criterio de cierre |
|---|---|---|
| P0 — pérdida de cambios | remove eliminaba archivos editados; update protegía dependencias nuevas pero no recursos nuevos de una pieza instalada | Corregido en esta revisión: negativa sin force y regresiones en los tres destinos |
| P1 — responsabilidad y aprobación | CODEOWNERS contiene solo comentarios; owner es opcional y está vacío; PR pide aprobación independiente sin imponerla | Asignar responsables reales; exigir revisión y CI en el proveedor; comprobar las reglas efectivas. No se inspeccionó la configuración remota |
| P1 — evidencia de calidad | evals contiene prompts y expected, sin registros por cliente/modelo ni artefactos | Ejecutar casos con contexto limpio, inputs sintéticos y criterios observables; registrar cliente, modelo, versión del wheel/pieza, resultados y comparación con versión anterior |
| P1 — portabilidad semántica | Conversión de agents y globs; frontmatter de skill adaptado conserva solo name/description | Separar compatible de verificado; declarar cambios de semántica y probar recursos, metadatos y permisos por cliente |
| P1 — conflictos entre piezas | python-refactor espera optimizar UDF/withColumn; pyspark-optimize también; TDD obligatorio convive con reglas de tests proporcionales al riesgo | Acordar precedencia, ajustar descripciones y casos de coexistencia; demostrar routing con ambas instaladas |
| P1 — distribución del equipo | CI construye wheel solo con tag y lo sube como artifact; no hay canal interno definido | Elegir un único canal accesible al equipo, artefactos inmutables con checksum y procedimiento probado de promoción y reversión |
| P2 — CI y suministro | No hay smoke test del wheel en PR; actions usan tags; paquete directo de tool fijado, dependencias transitivas no | Probar wheel instalado en venv limpio en PR, permisos mínimos, revisar pinning y reproducibilidad; registrar límites sin prometer aislamiento de pip |
| P2 — instrucciones compartidas | OpenCode y Genie guardan su propia copia de reglas en AGENTS.md | Probar convivencia real; reducir duplicación sin perder locks independientes. Su efecto en tokens o conducta es una hipótesis, no una medición |
| P2 — documentación y wizard | Guía principal centrada en Copilot; contribución pedía pruebas solo en VS Code; roles dev/ds/mle/docs | Una entrada por tarea y asistente, ficha de uso por pieza y perfiles basados en tareas reales de analytics |
| P2 — cobertura de analytics | Predominio Python/PySpark/ML; no hay workflows específicos SQL, BI, métricas ni contratos de datos | Priorizar dos o tres tareas frecuentes del equipo; extraer conocimiento de runbooks e incidentes; evitar añadir skills genéricas por completar categorías |
| P2 — diagnóstico | status verifica hashes y versión, no descubrimiento del cliente, ACL ni contexto remoto | Diseñar diagnóstico con límites claros: archivos/entorno verificables automáticamente; cliente, registro y permisos requieren evidencia adicional |

No se recomienda una plataforma de agentes, un servicio central nuevo ni una base de datos para
resolver estas brechas. Git, revisión, CI, un canal de wheels y documentación bastan para la primera
etapa. El wheel aprobado fija un conjunto; no es un resolvedor independiente de versiones de cada
skill. Reversión requiere revisar cambios locales y, en Genie, volver a publicar; no es atómica.

## Qué debe gobernarse

- **Skills:** propósito, disparadores, ejemplos, recursos, propietario, versión, licencia y evidencia.
- **Agents:** además, capacidades y permisos reales del cliente; en Genie, equivalencia como workflow.
- **Tools:** versión e integración, efectos externos, datos/red, licencia, actualización y desconexión;
 la aprobación en el wizard no es sandbox ni política corporativa.
- **Instructions:** alcance, precedencia y excepciones; no son controles de acceso ni protección de PII.

Unity Catalog, permisos de workspace, permisos del cliente y controles del proveedor siguen siendo
los límites efectivos. Los hashes detectan cambios; no autentican por sí mismos quién aprobó un wheel.

## Prácticas de referencia

El estándar [Agent Skills](https://agentskills.io/specification) favorece metadatos portables y carga
progresiva. Sus [prácticas de creación](https://agentskills.io/skill-creation/best-practices) recomiendan
conocimiento específico obtenido de tareas reales. Su [guía de evaluación](https://agentskills.io/skill-creation/evaluating-skills)
propone comparar con una baseline y registrar resultados con evidencia. Aquí se adopta una primera
etapa manual y trazable; no se afirma que exista un benchmark automático del comportamiento LLM.

[GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners)
permite solicitar responsables; exigir su aprobación requiere configuración adicional de protección.
Un checklist no reemplaza esa configuración.

## Cambios aplicados y pendientes

Aplicado: protección de cambios locales al quitar y de archivos ajenos al actualizar, validación de
nombres de skills acorde al estándar, guía operativa de gobernanza y PR con evidencia por destino.
El RFC-006 define la evolución propuesta. No se asignaron identidades ficticias, no se configuraron
reglas remotas ni se publicó un wheel o skills compartidas.

Verificación final: 205 pruebas pasan (16 avisos existentes de revisión manual de contenido), ruff
check/format y diff sin errores. Se construyeron sdist y wheel 0.5.1; el wheel se instaló en un venv
limpio y se verificó add/status/remove para los tres destinos. Python local: 3.14; no se ejecutó aquí
la matriz CI 3.11–3.13. La suite inicial pasó 199 pruebas.

Las pruebas de archivos y CLI no son pruebas de comportamiento
de los asistentes. Los registros de resultados reales siguen pendientes; no se usaron credenciales
ni se ejecutó un deploy autenticado durante esta evaluación.
