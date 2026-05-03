"""Vercel serverless entry-point — imports the FastAPI app."""
import sys
import os

# Put the backend package on the path so all relative imports work.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "atlas", "backend"))

# Vercel's filesystem is read-only except /tmp — redirect the SQLite DB there.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/atlas.db")
os.environ.setdefault("ENVIRONMENT", "production")

from main import app  # noqa: E402  (import after sys.path patch)

# Vercel expects the ASGI app to be named `app` or exported from the module.
__all__ = ["app"]
