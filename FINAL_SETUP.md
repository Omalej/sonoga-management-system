# Sonoga HMS — first deployment

The HMS is built for Django + PostgreSQL. WordPress remains the owner of public online booking and sends successful bookings/payment updates to Django through the secured booking webhook.

## Fastest deployment path

1. Install Docker + Docker Compose on the server.
2. From the project directory create private production secrets:

```bash
python deploy/create_env.py --host manage.sonogahotels.com
```

3. Run the first-deployment workflow:

```bash
./deploy/first_deploy.sh
```

This performs source preflight, builds the Django image, generates the initial migration files back into the project, starts PostgreSQL/Django/nginx, applies migrations, seeds the three Sonoga business units and standard departments/stores, and runs readiness checks.

4. Create the first administrator:

```bash
docker compose exec web python manage.py createsuperuser
```

5. Open the HMS through the HTTPS reverse proxy for `manage.sonogahotels.com`.

## Important

Initial application migrations are deliberately generated during the first deployment because this build environment cannot install Django from PyPI. Normal startup now refuses to continue if migrations are missing, rather than failing later with unclear missing-table errors.

After migration files exist, keep `SONOGA_AUTO_MAKEMIGRATIONS=False` and retain the generated migration files with the project.

## WordPress

Do not duplicate online booking in Django. Configure the existing WordPress booking plugin to call the helper in `deploy/wordpress_webhook_helper.php.example` after a successful booking/payment using the exact plugin hook available on the live website.
