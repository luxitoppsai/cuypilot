## Qué cambia
<!-- Piezas nuevas/modificadas o cambios de la CLI -->

## Checklist

**Contenido**
- [ ] Las piezas (SKILL.md, agents, instructions) están en **inglés**; la documentación para personas, en español.
- [ ] La `description` dice claramente **cuándo usar y cuándo no** la pieza (no le roba la activación a otras).
- [ ] Subí la `version` de cada pieza modificada en `catalog.toml` (semver) y lo anoté en `CHANGELOG.md`.

**Evals** (`evals/<pieza>.json`)
- [ ] Casos actualizados (trigger, no-trigger, coexistencia/edge).
- [ ] Los ejecuté a mano en VS Code con `cuypilot add` sobre un proyecto de prueba y el resultado es el esperado.

**Seguridad**
- [ ] Sin credenciales, tokens ni datos internos sensibles.
- [ ] Sin llamadas de red, URLs externas ni scripts; o, si los hay, están justificados y revisados.
- [ ] Sin instrucciones que pidan ocultar acciones, saltarse reglas o tocar rutas fuera del proyecto.
- [ ] Quien aprueba no es el autor.
