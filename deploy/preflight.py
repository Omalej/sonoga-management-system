#!/usr/bin/env python3
"""Source-level Sonoga HMS preflight that runs without Django installed."""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_APPS = [
    "accounts", "organization", "hr", "hotel", "inventory", "factory",
    "commercial", "procurement", "finance", "payroll", "control",
]
REQUIRED = [
    "manage.py", "requirements.txt", "sonoga_hms/settings.py", "sonoga_hms/urls.py",
    "Dockerfile", "docker-compose.yml", "deploy/entrypoint.sh",
    "integrations/views.py", "hotel/models.py", "factory/models.py",
]


def fail(message: str) -> None:
    print(f"ERROR: {message}")
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-migrations", action="store_true")
    args = parser.parse_args()

    if sys.version_info < (3, 12):
        fail("Python 3.12 or newer is required by Django 6.x.")

    missing_files = [item for item in REQUIRED if not (ROOT / item).exists()]
    if missing_files:
        fail("Missing required files: " + ", ".join(missing_files))

    python_files = [p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts]
    syntax_errors = []
    for path in python_files:
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
            ast.parse(source, filename=str(path))
        except Exception as exc:
            syntax_errors.append(f"{path.relative_to(ROOT)}: {exc}")
    if syntax_errors:
        fail("Python source validation failed:\n" + "\n".join(syntax_errors))

    missing_migrations = []
    for app in MODEL_APPS:
        migration_dir = ROOT / app / "migrations"
        if not migration_dir.exists() or not list(migration_dir.glob("0*.py")):
            missing_migrations.append(app)

    print(f"Python source: OK ({len(python_files)} files)")
    if missing_migrations:
        message = "Initial migrations not yet generated: " + ", ".join(missing_migrations)
        if args.require_migrations:
            fail(message)
        print("NOTICE: " + message)
    else:
        print("Application migrations: OK")

    env_file = ROOT / ".env"
    if env_file.exists():
        text = env_file.read_text(encoding="utf-8")
        placeholders = [line for line in text.splitlines() if "REPLACE_WITH_" in line]
        if placeholders:
            fail(".env still contains placeholder secrets.")
        print(".env: present, no placeholder secrets detected")
    else:
        print("NOTICE: .env not present yet. Run: python deploy/create_env.py")

    print("Sonoga source preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
