## Qué cambia
<!-- Piezas nuevas/modificadas o cambios de la CLI -->

## Checklist

**Contenido**
- [ ] Las piezas (SKILL.md, agents, instructions) están en **inglés**; la documentación para personas, en español.
- [ ] La `description` dice claramente **cuándo usar y cuándo no** la pieza (no le roba la activación a otras).
- [ ] Subí la `version` de cada pieza modificada en `catalog.toml` (semver) y lo anoté en `CHANGELOG.md`.

**Evals** (`evals/<pieza>.json`)
- [ ] Casos actualizados (trigger, no-trigger, coexistencia/edge).
- [ ] Probé cada destino declarado con `cuypilot add --target <destino>` y adjunté evidencia según `docs/gobernanza.md`; los destinos no ejecutados quedan identificados como pendientes.
- [ ] Registré wheel/pieza, cliente/modelo, entrada sintética, criterios observables, resultado y comparación con la versión anterior cuando corresponda.
- [ ] Documenté uso, responsable propuesto, dependencias y diferencias de agents, instructions y permisos por destino.

| Destino | Resultado: pasa / falla / no ejecutado | Evidencia y limitaciones |
|---|---|---|
| Copilot | | |
| OpenCode | | |
| Genie Code | | |

**Seguridad**
- [ ] Sin credenciales, tokens ni datos internos sensibles.
- [ ] Sin llamadas de red, URLs externas ni scripts; o, si los hay, están justificados y revisados.
- [ ] Sin instrucciones que pidan ocultar acciones, saltarse reglas o tocar rutas fuera del proyecto.
- [ ] Quien aprueba no es el autor.

La aprobación efectiva requiere responsables y reglas configurados en el proveedor. Este checklist no activa esos controles.
