#!/usr/bin/env python3
"""MainStreak TikTok Web sender using a normal Playwright Chromium profile.

No stealth plugins, fingerprint spoofing, private endpoints, CAPTCHA bypass, or
credential extraction. Login is performed manually in a persistent local profile.
TikTok may restrict automated use; stop if the site presents a security challenge.
"""

import argparse
import re
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "mainstreak.db"
PROFILE_PATH = ROOT / "browser-profile"
TIKTOK_HOME = "https://www.tiktok.com/"
USERNAME_RE = re.compile(r"^[A-Za-z0-9._]{1,24}$")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            last_confirmed_sent TEXT
        )
        """
    )
    return db


def login():
    """Open a normal visible browser; the user signs in manually."""
    PROFILE_PATH.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_PATH),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(TIKTOK_HOME, wait_until="domcontentloaded")
        print("Log in to TikTok in the opened browser window.")
        print("When you can see that you are logged in, return here and press Enter.")
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            print("\nLogin setup cancelled.")
        finally:
            context.close()
    print("Browser profile saved locally. Keep browser-profile private; it contains your login session.")


def visible_first(locator):
    """Return the first visible match, or None."""
    try:
        count = min(locator.count(), 10)
        for index in range(count):
            item = locator.nth(index)
            if item.is_visible():
                return item
    except Exception:
        return None
    return None


def open_conversation(page, username):
    profile_url = f"https://www.tiktok.com/@{quote(username, safe='')}"
    page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)

    # The recipient's privacy settings may prevent starting a conversation.
    message_control = visible_first(page.get_by_role("button", name=re.compile(r"^message$", re.I)))
    if message_control is None:
        message_control = visible_first(page.get_by_role("link", name=re.compile(r"^message$", re.I)))
    if message_control is None:
        message_control = visible_first(page.get_by_text("Message", exact=True))

    if message_control is None:
        raise RuntimeError("TikTok did not show a Message control for this profile.")
    message_control.click(timeout=15000)

    composer = page.locator('[data-e2e="message-input-area"]').first
    try:
        composer.wait_for(state="visible", timeout=15000)
    except PlaywrightTimeoutError:
        # Fallback for UI variants that expose the editor as an accessible textbox.
        composer = page.get_by_role("textbox").last
        composer.wait_for(state="visible", timeout=10000)
    return composer


def send_one(page, name, username, message):
    if not USERNAME_RE.fullmatch(username):
        raise RuntimeError("Username format is invalid; expected the TikTok handle without @.")

    composer = open_conversation(page, username)
    composer.fill(message, timeout=15000)

    send_control = visible_first(page.locator('[data-e2e="message-send"]'))
    if send_control is None:
        send_control = visible_first(page.get_by_role("button", name=re.compile(r"^send$", re.I)))
    if send_control is None:
        raise RuntimeError("Message composer is visible, but TikTok's Send control was not found.")

    send_control.click(timeout=15000)
    # Only record a recipient after the visible editor has consumed the draft.
    composer.wait_for(state="visible", timeout=10000)
    try:
        from playwright.sync_api import expect
        expect(composer).to_be_empty(timeout=15000)
    except Exception as exc:
        raise RuntimeError("TikTok did not clear the message draft; leaving this friend pending.") from exc

    today = date.today().isoformat()
    with connect() as db:
        cursor = db.execute(
            "UPDATE friends SET last_confirmed_sent=? WHERE name=?",
            (today, name),
        )
    if cursor.rowcount != 1:
        raise RuntimeError("Message was submitted, but the friend record could not be updated.")
    print(f"Submitted in TikTok UI: {name} (@{username}).")


def pending_friends():
    today = date.today().isoformat()
    with connect() as db:
        return db.execute(
            """
            SELECT name, username, message
            FROM friends
            WHERE last_confirmed_sent IS NULL OR last_confirmed_sent != ?
            ORDER BY name COLLATE NOCASE
            """,
            (today,),
        ).fetchall()


def send_all(headless=False, delay_seconds=4):
    if not DB_PATH.exists():
        print("No MainStreak database found. Add friends first with main.py.", file=sys.stderr)
        return 2

    rows = pending_friends()
    if not rows:
        print(f"No pending friends for {date.today().isoformat()}.")
        return 0

    if not PROFILE_PATH.exists():
        print("No browser profile found. Run: python3 tiktok_sender.py --login", file=sys.stderr)
        return 2

    failures = []
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_PATH),
            headless=headless,
            viewport={"width": 1280, "height": 900},
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            for index, (name, username, message) in enumerate(rows):
                try:
                    send_one(page, name, username, message)
                except Exception as exc:
                    failures.append((name, str(exc)))
                    print(f"FAILED: {name} (@{username}): {exc}", file=sys.stderr)
                if index < len(rows) - 1:
                    time.sleep(max(0, delay_seconds))
        finally:
            context.close()

    if failures:
        print("\nSome recipients remain pending; review errors before retrying.")
        return 1
    print("\nAll pending messages were submitted in the TikTok interface.")
    print("This confirms the composer cleared, not that the recipient read or received the message.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="MainStreak TikTok Web browser automation")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--login", action="store_true", help="open TikTok for manual login and save a local browser profile")
    group.add_argument("--send", action="store_true", help="send today's pending messages through TikTok Web")
    parser.add_argument("--headless", action="store_true", help="run Chromium without a visible window (for scheduled jobs)")
    parser.add_argument("--delay", type=float, default=4.0, help="seconds between recipients (default: 4)")
    args = parser.parse_args()

    if args.login:
        login()
        return 0
    return send_all(headless=args.headless, delay_seconds=args.delay)


if __name__ == "__main__":
    raise SystemExit(main())
