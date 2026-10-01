# Estado del arte — Personalización de GitHub Copilot (VS Code)

Fecha de la investigación: 2026-09-30. Insumo para `RFC.md`.

## 1. Tipos de personalización

| Tipo | Archivo / ubicación (workspace) | Uso | Estado (2026-09) |
|---|---|---|---|
| Instrucciones siempre activas | `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md` | Contexto y reglas globales del proyecto | Vigente |
| Instrucciones por archivo | `.github/instructions/*.instructions.md` (`applyTo: "**/*.py"`) | Estándares por lenguaje o carpeta | Vigente |
| Agent Skills | `.github/skills/<name>/SKILL.md` (+ scripts/recursos); también `.claude/skills`, `.agents/skills` | Flujos reutilizables con carga progresiva; se invocan como `/name` | **Pieza central.** Estándar abierto (agentskills.io), ~40 clientes |
| Agentes a medida | `.github/agents/*.agent.md` | Roles con `tools`, `model`, `agents` (subagentes), `handoffs`, `target` | Vigente |
| Prompt files | `.github/prompts/*.prompt.md` | — | **Deprecados** para Agent Host → migrar a skills |
| Hooks | `.github/hooks/*.json` (SessionStart, PreToolUse, PostToolUse, Stop…) | Automatización determinista (p. ej. `ruff format` tras editar) | Vigente |
| MCP | `.mcp.json` (portable) | Herramientas externas | Vigente |
| Agent Plugins 1.0 | `plugin.json` + `skills/` + `mcp.json` + `com.github.copilot/{agents,hooks,commands}` | Empaquetado y distribución entre clientes | Estándar publicado el 2026-08-06 |

Frontmatter de `SKILL.md`: `name` (minúsculas/dígitos/guiones, ≤64), `description` (≤1024; es el
mecanismo de activación), opcionales `argument-hint`, `user-invocable`, `disable-model-invocation`, `context`.

Ajustes deprecados (no basar diseño en ellos): `chat.instructionsFilesLocations`,
`chat.agentSkillsLocations`, `chat.promptFilesLocations`, `chat.agentFilesLocations`.

## 2. Mecanismos de distribución existentes

1. **Marketplace de plugins**: repositorio Git con `marketplace.json`. Se registra con
   `chat.plugins.marketplaces` (configuración de usuario) o se recomienda desde el workspace con
   `extraKnownMarketplaces` + `enabledPlugins` en `.github/copilot/settings.json`. Soporta repos privados
   y fijar versión con `ref`. Actualización automática cada 24 h.
   - Gotcha: un error en `marketplace.json`/`plugin.json` hace que el plugin **no aparezca, sin ningún error**.
   - La instalación es por persona y no queda versionada en el repo del proyecto.
2. **Nivel organización/enterprise en GitHub**: agentes en `{org}/.github-private/agents/`, instrucciones
   de organización (GA desde 2026-04). En enterprise, `managed-settings.json` (`enabledPlugins`,
   `extraKnownMarketplaces`, `strictKnownMarketplaces`). Requiere administradores; no cubre skills por proyecto.
3. **Copia de archivos al repo** (manual, plantilla o herramienta): queda versionada y visible para todo el
   equipo y para el agente en la nube; el riesgo es la deriva respecto del origen.

## 3. Gobernanza: prácticas recomendadas

- Registro por pieza: propósito, dueño, versión, dependencias y estado de evaluación.
- Evals antes de publicar: 3–5 casos por skill (debe activarse / no debe / ambiguo). Probar coexistencia
  (que una skill nueva no le robe la activación a otras) y probar en varios modelos.
- Revisión de seguridad: scripts incluidos, llamadas de red, credenciales, instrucciones adversariales,
  rutas fuera del directorio. Separación de funciones: el autor no aprueba su propia pieza.
- Limitar las skills activas a la vez (las descripciones compiten por la atención) → agrupar por rol o
  dominio e instalar selectivamente.
- Empezar con skills específicas y consolidarlas después, solo si las evals lo justifican.
- Versionado semántico, versión fijada en consumidores, plan de rollback, commits firmados.

## 4. Ecosistema reutilizable

- `github/awesome-copilot`: referencia de estructura y validación en CI; poco contenido de Python/PySpark/Sphinx.
- `databricks/databricks-agent-skills`: skills oficiales de Databricks (estándar abierto).
- `vaquarkhan/data-engineering-agent-skills`: 73 flujos de data engineering (inspiración).

## Fuentes

- https://code.visualstudio.com/docs/agent-customization/overview
- https://code.visualstudio.com/docs/agent-customization/agent-skills
- https://code.visualstudio.com/docs/agent-customization/custom-agents
- https://code.visualstudio.com/docs/agent-customization/agent-plugins
- https://code.visualstudio.com/docs/agent-customization/hooks
- https://github.blog/changelog/2026-08-12-agent-plugins-1-0-in-vs-code-copilot-cli-and-the-copilot-app/
- https://github.blog/changelog/2026-04-02-copilot-organization-custom-instructions-are-generally-available/
- https://docs.github.com/en/copilot/how-tos/administer-copilot/manage-for-organization/prepare-for-custom-agents
- https://www.kenmuse.com/blog/creating-agent-plugins-for-vs-code-and-copilot-cli/
- https://platform.claude.com/docs/en/agents-and-tools/agent-skills/enterprise
- https://www.philschmid.de/testing-skills
- https://github.com/github/awesome-copilot
- https://github.com/databricks/databricks-agent-skills
