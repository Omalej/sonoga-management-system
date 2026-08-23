# Sonoga HMS Live-Ready Phase

Added in this phase:

- Localhost-only exposure for the bundled nginx service by default.
- Docker health checks for Django/Gunicorn and nginx.
- Session/cookie and upload-size hardening settings.
- Trusted-proxy-aware WordPress source IP handling.
- Authenticated + HMAC-signed WordPress connectivity ping endpoint.
- Refactored generic WordPress signed POST helper with ping support.
- PostgreSQL + media backup script with checksums and retention.
- Explicit-confirmation PostgreSQL/media restore workflow.
- Post-deployment public health/readiness verifier.
- Host-level HTTPS nginx example for `manage.sonogahotels.com`.
- Example systemd daily-backup service/timer.
- Extended infrastructure and operational readiness checks.
- Live deployment checklist for initial Sonoga operating data and WordPress bridge validation.

The exact WordPress booking plugin hook remains intentionally unbound until the installed plugin is identified. WordPress continues to own public online booking.
