"""
Vercel serverless entry point.

Vercel's @vercel/python runtime imports this file and serves the
`app` ASGI application. All requests are routed here by vercel.json.

The FastAPI app is ASGI-compatible; Vercel handles it natively.
"""

import sys
import os

# Add backend directory to path so backend imports work
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir = os.path.join(_root, "backend")
_bot_dir = os.path.join(_root, "bot")

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _bot_dir not in sys.path:
    sys.path.insert(0, _bot_dir)

# Import the FastAPI app — Vercel looks for `app` at module level
from main import app  # noqa: E402
