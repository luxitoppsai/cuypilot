# Contribuir a cuypilot

## Agregar o modificar una pieza

1. Crea el archivo en `src/cuypilot/catalog/` según su tipo:

   | Tipo | Ruta |
   |---|---|
   | skill | `skills/<name>/SKILL.md` (+ recursos opcionales en la misma carpeta) |
   | agent | `agents/<name>.agent.md` |
   | instruction | `instructions/<name>.instructions.md` |

2. Regístrala en `src/cuypilot/catalog/catalog.toml` con `type`, `version`, `description` y, si aplica, `owner` y `requires`.
3. Si es una skill o un agente, crea `evals/<name>.json` con al menos 3 casos, incluyendo `trigger` y `no-trigger` (ver los existentes).
4. Corre `pytest` (valida el catálogo) y `ruff check .` (instala lo necesario con `pip install -e . --group dev`).
5. Prueba la pieza en VS Code: en un proyecto de prueba, `pip install -e <ruta-a-cuypilot>` y `cuypilot add <name>`. Ejecuta tus evals a mano.
6. Abre un PR y completa el checklist.

## Reglas de contenido

- **Idioma:** las piezas van en **inglés** (el modelo las sigue mejor); la documentación para personas, en español. La instrucción base ya le pide a Copilot que responda en el idioma del usuario (ADR-002).
- **La `description` es el disparador.** Debe decir qué hace, **cuándo usarla y cuándo no** (y qué pieza usar en su lugar). Una descripción vaga hace que la skill no se active o que le robe la activación a otras.
- **Una responsabilidad por pieza.** Antes de crear una, revisa si ya existe una parecida para extenderla.
- **Directivas, no sugerencias:** "Use X", no "X might be a good idea".
- **Sin secretos, sin red y sin scripts** salvo que sea imprescindible; si los hay, se justifican en el PR.
- **Skills que no deben activarse solas** (por ejemplo, de uso explícito): `disable-model-invocation: true`.
- Usa solo el frontmatter estándar de VS Code; versión, dueño y dependencias van en `catalog.toml`.

## Scripts dentro de una skill

Si una parte del trabajo es determinista (contar, listar, medir), conviértela en un script en
`skills/<name>/scripts/` para que el LLM no gaste tokens haciéndolo. Se instala junto con la skill. Reglas
(las valida `tests/scripts/test_script_rules.py`):

- Solo librería estándar, compatible con Python 3.11.
- **Solo lectura:** reporta, no modifica archivos. Las ediciones las hace el LLM.
- Sin red.
- Salida compacta (una línea por hallazgo y un resumen al final), con `--json` opcional.
- Tests en `tests/scripts/test_<script>.py`.
- El `SKILL.md` indica cuándo ejecutarlo (`python .github/skills/<name>/scripts/<script>.py <path>`) y le pide al LLM leer solo lo reportado.

## Piezas de terceros

1. Verifica la licencia: solo `MIT`, `Apache-2.0`, `BSD-2-Clause` y `BSD-3-Clause`.
2. Copia la pieza desde un **commit concreto** del repo original. En skills, incluye el `LICENSE` en la
   carpeta. En agents e instructions (archivo único), agrega al final un comentario HTML con la fuente y el
   texto de la licencia.
3. En `catalog.toml`, agrega el bloque `upstream` (`repo`, `ref` con el sha completo, `path`, `license`, `adapted`).
4. Adapta **lo mínimo** (por ejemplo, referencias a herramientas exclusivas de Claude Code o a archivos que
   no se copian). Si adaptas algo, `adapted = true`, explícalo en el PR y deja un comentario
   `<!-- cuypilot: adapted - ... -->` donde cambiaste.
5. **Actualizar desde el original:** nuevo `ref`, diff revisado en el PR y checklist de seguridad completo.

## Herramientas (`type = "tool"`)

Para programas externos que tienen su propio instalador (por ejemplo `graphify`). En `catalog.toml`:

- `package` es el paquete de PyPI fijado a la **versión aprobada** (`nombre==versión`, igual a `version`); cuypilot lo instala con `python -m pip install` en el entorno virtual del proyecto (sin uv ni pipx).
- `configure`, `uninstall` y `check` son **listas de argumentos**: nunca un shell, `|` ni `&&`. `configure` y `uninstall` son opcionales (herramientas de solo terminal).
- `gitignore`: lo que la herramienta genera en el repo.
- `instructions`: regla de uso seguro que se agrega al bloque gestionado mientras esté instalada.

Pruébala de punta a punta en un entorno aislado (un `python -m venv` nuevo, sin activar, y con `HOME` temporal), incluyendo
`remove` y la convivencia con el bloque gestionado de `copilot-instructions.md`.

## Versionado

- **Pieza:** sube su `version` en `catalog.toml` cada vez que cambie su contenido (MAJOR si cambia su propósito o se renombra; MINOR si agrega comportamiento; PATCH si son correcciones).
- **Paquete (`pyproject.toml`)**, en cada release:
  - MAJOR: se quita o renombra una pieza, o hay un cambio incompatible en la CLI o el lockfile.
  - MINOR: piezas o comandos nuevos.
  - PATCH: correcciones.
- **Release:** sube `version` en `pyproject.toml`, actualiza `CHANGELOG.md`, crea el tag `vX.Y.Z` y haz push del tag. El CI construye el wheel y lo deja como artifact (localmente: `python -m build`).
