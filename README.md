# Sonoga Group Management System

Django + PostgreSQL operational management system for:

- Sonoga Hotels & Suites
- Sonoga Pure Water Factory
- Sonoga Bread Factory

The existing WordPress website remains the owner of public online hotel booking. The Django HMS receives WordPress reservations through an authenticated API and manages the operational lifecycle after the booking reaches the hotel.

## Included in this build

### Core and access
- Custom Django user model
- Business units, departments and positions
- Employees
- Role groups and permission bootstrap command
- Role-aware dashboards/navigation
- Audit log foundation

### Hotel
- Room types and rooms
- Guests
- WordPress and offline reservation records
- Manual walk-in/phone/WhatsApp/corporate reservation screen
- Check-in
- Automatic guest folio creation
- Pre-arrival deposit transfer into the active folio
- Folio charges and payments
- Check-out
- Automatic dirty-room and housekeeping handoff
- Housekeeping workflow and supervisor verification
- Maintenance records

### Pure Water and Bread factories
- Products
- Bread recipes / bill of materials
- Raw materials and finished-goods stores
- Transaction-based inventory
- Production batches
- Production material usage
- Production approval with atomic stock deduction/output
- Customers
- Sales invoices and lines
- Stock validation at sale confirmation
- Customer payments / receivables
- Distribution and returns data models

### Finance / management
- Procurement data models and goods receipts
- Expenses, approvals and payments
- Payroll runs and payroll lines
- Consolidated Sonoga Group reporting
- Hotel / Water / Bread business-unit results
- Audit events for critical operational/financial actions

## Local setup

1. Create a PostgreSQL database and user matching `.env.example`, or export your own equivalent environment variables.
2. Create and activate a Python virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Export the variables in `.env.example` into the environment.
5. Create migrations for the Sonoga apps:

```bash
python manage.py makemigrations accounts organization hr hotel inventory factory commercial procurement finance payroll control
```

6. Apply migrations:

```bash
python manage.py migrate
```

7. Create the first superuser:

```bash
python manage.py createsuperuser
```

8. Bootstrap the three business units, Sonoga role groups, and the WordPress integration user:

```bash
python manage.py bootstrap_sonoga
```

9. Start the development server:

```bash
python manage.py runserver
```

10. Sign in at `/accounts/login/`.

Before normal staff use, configure departments, positions, rooms, room types, factory stores/items/products, suppliers and employees through the administration interface.

## Main user-facing URLs

- `/` — role-based landing page
- `/dashboard/` — consolidated group dashboard
- `/hotel/` — hotel/front-desk dashboard
- `/hotel/reservations/` — all HMS + WordPress reservations
- `/hotel/housekeeping/` — housekeeping workflow
- `/factory/WATER/` — Pure Water dashboard
- `/factory/BREAD/` — Bread Factory dashboard
- `/finance/` — finance dashboard
- `/finance/expenses/` — expense register/workflow
- `/hr/` — HR dashboard
- `/hr/employees/` — employees
- `/admin/` — Django administration

## WordPress booking synchronization

The HMS endpoint is:

```text
POST /api/wordpress/bookings/
```

Send the API key in:

```text
X-Sonoga-Api-Key: <SONOGA_WORDPRESS_API_KEY>
```

Example payload:

```json
{
  "external_reference": "WP-BOOKING-7812",
  "business_unit_code": "HOTEL",
  "room_type_code": "DLX",
  "arrival_date": "2026-08-20",
  "departure_date": "2026-08-23",
  "adults": 2,
  "children": 0,
  "nightly_rate": "50000.00",
  "discount_amount": "0.00",
  "tax_amount": "0.00",
  "status": "CONFIRMED",
  "special_requests": "Late arrival",
  "guest": {
    "first_name": "John",
    "last_name": "Doe",
    "phone": "+2348000000000",
    "email": "john@example.com"
  },
  "payment": {
    "reference": "WP-PAY-9921",
    "external_reference": "gateway-transaction-123",
    "amount": "50000.00",
    "method": "ONLINE"
  }
}
```

The endpoint is idempotent by WordPress external booking reference. Repeated notifications update the existing reservation rather than creating a duplicate. A later payment notification can also be attached to the same booking. Once a guest is checked in, synchronized payments are attached to the active folio.

