# Instalación reproducible y validación en CI

Disponible en la versión preparada 0.6.0. No presupone que su Release ya esté publicada.

`cuypilot init` escribe `cuypilot.toml` después de confirmar e instalar la selección. El manifiesto se
versiona junto con los archivos instalados y los locks. También puedes escribirlo y ejecutar `install`:

```toml
cuypilot = ">=0.6,<0.7"
targets = ["copilot", "genie"]
pieces = ["python-standards", "docs-writer", "python-design"]
tools = []
```

```bash
cuypilot install
cuypilot install --frozen
cuypilot audit --ci
```

El wheel fija las versiones de todas las piezas. La restricción `cuypilot` admite `>=`, `>`, `<=`, `<`,
`==` y `!=`, separados por comas, con uno a tres componentes numéricos. `0.6` equivale a `0.6.0`.
No admite `~=`, comodines, prereleases ni el formato completo de PEP 440. Se rechazan claves desconocidas,
nombres repetidos, tipos incorrectos y piezas incompatibles antes de escribir.

## Selección y destinos

`pieces` contiene skills, agents e instructions; `tools` contiene programas externos. Las dependencias se
expanden desde el catálogo. La selección es **común a todos los destinos**; una tool no compatible con
Genie exige otro manifiesto/proyecto o quitar Genie de esa selección. No hay selecciones por destino.

`install` reconcilia el conjunto exacto: agrega, actualiza y retira lo que ya no se pide, incluidas
dependencias que dejan de ser necesarias. Se detiene ante cambios locales o conflictos ajenos; usa
`--force` únicamente después de revisar y respaldar lo que perderías. Las tools muestran comandos y piden
confirmación; `--yes` los acepta. Un fallo restaura archivos gestionados, locks y manifiesto de todos los
destinos. No revierte paquetes pip ni efectos externos de tools, no protege frente a escritores concurrentes
y no es una recuperación tras terminar abruptamente el proceso.

Si retiras un destino de `targets`, frozen detecta su lock sobrante. `install` retira sus piezas y su
bloque gestionado en la misma transacción, conservando contenido ajeno. Si tiene ediciones locales,
se detiene para que las revises antes de considerar `--force`.

Con manifiesto, `add/remove` cambian la selección común y reconcilian **todos sus destinos**, incluso si
se indica uno con `--target`. `--target` debe figurar en el manifiesto. `remove` acepta nombres declarados
explícitamente; sus dependencias se retiran automáticamente si ya no se necesitan. Si otra selección
todavía requiere una pieza, no se permite eliminarla. Editar el manifiesto directamente seguido de `install`
también permite cambiar la selección. Su escritura por la CLI normaliza el TOML y no conserva comentarios.

```bash
cuypilot add design-review
cuypilot remove docs-writer
cuypilot update --dry-run
cuypilot outdated
cuypilot why sphinx-docstrings
```

`update` mantiene la selección declarada y actualiza lo instalado. Sin `--target`, `list`, `status`,
`update`, `outdated` y `why` recorren los destinos declarados o detectados. Con `--target` consultan o
actualizan solo ese destino. `outdated` incluye cambios de contenido/adaptación/integración, aunque la
versión no cambie. `why` usa dependencias registradas y muestra cadenas transitivas. Las consultas y
`update --dry-run` no escriben ni ejecutan instaladores/configuradores; las consultas de tools pueden
ejecutar su comando de versión. El dry-run puede rechazar conflictos que impedirían aplicar el plan.

`status` informa además del **bloque compartido**: un cambio de la instrucción base se detecta ahí, sin
atribuirlo a todas las piezas. El plan y el informe explican cuándo se modifica ese bloque.

## Migrar proyectos anteriores

Sin manifiesto, `add/remove/update` siguen disponibles; `add/remove` no lo crean implícitamente.
`install` deduce el manifiesto a partir de los locks existentes. Si varios destinos tienen selecciones
distintas, se detiene: escribe la selección común explícitamente antes de ejecutar `install`.
Las entradas deducidas de locks se conservan como selecciones explícitas porque los locks antiguos no
distinguen intención y dependencias. Puedes simplificar después `pieces` y volver a ejecutar `install`.

