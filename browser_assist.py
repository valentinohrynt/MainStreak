#!/usr/bin/env python3
"""Open each pending TikTok profile and copy its message template.

This helper does not log in, inspect TikTok pages, click Message, or send DMs.
The user sends each message manually and confirms it here before it is recorded.
"""

import re
import shutil
import sqlite3
import subprocess
import sys
import webbrowser
from datetime import date
from pathlib import Path
from urllib.parse import quote

DB_PATH = Path(__file__).with_name("mainstreak.db")
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


def pending_friends():
    today = date.today().isoformat()
    with connect() as db:
        return db.execute(
            """
            SELECT name, username, message
            FROM friends
            WHERE last_confirmed_sent IS NULL
               OR last_confirmed_sent != ?
            ORDER BY name COLLATE NOCASE
            """,
            (today,),
        ).fetchall()


def copy_to_clipboard(message):
    """Copy text using a common Linux clipboard utility, if installed."""
    if shutil.which("wl-copy"):
        command = ["wl-copy"]
    elif shutil.which("xclip"):
        command = ["xclip", "-selection", "clipboard"]
    elif shutil.which("xsel"):
        command = ["xsel", "--clipboard", "--input"]
    else:
        return False

    try:
        subprocess.run(
            command,
            input=message,
            text=True,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def mark_sent(name):
    today = date.today().isoformat()
    with connect() as db:
        cursor = db.execute(
            "UPDATE friends SET last_confirmed_sent=? WHERE name=?",
            (today, name),
        )
    return cursor.rowcount > 0


def main():
    rows = pending_friends()
    if not rows:
        print(f"All tracked friends are already confirmed for {date.today().isoformat()}.")
        return 0

    print(f"MainStreak browser assist — {len(rows)} friend(s) pending today")
    print("A profile will open in your default browser for each friend.")
    print("You must click Message, paste the copied template, and send it yourself.")
    print("Only enter 's' after the DM has actually been sent.")
    print()

    for index, (name, username, message) in enumerate(rows, start=1):
        username = username.strip().lstrip("@")
        print(f"[{index}/{len(rows)}] {name} (@{username})")

        if not USERNAME_RE.fullmatch(username):
            print("  Skipped: username contains unsupported characters.")
            continue

        profile_url = f"https://www.tiktok.com/@{quote(username, safe='')}"
        opened = webbrowser.open_new_tab(profile_url)
        print(f"  Profile: {profile_url}")
        if not opened:
            print("  Could not open the browser automatically; open the profile URL above.")

        if copy_to_clipboard(message):
            print("  Message template copied to clipboard.")
        else:
            print("  Clipboard utility not found; copy the message below manually:")
            print(f"  {message}")

        print()
        while True:
            try:
                answer = input("After sending, type [s]ent; [Enter] to skip; [q]uit: ")
            except (EOFError, KeyboardInterrupt):
                print("\nStopped. Unconfirmed friends remain pending.")
                return 130

            answer = answer.strip().lower()
            if answer == "s":
                if mark_sent(name):
                    print(f"  Recorded today's confirmation for {name}.")
                else:
                    print(f"  Could not update {name}; check the friend list.")
                break
            if answer in ("", "n", "skip"):
                print("  Left pending.")
                break
            if answer in ("q", "quit"):
                print("Stopped. Remaining friends stay pending.")
                return 0
            print("Please enter s, Enter, or q.")

        print()

    print("Finished. Check the dashboard or run 'python3 main.py due' for the remaining list.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
