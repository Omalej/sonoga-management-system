#!/usr/bin/env python3
"""Verify the public Sonoga HMS health/readiness endpoints after deployment."""
from __future__ import annotations

import argparse
import json
import ssl
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def fetch(url: str, timeout: int = 10) -> tuple[int, dict]:
    request = Request(url, headers={"User-Agent": "Sonoga-Deploy-Verify/1.0"})
    with urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://manage.sonogahotels.com")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failures = []
    for path in ("/health/", "/ready/"):
        url = base + path
        try:
            status, payload = fetch(url)
            ok = status == 200 and payload.get("ok") is True
            print(f"{url}: status={status} ok={payload.get('ok')}")
            if not ok:
                failures.append(url)
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            print(f"{url}: FAILED: {exc}")
            failures.append(url)
    if failures:
        print("Deployment verification failed.")
        return 1
    print("Public Sonoga HMS health/readiness verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
