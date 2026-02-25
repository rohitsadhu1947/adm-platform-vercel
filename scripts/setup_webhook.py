#!/usr/bin/env python3
"""
Register Telegram webhook URL.

Run this ONCE after the first successful Vercel deployment.

Usage:
    TELEGRAM_BOT_TOKEN=... TELEGRAM_WEBHOOK_URL=... python scripts/setup_webhook.py

Or set the env vars in your shell / .env file first.

IMPORTANT: Before running this, either:
  - Stop the Railway instance, OR
  - Remove TELEGRAM_BOT_TOKEN from Railway env vars
  Otherwise Railway's polling and Vercel's webhook will CONFLICT.
"""

import os
import sys

try:
    import requests
except ImportError:
    print("Installing requests...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests


def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN environment variable is not set.")
        print("  export TELEGRAM_BOT_TOKEN=your_bot_token")
        sys.exit(1)

    webhook_url = os.environ.get(
        "TELEGRAM_WEBHOOK_URL",
        "https://adm-platform-vercel.vercel.app/api/v1/telegram/webhook",
    )

    print(f"Bot Token: {token[:10]}...{token[-5:]}")
    print(f"Webhook URL: {webhook_url}")
    print()

    # Step 1: Delete any existing webhook
    print("Step 1: Deleting existing webhook...")
    resp = requests.get(
        f"https://api.telegram.org/bot{token}/deleteWebhook",
        params={"drop_pending_updates": True},
    )
    print(f"  Response: {resp.json()}")
    print()

    # Step 2: Set the new webhook
    print("Step 2: Setting new webhook...")
    resp = requests.post(
        f"https://api.telegram.org/bot{token}/setWebhook",
        json={
            "url": webhook_url,
            "allowed_updates": ["message", "callback_query", "my_chat_member"],
            "drop_pending_updates": True,
        },
    )
    result = resp.json()
    print(f"  Response: {result}")
    print()

    if result.get("ok"):
        print("SUCCESS! Webhook is now active.")
        print(f"  Telegram will send updates to: {webhook_url}")
    else:
        print("FAILED! Check the error above.")
        sys.exit(1)

    # Step 3: Verify
    print()
    print("Step 3: Verifying webhook info...")
    resp = requests.get(f"https://api.telegram.org/bot{token}/getWebhookInfo")
    info = resp.json()
    print(f"  Webhook URL: {info.get('result', {}).get('url', 'none')}")
    print(f"  Pending updates: {info.get('result', {}).get('pending_update_count', 0)}")
    print(f"  Last error: {info.get('result', {}).get('last_error_message', 'none')}")


if __name__ == "__main__":
    main()
