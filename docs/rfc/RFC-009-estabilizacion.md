---
rfc: RFC-009
estado: aceptado
fecha: 2026-11-12
---

# RFC-009 — Integridad, recuperación y distribución comprobada

Alcance autorizado: puntos 1–3 de la evaluación del 2026-11-12. Se conserva la arquitectura y se
reutiliza RFC-008 para el manifiesto. No incluye RFC-007, evals con modelos ni publicación remota.

## Problema y alcance

Corregir H1–H5 de la evaluación, comprobar el wheel en entornos limpios y entregar RFC-008.
El rollback local debe cubrir errores de codificación; un bloque sin lock requiere adopción explícita.
El bloque compartido debe tener estado e informe propios. La recuperación de despliegues y Releases
parciales debe conservar contenido ajeno y no declarar éxito con hashes incoherentes.

## Decisiones

- Despliegue: añadir `deploy --resume`, explícito y limitado a archivos cuyo contenido remoto ya
  coincide exactamente con el deseado (o que ya están ausentes si iban a eliminarse). Un bloque
  remoto solo se adopta si coincide con el local. Cualquier otra discrepancia conserva la protección
  normal y requiere revisión. `--force` mantiene su significado previo. El lock sigue publicándose
  al final. No se promete atomicidad remota ni se adopta contenido diferente durante un reintento.
- Releases: descargar los assets existentes a una carpeta temporal, verificar su coherencia antes
  de mutar y calcular el checksum sobre los bytes publicados. Nunca sobrescribir assets. Un checksum
  existente incompatible causa un error, incluso si el wheel falta. Se separa la lógica del workflow
  para poder probarla con un ejecutor simulado.
- Bloque base: estado separado de las piezas; comparar contenido esperado, histórico e instalado.
  El informe y el dry-run indican cambios del bloque compartido.
- RFC-008: el manifiesto expresa una selección común para sus destinos. `install` reconcilia el conjunto
  exacto (incluidas dependencias), sin pisar ediciones locales por defecto. `add/remove` con manifiesto
  actualizan esa selección y todos sus destinos en una transacción local. Una selección diferente por
  destino queda fuera del formato actual; no se inventa una extensión de esquema.
- Sin manifiesto, `add/remove/update` conservan su operación por destino; `init` genera el manifiesto
  y `install` permite migrar locks existentes. En una migración, selecciones distintas entre destinos
  requieren un manifiesto explícito: no se adivina la intención ni se instala una unión silenciosamente.
- Rangos del wheel: comparadores `>=`, `>`, `<=`, `<`, `==`, `!=`, separados por comas, con versiones
  de uno a tres componentes numéricos. No se anuncian rangos PEP 440 completos. Sin nuevas dependencias.
- Frozen exige manifiesto y locks coherentes con el wheel, hashes, dependencias, bloques y conjunto
  de archivos de cada pieza; no escribe ni ejecuta comandos de instalación/configuración. `audit --ci`
  comprueba integridad instalada y manifiesto si existe; no implementa el escaneo de contenido RFC-007.
- El CI construye sdist/wheel en PR y prueba el wheel en venv limpio para los tres destinos. Matriz:
  Ubuntu Python 3.11–3.14 y Windows Python 3.11/3.14. No se afirma haber ejecutado localmente esa matriz.

## Alternativas

Staging remoto o un journal persistente aportarían más complejidad y otro formato que mantener.
La adopción explícita por igualdad de bytes basta para reintentar sin desproteger conflictos.
Copiar todo el proyecto para rollback es excesivo: se conservan snapshots de los archivos gestionados,
destinos previstos y manifiesto, como RFC-004. No se revierten pip ni efectos externos de herramientas.

## Aceptación

Regresiones de H1–H5, fallos después de escrituras exitosas, preservación de archivos y locks entre
destinos y errores al guardar el manifiesto. Siete criterios de RFC-008, incluidos modo frozen sin
mutaciones, restricción de wheel antes de escribir, migración y consultas de solo lectura.
Wheel con recursos y licencias completos, CLI ejecutada fuera del checkout en venv limpio; suite,
lint, formato y guías actualizadas. No requiere publicar una Release ni llamar servicios reales.
