#!/usr/bin/env python
"""Database connectivity check utility."""

import sys
from pathlib import Path

# Add backend to sys.path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.config import get_settings  # noqa: E402
from app.db import check_db_connection  # noqa: E402


def main() -> int:
    settings = get_settings()
    # Mask password for display
    display_url = settings.DATABASE_URL
    if "@" in display_url:
        prefix, host_part = display_url.split("@", 1)
        scheme_and_user = prefix.split(":")[0] + "://***:***"
        display_url = f"{scheme_and_user}@{host_part}"

    print("==================================================")
    print("ControlChaos Database Connectivity Check")
    print(f"Target URL: {display_url}")
    print("==================================================")

    try:
        diag = check_db_connection()
        print(f"[OK] Status:         {diag['status']}")
        print(f"[OK] Latency:        {diag['latency_ms']} ms")
        print(f"[OK] SSL Active:     {diag['ssl_active']}")
        print(f"[OK] Server Version: {diag['server_version']}")
        print("Database check passed successfully.")
        return 0
    except Exception as exc:
        print(f"[FAIL] Database connection failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
