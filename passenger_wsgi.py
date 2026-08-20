"""
Namecheap / cPanel shared hosting WSGI entry (Passenger / LiteSpeed).

Setup Python App fields:
  Application startup file : passenger_wsgi.py
  Application Entry point  : application
"""

from __future__ import annotations

import os
import sys

APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Optional: load .env if present (shared hosts sometimes prefer cPanel env UI instead)
env_path = os.path.join(APP_DIR, ".env")
if os.path.isfile(env_path):
    try:
        with open(env_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key, val)
    except OSError:
        pass

from app import app as application  # noqa: E402  — Passenger requires this name
