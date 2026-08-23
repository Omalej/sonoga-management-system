# Runtime phase changes

- Added `deploy/preflight.py` for dependency-free source validation.
- Added `deploy/create_env.py` to generate private production secrets safely.
- Added `deploy/first_deploy.sh` for first-server bootstrap.
- Added startup migration guard to prevent unclear missing-table failures.
- Kept automatic migration generation disabled for normal production startup.
- Added `.gitignore` protections for `.env`, media, static build output and caches.
- Added `RUNTIME_STATUS.md` describing completed validation and the remaining live-runtime test.
- Updated first-deployment instructions.
