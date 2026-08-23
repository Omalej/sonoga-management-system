# Sonoga HMS runtime status

## Completed in this package

- Django/PostgreSQL project structure
- Hotel operations and WordPress reservation synchronization endpoint
- Pure Water and Bread production/stock/sales foundation
- HR, payroll, finance, procurement, approvals and audit foundation
- Role-based operational screens
- Docker, Gunicorn and nginx deployment configuration
- Production environment generator
- First-deployment workflow
- Migration presence guard
- Source-level preflight validation

## Validation performed in the build environment

- All Python sources compile and parse successfully.
- Local cross-module import symbol scan reports no unresolved local imports.
- String model-reference scan reports no unresolved Django model references.
- Deployment shell scripts pass shell syntax validation.
- WordPress PHP helper passes PHP syntax validation.

## Environment limitation

The build container cannot resolve PyPI and does not have Django/psycopg installed, so `manage.py check`, `makemigrations`, `migrate`, and a live PostgreSQL transaction test cannot be executed inside this environment. The bundled first-deploy workflow performs those checks on the actual deployment host where Docker can install the declared dependencies.