The exact WordPress-side adapter still needs to be mapped to the booking plugin currently used on `sonogahotels.com`, because the plugin name and its field/event hooks have not yet been supplied.

## Important implementation rules

- WordPress owns public online booking. Django does not duplicate it.
- Offline reservations are created in the HMS.
- Inventory balances are calculated from stock movements rather than manually edited quantities.
- Factory sales cannot drive stock negative.
- Production approval posts raw-material consumption and finished-goods output atomically.
- Reservation deposits move into the guest folio on check-in.
- Checkout marks the room dirty and automatically creates a housekeeping task.
- Critical check-in, checkout, payment, production, sales and expense actions are written to audit logs.
- Business-unit separation is preserved for Hotel, Water and Bread while management receives consolidated reports.

## Validation note

All Python source files in this build pass `compileall` / AST syntax validation. Full Django system checks and migration generation could not be executed in the build container because outbound PyPI package resolution is unavailable there. Run the setup commands above in a normal Python/PostgreSQL environment to perform the framework/database checks.

## Deployment hardening added in this phase

- Production environment settings and HTTPS security switches
- PostgreSQL connection health checks
- `/health/` and `/ready/` endpoints
- Gunicorn production process
- Dockerfile + PostgreSQL/nginx Docker Compose stack
- Explicit initial migration-generation workflow
- Forced temporary-password change for interactive users
- App-scoped Sonoga role permissions
- Bootstrap of Hotel, Water and Bread business units
- Seed command for departments, positions, stores and expense categories
- Staff account + employee onboarding command
- Sonoga readiness command
- Optional HMAC-SHA256 WordPress webhook signatures and replay-window validation
- Optional WordPress source-IP restriction
- Deployment and WordPress integration runbooks

Useful commands after migrations are available:

```bash
python manage.py bootstrap_sonoga
python manage.py seed_sonoga_defaults
python manage.py sonoga_readiness
```

Create a staff account and employee record together, for example:

```bash
python manage.py create_sonoga_staff \
  --username receptionist1 \
  --email receptionist1@example.com \
  --first-name Grace \
  --last-name James \
  --phone 08000000000 \
  --staff-number SHS-001 \
  --unit HOTEL \
  --department FO \
  --position "Receptionist" \
  --role "Receptionist"
```

The command requires a temporary password and the user must replace it on first login.

## Operational UI phase

This build adds staff-facing screens beyond Django Admin:

- `/inventory/` — balances, low-stock alerts, movement ledger, transfers and controlled adjustments
- `/procurement/` — purchase requests, approvals, purchase orders and goods receipts into stock
- `/payroll/` — business-unit payroll runs, generation, line adjustments, approval and payment status
- `/control/approvals/` — unified approval queue for expenses, purchasing and payroll
- `/control/notifications/` — current low-stock and operational exception alerts
- `/control/audit/` — read-only audit trail for management/auditors
- `/reports/` — date-range Sonoga Group reporting and CSV export

Online hotel booking remains owned by WordPress. The Django HMS only receives synchronized online reservations through the signed integration endpoint.

## Live-ready deployment phase

Additional production tools are now included:

- `deploy/backup.sh` — PostgreSQL + media backup with checksums and retention
- `deploy/restore.sh` — explicit-confirmation database/media restore
- `deploy/post_deploy_verify.py` — public `/health/` + `/ready/` verification
- `deploy/host_nginx.conf.example` — HTTPS host reverse-proxy example
- `deploy/sonoga-backup.service.example` / `.timer.example` — daily backup scheduling examples
- `LIVE_DEPLOYMENT_CHECKLIST.md` — go-live checklist
- `/api/wordpress/ping/` — signed WordPress bridge connectivity test without creating bookings

The internal Docker nginx listener binds to localhost by default. Public HTTPS should terminate at the host reverse proxy/load balancer and forward to that listener.

## Server activation and real-data loading

- `SERVER_ACTIVATION.md` contains the HTTP -> Certbot -> HTTPS go-live sequence.
- `INITIAL_DATA_IMPORT.md` contains the controlled CSV import workflow for real Sonoga rooms, staff, stock items, factory products, and bread recipes.
- Run `python manage.py import_sonoga_data --help` inside the web container for import options.

