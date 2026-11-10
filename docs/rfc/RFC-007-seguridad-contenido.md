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

Capas, de la más barata a la más cara. Todas son **informativas**: reportan hallazgos para el revisor y nunca bloquean un PR ni una instalación. La
decisión sigue siendo humana. Corren en el CI de cada PR y las primeras también en local.

### 1. Auditoría determinista: `cuypilot audit`

Un módulo con la librería estándar (sin dependencias nuevas) que recorre las piezas del catálogo y reporta
hallazgos con identificador, prioridad orientativa, archivo y línea. Los hallazgos de contenido nunca cambian el
código de salida (siempre 0); solo `audit --ci`, de la RFC-008, devuelve un código distinto de cero y únicamente
por inconsistencias de lockfile o archivos gestionados;
`--json` para máquinas.

| Familia | Qué detecta | Prioridad |
|---|---|---|
| Texto oculto | Caracteres Unicode de formato, dirección y bloque Tag (U+E0000–E007F); comentarios HTML con contenido (salvo los marcadores `cuypilot:` y las licencias de terceros); bloques base64 o hexadecimales largos | alta |
| Inyección | Frases como "ignore previous instructions", "ignora las instrucciones anteriores", "no se lo digas al usuario", "sin pedir confirmación", "no menciones" (español e inglés) | alta |
| Acceso sensible | Referencias a `.env`, `~/.ssh`, claves privadas, `credentials`, volcado de variables de entorno | alta |
| Red y exfiltración | URLs externas (se listan todas); `curl`, `wget`, `Invoke-WebRequest`, `\| sh`; `pip install` de paquetes no declarados | media |
| Ejecución en scripts | Por AST: `eval`, `exec`, `compile`, `__import__`, `subprocess`, `os.system`, `shell=True`, `pickle`, módulos de red, escritura de archivos | alta |
| Persistencia | Instrucciones que piden escribir o modificar `AGENTS.md`, `copilot-instructions.md`, `.github/`, `.vscode/` o ajustes de aprobación automática | alta |
| Frontmatter | Claves fuera del conjunto permitido; `tools` más amplio que lo declarado | media |
| Nombres | Nombre a distancia de edición ≤2 de otra pieza (suplantación) | media |

La prioridad (`alta` o `media`) solo ayuda al revisor a decidir qué mirar primero. Las URLs se listan tal
cual se encuentran, sin lista de dominios permitidos: el revisor decide si son legítimas.

### 2. Capacidades declaradas

Cada pieza declara en `catalog.toml` lo que puede hacer: `capabilities = ["scripts", "network", "tools"]`
(vacío por defecto). La auditoría compara lo declarado con lo detectado y reporta las discrepancias. Así el
revisor ve de un vistazo qué privilegios pide cada PR.

### 3. Escáner externo en el CI

Evaluar [Cisco skill-scanner](https://github.com/cisco-ai-defense/skill-scanner) como **segundo juicio**
independiente de nuestras reglas. Datos verificados el 2026-11-10: código abierto con **licencia Apache-2.0**
(archivo `LICENSE`; la API de GitHub la informa como "NOASSERTION"), activo, con soporte para CI. Combina
reglas YAML/YARA, análisis de flujo de datos sobre los scripts y un juez LLM opcional. Se usaría **solo con
los modos que no necesitan LLM ni salida a red**, como paso informativo del CI.

### 4. Integridad de lo que se instala

- El lockfile ya guarda el hash de cada archivo y `cuypilot status` detecta ediciones locales y cambios del
  catálogo: no se agrega nada.
- Cada Release publica el `sha256` del wheel en `SHA256SUMS`: ya existe en el CI.

### 5. Revisión humana

El escáner entrega un informe al revisor en lugar de un diff en bruto. La revisión independiente se hace
efectiva con CODEOWNERS y protección de rama configurados en la organización. Para scripts, herramientas y
agents con herramientas se recomienda un segundo revisor. Esto no se implementa en el repositorio: se
configura en el proveedor.

### 6. Pruebas

Un directorio de **piezas maliciosas de ejemplo** (una por familia de la tabla) que la auditoría debe rechazar
con el identificador esperado, y las piezas actuales del catálogo, que deben pasar. Las piezas de terceros
(ponytail, superpowers, awesome-copilot) se auditan igual: si alguna da un hallazgo legítimo, se corrige o se
se explica en el PR.

## Alcance

**Entra:** `cuypilot audit` (informativo), capacidades declaradas, el escáner de Cisco como paso informativo del
CI, pruebas con piezas maliciosas de ejemplo y actualización del checklist de PR.

**No entra:**
- Un LLM como juez de la prosa: se deja para una fase posterior.
- Control en ejecución (hooks, restricción de red, herramientas permitidas): depende del asistente y de la
  configuración de la organización.
- Un marketplace o registro con niveles de confianza, y la firma de piezas individuales.
- Bloquear PRs o instalaciones por hallazgos.
- Atestaciones de procedencia y fijar hashes en los proyectos consumidores.
- Cambios en dónde se instalan las piezas o en si se versionan.

## Alternativas descartadas

- **Solo revisión humana:** no escala y no detecta texto invisible.
- **Solo el escáner externo:** no cubre nuestras convenciones (capacidades declaradas, marcadores propios) y
  añade una dependencia de CI que no controlamos.
- **Un LLM como única barrera:** costoso, no determinista y evadible; queda como capa adicional.

## Criterios de aceptación

1. `cuypilot audit` reporta, con su identificador, cada hallazgo de las piezas maliciosas de ejemplo y no
   reporta nada grave sobre el catálogo actual (o cada hallazgo está explicado).
2. El CI muestra el informe en el resumen del job de cada PR y no falla por los hallazgos.
3. Las discrepancias entre capacidades declaradas y detectadas aparecen en el informe.
4. El checklist de PR describe la auditoría y cómo leer el informe.
5. `pytest`, `ruff check` y `ruff format --check` pasan; los scripts del catálogo siguen cumpliendo sus reglas.

## Decisiones tomadas

- Todo es informativo: ningún hallazgo bloquea.
- No hay lista de dominios permitidos ni excepciones: las URLs se listan y el revisor decide.
- Las atestaciones de procedencia y el hash fijado en los consumidores quedan fuera de esta RFC.
