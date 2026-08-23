# Sonoga HMS Server Activation

This is the final server-side activation sequence for `manage.sonogahotels.com`.

## Prerequisites

The Linux server must already have:

- Docker Engine
- Docker Compose plugin
- Nginx
- Certbot with the Nginx plugin
- DNS for `manage.sonogahotels.com` pointing to the server
- ports 80 and 443 reachable from the internet

Run:

```bash
./deploy/server_precheck.sh manage.sonogahotels.com
```

## Automated activation

From the project directory, run as root:

```bash
sudo ./deploy/go_live.sh
```

The script deliberately uses an HTTP-only Nginx configuration first. This allows Nginx to start before the TLS certificate exists. Certbot then obtains the certificate and upgrades the host to HTTPS with redirect enabled.

The activation sequence:

1. verifies Docker, Docker Compose, Nginx, Certbot and DNS;
2. generates `.env` if it does not exist;
3. builds the Sonoga Docker image;
4. generates the initial Django migrations into the project;
5. starts PostgreSQL, Django/Gunicorn and the internal Nginx service;
6. bootstraps Sonoga business units/defaults;
7. enables the HTTP host proxy;
8. obtains the TLS certificate using Certbot;
9. redirects HTTP to HTTPS;
10. runs post-deployment verification.

## First administrator

After activation:

```bash
docker compose exec web python manage.py createsuperuser
```

## Load real Sonoga data

Follow `INITIAL_DATA_IMPORT.md`. Always use `--dry-run` before committing a CSV import.

## Final checks

```bash
docker compose exec web python manage.py check --deploy
docker compose exec web python manage.py sonoga_readiness --operational
python3 deploy/post_deploy_verify.py --base-url https://manage.sonogahotels.com
```

Do not connect the live WordPress booking plugin until the HMS health/readiness checks and a manual hotel transaction test have passed.
