---
rfc: RFC-007
estado: borrador   # borrador | en-revision | aceptado | rechazado | superado
fecha: 2026-11-10
---

# RFC-007 — Seguridad del contenido del catálogo

## Problema

Las piezas del catálogo (`SKILL.md`, agents, instructions y scripts) son texto que el asistente **obedece** y
código que se **ejecuta** en la máquina del desarrollador. Una pieza maliciosa o descuidada puede hacer que
el asistente inserte código ajeno, filtre credenciales o ejecute comandos sin que el usuario lo note.

Hoy la protección es casi toda manual:

- **Automática:** el CI valida licencias, que las piezas de terceros estén fijadas a un commit, y que los
  scripts usen solo la librería estándar, sean de solo lectura y no usen red (`tests/scripts/test_script_rules.py`).
- **Manual:** el checklist de seguridad de la plantilla de PR y la revisión de otra persona.
- **No existe** ninguna detección sobre el **texto** de las piezas: ni Unicode invisible, ni instrucciones de
  inyección, ni referencias a credenciales o a URLs externas. Es el hueco principal, porque ahí viven las
  instrucciones que el asistente sigue.

## Contexto del mercado

Investigación del 2026-11-10 (las cifras son de proveedores y no están verificadas de forma independiente):

- Snyk analizó 3.984 skills públicas: el 36,8 % tenía algún problema de seguridad y confirmó 76 payloads
  maliciosos ([ToxicSkills](https://snyk.io/blog/toxicskills-malicious-ai-agent-skills-clawhub/)). Otro estudio
  de 42.447 skills halló inyección de prompts en el 26 % ([SkillSieve](https://arxiv.org/html/2604.06550v1)).
- El ataque "Rules File Backdoor" ocultó instrucciones con caracteres Unicode invisibles en un archivo de
  reglas; Copilot y Cursor las siguieron e insertaron un script externo sin avisar
  ([Pillar Security](https://www.pillar.security/blog/new-vulnerability-in-github-copilot-and-cursor-how-hackers-can-weaponize-code-agents)).
- Las técnicas habituales: robo de credenciales, comandos disfrazados, rutado de datos a terceros, persistencia
  escribiendo en otros archivos de contexto, suplantación de nombres y prosa condicional
  ([CSA](https://labs.cloudsecurityalliance.org/research/csa-research-note-skill-md-agent-context-poisoning-20260506/)).
- Marco de referencia: [OWASP Agentic Skills Top 10](https://owasp.org/www-project-agentic-skills-top-10/)
  (AST01 skills maliciosas, AST02 compromiso de la cadena de suministro).
- Prácticas comunes en registros empresariales: un solo registro gobernado, escaneo automático más aprobación
  humana, versiones fijadas con hash, promoción por etapas y control en ejecución.
- Los escáneres se pueden evadir ([ColluSkill](https://arxiv.org/pdf/2608.09732)). El escaneo **reduce el trabajo
  del revisor, no lo reemplaza**.

## Decisión propuesta

Capas, de la más barata a la más cara. Todas corren en el CI de cada PR y las primeras también en local.

### 1. Auditoría determinista: `cuypilot audit`

Un módulo con la librería estándar (sin dependencias nuevas) que recorre las piezas del catálogo y reporta
hallazgos con identificador, severidad, archivo y línea. Sale con código distinto de cero si hay hallazgos
`alta`; `--json` para máquinas.

| Familia | Qué detecta | Severidad |
|---|---|---|
| Texto oculto | Caracteres Unicode de formato, dirección y bloque Tag (U+E0000–E007F); comentarios HTML con contenido (salvo los marcadores `cuypilot:` y las licencias de terceros); bloques base64 o hexadecimales largos | alta |
| Inyección | Frases como "ignore previous instructions", "ignora las instrucciones anteriores", "no se lo digas al usuario", "sin pedir confirmación", "no menciones" (español e inglés) | alta |
| Acceso sensible | Referencias a `.env`, `~/.ssh`, claves privadas, `credentials`, volcado de variables de entorno | alta |
| Red y exfiltración | URLs fuera de la lista permitida; `curl`, `wget`, `Invoke-WebRequest`, `\| sh`; `pip install` de paquetes no declarados | media |
| Ejecución en scripts | Por AST: `eval`, `exec`, `compile`, `__import__`, `subprocess`, `os.system`, `shell=True`, `pickle`, módulos de red, escritura de archivos | alta |
| Persistencia | Instrucciones que piden escribir o modificar `AGENTS.md`, `copilot-instructions.md`, `.github/`, `.vscode/` o ajustes de aprobación automática | alta |
| Frontmatter | Claves fuera del conjunto permitido; `tools` más amplio que lo declarado | media |
| Nombres | Nombre a distancia de edición ≤2 de otra pieza (suplantación) | media |

La lista de dominios permitidos y las excepciones justificadas viven en `catalog.toml`
(`[audit] allowed_domains` y `allow = [{ id, razón }]` por pieza). Como `catalog.toml` está en CODEOWNERS, toda
excepción pasa por revisión.

### 2. Capacidades declaradas

Cada pieza declara en `catalog.toml` lo que puede hacer: `capabilities = ["scripts", "network", "tools"]`
(vacío por defecto). La auditoría compara lo declarado con lo detectado: una capacidad detectada y no
declarada es un hallazgo alto. Así el revisor ve de un vistazo qué privilegios pide cada PR.

### 3. Escáner externo en el CI

Evaluar [Cisco skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) como **segundo juicio**
independiente de nuestras reglas. Datos verificados el 2026-11-10: código abierto con **licencia Apache-2.0**
(archivo `LICENSE`; la API de GitHub la informa como "NOASSERTION"), activo, con soporte para CI. Combina
reglas YAML/YARA, análisis de flujo de datos sobre los scripts y un juez LLM opcional. Se usaría **solo con
los modos que no necesitan LLM ni salida a red**. Entra primero como paso informativo; pasa a bloqueante
cuando se mida su ruido contra las piezas actuales.

### 4. Integridad de lo que se instala

- El lockfile ya guarda el hash de cada archivo y `cuypilot status` detecta ediciones locales y cambios del
  catálogo: no se agrega nada.
- Cada release publica el `sha256` del wheel junto al artifact. Los proyectos consumidores pueden fijarlo con
  `pip install --require-hashes` (mecanismo nativo de pip), sin código nuevo.
- Evaluar las atestaciones de procedencia de GitHub Actions si el GitHub Enterprise de la organización las ofrece.

### 5. Revisión humana

El escáner entrega un informe al revisor en lugar de un diff en bruto. La revisión independiente se hace
efectiva con CODEOWNERS y protección de rama configurados en la organización. Para scripts, herramientas y
agents con herramientas se recomienda un segundo revisor. Esto no se implementa en el repositorio: se
configura en el proveedor.

### 6. Pruebas

Un directorio de **piezas maliciosas de ejemplo** (una por familia de la tabla) que la auditoría debe rechazar
con el identificador esperado, y las piezas actuales del catálogo, que deben pasar. Las piezas de terceros
(ponytail, superpowers, awesome-copilot) se auditan igual: si alguna da un hallazgo legítimo, se corrige o se
registra una excepción justificada.

## Alcance

**Entra:** `cuypilot audit`, capacidades declaradas, evaluación del escáner de Cisco en el CI, hash del wheel en
cada release, pruebas con piezas maliciosas de ejemplo, actualización del checklist de PR y de las guías.

**No entra:**
- Un LLM como juez de la prosa: se deja para una fase posterior.
- Control en ejecución (hooks, restricción de red, herramientas permitidas): depende del asistente y de la
  configuración de la organización.
- Un marketplace o registro con niveles de confianza, y la firma de piezas individuales.
- Cambios en dónde se instalan las piezas o en si se versionan.

## Alternativas descartadas

- **Solo revisión humana:** no escala y no detecta texto invisible.
- **Solo el escáner externo:** no cubre nuestras convenciones (capacidades declaradas, marcadores propios) y
  añade una dependencia de CI que no controlamos.
- **Un LLM como única barrera:** costoso, no determinista y evadible; queda como capa adicional.

## Criterios de aceptación

1. `cuypilot audit` pasa sobre el catálogo actual y rechaza cada pieza maliciosa de ejemplo con su identificador.
2. El CI falla en un PR que agrega una pieza con un hallazgo alto y muestra el informe en el resumen del job.
3. Una capacidad detectada y no declarada falla; declararla la deja pasar y visible en el PR.
4. Cada release adjunta el `sha256` del wheel.
5. El checklist de PR y las guías describen la auditoría y cómo registrar una excepción.
6. `pytest`, `ruff check` y `ruff format --check` pasan; los scripts del catálogo siguen cumpliendo sus reglas.

## Preguntas abiertas

1. **Severidades:** ¿bloquean solo los hallazgos `alta` y los `media` avisan? Es la propuesta de este borrador.
2. **Escáner de Cisco:** ¿informativo al principio y bloqueante después de medir su ruido, o bloqueante desde el inicio?
3. **Dominios permitidos:** ¿qué dominios de documentación pueden aparecer en las piezas además de los de los
   proyectos de origen (GitHub, docs de Databricks, Sphinx, PyPI)?
4. **Atestaciones y `--require-hashes`:** ¿el GitHub Enterprise de la organización ofrece las atestaciones de
   procedencia, y los proyectos consumidores aceptan fijar el hash en `requirements-dev.txt`?
