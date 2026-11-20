# Infrastructure

Deployment and infrastructure assets (Phase 1 scaffold).

- `docker-compose.yml` at repo root: local dev services (db, redis, backend, celery, frontend).
- Production/staging configuration, reverse proxy (Nginx), TLS, secrets management, and IaC to be added per `docs/architecture/DEPLOYMENT_AND_OPERATIONS_PLAN.md`.

Notes:
- Pin/validate images and runtime versions per D-010 and `TECHNOLOGY_COMPATIBILITY_MATRIX.md`.
- Do not commit secrets; use environment variables/secret manager.
- Backups/restore procedures to be operationalized before production.