Sin `targets` ni `--target` se detectan locks, bloques de Copilot y carpetas `.opencode`/`.assistant`;
una `.github` genérica no añade Copilot. Sin señales se usa Copilot. `init` sigue preguntando el destino;
si ya existe manifiesto, usa `add` o `install`. Los bloques con marcadores pero sin lock requieren adopción
explícita mediante `--force`; los locks antiguos válidos siguen siendo legibles.

Si el wheel nuevo queda fuera de la restricción del manifiesto, revisa sus cambios y actualiza esa
restricción antes de operar. Al volver a un wheel anterior, revisa también la compatibilidad del rango y
del formato del manifiesto; no se promete que una CLI anterior a 0.6.0 interprete este archivo.

## Qué comprueba cada validación

| Comando | Comprobación | Escrituras / salida |
|---|---|---|
| `install --frozen` | Manifiesto obligatorio, selección expandida, versiones y contenido del wheel, dependencias, hashes, bloque esperado y archivos añadidos dentro de cada skill gestionada | No escribe ni ejecuta procesos externos; 0 si coincide, 1 con diferencias |
| `audit --ci` | Integridad instalada según locks: archivos, hashes, dependencias, marcadores y bloque histórico; selección del manifiesto si existe | No escribe; 0 si coincide, 1 si encuentra inconsistencias |
| `audit` | La misma comprobación de integridad | Hallazgos informativos; errores de lectura/formato sí devuelven 1 |

Se ignoran caches `__pycache__` dentro de skills. Los archivos ajenos fuera de directorios de piezas
gestionadas se conservan. Los hashes no impiden que alguien edite conjuntamente archivos y locks;
`--frozen` compara también contra el catálogo del wheel instalado. El entorno binario de las tools no se
reproduce ni verifica con frozen: se comprueba su declaración y hash de integración. Consulta `status`
para su versión ejecutable. `audit` no implementa el escaneo de contenido pendiente de RFC-007.

## CI del proyecto consumidor

Una vez publicada 0.6.0, adapta el repositorio proveedor y configura `CUYPILOT_RELEASE_TOKEN` con acceso
de lectura a sus Releases. Para repos públicos puede bastar un token con acceso a esos assets. No pongas
tokens dentro del manifiesto o de los comandos. Los archivos y locks deben estar previamente commiteados.

```yaml
name: cuypilot-consumer
on: [pull_request, push]
permissions:
  contents: read
jobs:
  verify:
    runs-on: ubuntu-latest
    env:
      CUYPILOT_REPOSITORY: tu-organizacion/cuypilot
      CUYPILOT_TAG: v0.6.0
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Descargar y verificar distribución
        env:
          GH_TOKEN: ${{ secrets.CUYPILOT_RELEASE_TOKEN }}
        run: |
          gh release download "$CUYPILOT_TAG" --repo "$CUYPILOT_REPOSITORY" \
            --pattern '*.whl' --pattern SHA256SUMS --dir /tmp/cuypilot-wheel
          (cd /tmp/cuypilot-wheel && sha256sum -c SHA256SUMS)
          python -m pip install --no-deps /tmp/cuypilot-wheel/*.whl
      - run: cuypilot install --frozen
      - run: cuypilot audit --ci
```

Protecciones de rama y checks requeridos se configuran en el proveedor. El YAML no los activa ni
establece por sí mismo confianza en el wheel: revisa su procedencia y los permisos de publicación.

## Recuperar un despliegue Genie parcial

```bash
cuypilot deploy --workspace-path /Workspace/Users/usuario/proyecto --resume --dry-run
cuypilot deploy --workspace-path /Workspace/Users/usuario/proyecto --resume
```

`--resume` adopta solo archivos que ya tienen exactamente los bytes deseados y eliminaciones ya
realizadas. Un bloque remoto se adopta solo si coincide exactamente con el local. Cualquier discrepancia
conserva la protección normal. Revisa y resuelve los conflictos antes de considerar `--force`.
El lock se publica al final; un fallo puede dejar contenido remoto parcial, detectable por el reintento.
