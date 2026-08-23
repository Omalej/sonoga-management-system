# Sonoga HMS Deployment Runbook

## 1. Prepare environment

Copy `.env.production.example` to `.env` and replace every `REPLACE_...` value with a real secret. For the planned deployment, use:

- `DJANGO_ALLOWED_HOSTS=manage.sonogahotels.com`
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://manage.sonogahotels.com`
- `POSTGRES_HOST=db`
- `SONOGA_WORDPRESS_REQUIRE_SIGNATURE=True`

Do not commit `.env`.

## 2. Generate the initial migrations once

This source package intentionally keeps migration generation explicit. Run this once from the project directory so the generated migration files are written back into the project:

```bash
docker compose -f docker-compose.yml -f docker-compose.migrations.yml build web
docker compose -f docker-compose.yml -f docker-compose.migrations.yml run --rm --entrypoint python web manage.py makemigrations accounts organization hr hotel inventory factory commercial procurement finance payroll control
```

Review the generated migrations and keep them in the project. Leave `SONOGA_AUTO_MAKEMIGRATIONS=False` for normal deployments.

## 3. Start PostgreSQL and the HMS

```bash
docker compose up -d --build
```

The container entrypoint will:

1. wait for PostgreSQL;
2. apply migrations;
3. create Sonoga role groups and the three business units;
4. seed standard departments, positions, stores and expense categories;
5. collect static files;
6. run the Sonoga readiness check;
7. start Gunicorn.

The bundled nginx container listens on port `8080`. Put the production HTTPS reverse proxy or hosting load balancer in front of that port and route `manage.sonogahotels.com` to it.

## 4. Create the first administrator

```bash
docker compose exec web python manage.py createsuperuser
```

The account will be required to change its password on first interactive use if `must_change_password` is set.

## 5. Verify health

```text
/health/   application process is alive
/ready/    application can reach PostgreSQL
```

Also run:

```bash
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py sonoga_readiness
```

## 6. Configure operating data

Use `/admin/` initially to configure business-specific values not safe to guess:

- hotel room types and prices;
- individual hotel rooms;
- factory products and prices;
- inventory items and opening stock;
- bread recipes;
- suppliers;
- employees and salaries;
- customers/distributors;
- vehicles and delivery routes.

## 7. WordPress integration

WordPress remains the owner of online booking. The HMS endpoint is:

```text
POST https://manage.sonogahotels.com/api/wordpress/bookings/
```

When webhook signatures are required, WordPress sends:

```text
X-Sonoga-Api-Key
X-Sonoga-Timestamp
X-Sonoga-Signature: sha256=<hex digest>
```

The signature is HMAC-SHA256 of:

```text
<unix_timestamp>.<raw_json_body>
```

using `SONOGA_WORDPRESS_API_KEY` as the secret. `deploy/wordpress_webhook_helper.php.example` contains a generic WordPress sender. The final hook that calls it depends on the booking plugin already installed on sonogahotels.com.

## 8. Backups

Back up PostgreSQL and uploaded media independently. Example PostgreSQL backup:

```bash
docker compose exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > sonoga-backup.sql
```

Test restore procedures before live operations.

## 9. Public exposure and TLS

The internal nginx service now binds only to `127.0.0.1:8080` by default. Route the public HTTPS virtual host for `manage.sonogahotels.com` to that local port. An example host-level nginx file is provided at `deploy/host_nginx.conf.example`.

Before staff use, verify DNS points `manage.sonogahotels.com` at the intended server and install a valid TLS certificate. Then run:

```bash
python deploy/post_deploy_verify.py --base-url https://manage.sonogahotels.com
```

## 10. Backup and restore

Create a database + uploaded-media backup:

```bash
./deploy/backup.sh
```

Backups default to `./backups/` and retain 14 days unless `SONOGA_BACKUP_RETENTION_DAYS` is changed.

Restore requires an explicit confirmation flag because it replaces the current database:

```bash
./deploy/restore.sh \
  --database /path/to/sonoga_hms_TIMESTAMP.dump \
  --media /path/to/sonoga_media_TIMESTAMP.tar.gz \
  --confirm
```

Example systemd service/timer files for daily backup are included in `deploy/sonoga-backup.service.example` and `deploy/sonoga-backup.timer.example`.

## 11. Operational readiness

Infrastructure readiness:

```bash
docker compose exec web python manage.py sonoga_readiness
```

After real rooms, products, inventory items and the Bread recipe are configured, run the stricter check:

```bash
docker compose exec web python manage.py sonoga_readiness --operational
```

Do not treat the system as ready for live staff transactions until the operational check passes.
