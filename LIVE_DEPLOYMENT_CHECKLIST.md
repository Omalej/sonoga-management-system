# Sonoga HMS Live Deployment Checklist

## Server and DNS

- Point `manage.sonogahotels.com` to the deployment server.
- Install Docker Engine + Docker Compose plugin.
- Place the project in a controlled directory such as `/opt/sonoga_hms`.
- Generate `.env` with `python deploy/create_env.py` and keep it private.
- Do not expose PostgreSQL to the public internet.
- Keep the bundled nginx port bound to localhost only.
- Install a valid HTTPS certificate on the host reverse proxy.

## First database launch

- Run `./deploy/first_deploy.sh` once to generate initial migration files and launch the stack.
- Keep the generated migration files with the application source after review.
- Create the first superuser.
- Run `sonoga_readiness`.

## Initial Sonoga operating data

Configure real, non-guessed data before staff transactions:

### Hotel
- Room types and rates
- Physical room numbers/floors
- Opening room status

### Pure Water
- Finished products and prices
- Raw/packaging inventory items
- Opening stock balances

### Bread
- Bread products and prices
- Raw/packaging inventory items
- Production recipes
- Opening stock balances

### Shared
- Employees and user accounts
- Suppliers
- Customers/distributors
- Vehicles/routes where used
- Expense categories and approval responsibilities

Then run:

```bash
docker compose exec web python manage.py sonoga_readiness --operational
```

## WordPress bridge

1. Put the same webhook secret in the HMS `.env` and WordPress configuration.
2. Test `/api/wordpress/ping/` with `sonoga_hms_ping()`.
3. Confirm the response reports the integration user and Hotel business unit as ready.
4. Map the exact installed booking plugin's successful booking/payment events to `sonoga_send_booking_to_hms()`.
5. Perform one controlled test reservation and verify it appears once in `/hotel/reservations/`.
6. Repeat the webhook and confirm no duplicate reservation is created.
7. Test a later payment update against the same booking reference.

## Backup and recovery

- Run `./deploy/backup.sh` before the first production transaction.
- Copy backups off the application server.
- Test one restore in a non-production environment.
- Enable the supplied systemd timer or an equivalent scheduler.

## Go-live verification

- `https://manage.sonogahotels.com/health/` returns OK.
- `https://manage.sonogahotels.com/ready/` returns database ready.
- `python deploy/post_deploy_verify.py` passes.
- `python manage.py check --deploy` passes inside the web container.
- `python manage.py sonoga_readiness --operational` passes.
- Receptionist cannot open payroll/factory management pages.
- Factory staff cannot open Hotel/HR/Group finance pages outside their permissions.
- Stock cannot become negative through normal sale/production workflows.
- Backup has completed successfully.
