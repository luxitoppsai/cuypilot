# cuypilot

Repositorio centralizado y gobernado de skills, agents e instructions para GitHub Copilot (VS Code), OpenCode y Genie Code (Databricks),
distribuido como wheel con una CLI que los instala en el workspace de cada proyecto.

## Decisiones y contratos

Las decisiones necesarias para mantener el proyecto están en el repositorio:
- [RFC-001](RFC.md): catálogo y CLI.
- [RFC-002](docs/rfc/RFC-002-integraciones-terceros.md): scripts, terceros y enmienda de pip.
- [RFC-003](docs/rfc/RFC-003-contenido-dominio.md): contenido de dominio.
- [RFC-005](docs/rfc/RFC-005-multiples-asistentes.md): destinos, versiones y despliegue Genie.
- [RFC-004](docs/rfc/RFC-004-seguridad-wizard.md): seguridad y wizard.
- [Lineamientos de gobernanza](docs/gobernanza.md): operación y revisión por el equipo.
- [RFC-006](docs/rfc/RFC-006-gobernanza-analytics.md): evolución técnica opcional.

Las notas personales de Obsidian son complementarias; no son necesarias para contribuir.
Las causas de bugs y decisiones se documentan junto al código, en los RFC y en CHANGELOG.md.
