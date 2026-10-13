---
rfc: RFC-004
estado: aceptado
fecha: 2026-10-01
---

# RFC-004 — Operaciones seguras y wizard editable

Solicitud aprobada por el usuario: reforzar seguridad y wizard, con código y documentación.

## Problema y alcance

El lockfile se consume sin validar, las rutas pueden seguir enlaces simbólicos y una actualización
puede sobrescribir una dependencia ajena. Un fallo de escritura puede dejar archivos a medias.
El wizard no permite ajustar las sugerencias y descarta entradas inválidas silenciosamente.

## Decisión

- Validar estructura, nombres, tipos, versiones, hashes y pertenencia de rutas del lockfile.
- Rechazar enlaces simbólicos en rutas gestionadas y validar destinos antes de ejecutar comandos.
- Prevalidar dependencias y conflictos en actualizaciones; restaurar archivos gestionados y lockfile
  ante errores durante una operación. No revertir paquetes pip ni efectos externos de herramientas.
- Preferir ejecutables del entorno Python actual; mantener stdlib y confirmación de herramientas.
- Wizard de cuatro pasos: rol, selección editable, resumen con dependencias y comandos, instalación.
  Validar números y respuestas, mostrar estado y utilidad, conservar modo no interactivo y NO_COLOR.

## Alternativas

No se añaden frameworks de terminal ni dependencias. Una copia de todo el repositorio sería excesiva:
se respaldan únicamente archivos gestionados y destinos potenciales. No hay garantía contra cambios
concurrentes del sistema de archivos ni recuperación tras terminar abruptamente el proceso.

## Aceptación

Regresiones para lockfile inválido, rutas externas, symlinks, conflictos en dependencias, rollback,
preferencia de entorno y selección inválida/editable. Suite y lint completos pasan.

## Verificación

Suite completa: 150 pruebas pasan, además de `ruff check`, `ruff format --check` y revisión del diff.
Build de sdist y wheel 0.4.0 realizado con `python -m build`. El wheel se instaló sin dependencias
en un venv limpio y se verificaron wizard interactivo, status, update, remove y versión.
No se ejecutaron evals de comportamiento en Copilot/VS Code en esta entrega.
