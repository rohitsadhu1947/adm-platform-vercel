"""
Vercel serverless entry point.

Vercel's @vercel/python runtime imports this file and serves the
`app` ASGI application. All requests are routed here by vercel.json.

The backend directory is added to sys.path at module level so that
`from main import app` works. The bot directory is added lazily by
the webhook handler when it first processes a Telegram update.

Note: bot/config.py was renamed to bot/bot_config.py to avoid module
name conflicts with backend/config.py when both dirs are on sys.path.
"""

import sys
import os

# Add backend directory to path so FastAPI app imports resolve
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir = os.path.join(_root, "backend")

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

# Import the FastAPI app — Vercel looks for `app` at module level
from main import app  # noqa: E402
