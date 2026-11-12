# cuypilot

Catálogo versionado de skills, agents, instructions y herramientas para GitHub Copilot (VS Code),
OpenCode y Genie Code (Databricks), distribuido como wheel con una CLI que los instala en el workspace
de cada proyecto.

## Dónde está cada cosa

| Qué | Dónde |
|---|---|
| Uso e instalación | [README](README.md) y [guía de usuario](docs/guia-usuario.md) |
| Cómo trabaja el equipo | [docs/gobernanza.md](docs/gobernanza.md) |
| Cómo contribuir | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Cambios por versión | [CHANGELOG.md](CHANGELOG.md) |
| Decisiones y contratos | [RFC-001](RFC.md), [RFC-002](docs/rfc/RFC-002-integraciones-terceros.md), [RFC-003](docs/rfc/RFC-003-contenido-dominio.md), [RFC-004](docs/rfc/RFC-004-seguridad-wizard.md), [RFC-005](docs/rfc/RFC-005-multiples-asistentes.md), [RFC-006](docs/rfc/RFC-006-gobernanza-analytics.md), [RFC-007](docs/rfc/RFC-007-seguridad-contenido.md), [RFC-008](docs/rfc/RFC-008-manifiesto-y-flujo-reproducible.md) |

Las causas de bugs y las decisiones se documentan junto al código: en los RFC y en el CHANGELOG.

La [evaluación técnica del 2026-11-12](docs/reviews/2026-11-12/README.md) registra fortalezas,
defectos reproducidos y el plan priorizado de estabilización, con sus criterios de aceptación.
La implementación de los puntos 1–3 sigue [RFC-009](docs/rfc/RFC-009-estabilizacion.md) y
[RFC-008](docs/rfc/RFC-008-manifiesto-y-flujo-reproducible.md).
Uso del manifiesto y validación en CI: [flujo reproducible](docs/flujo-reproducible.md).
Evidencia de entrega y trabajo posterior: [estabilización 0.6.0](docs/estabilizacion-0.6.0.md).
