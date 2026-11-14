#!/usr/bin/env python3
"""MainStreak: local daily streak tracker (does not send TikTok DMs)."""

import argparse
import sqlite3
from datetime import date
from pathlib import Path

DB_PATH = Path(__file__).with_name("mainstreak.db")


def connect():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            last_confirmed_sent TEXT
        )
    """)
    return db


def add_friend(args):
    with connect() as db:
        db.execute(
            """INSERT INTO friends(name, username, message)
               VALUES (?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                 username=excluded.username,
                 message=excluded.message""",
            (args.name, args.username.lstrip("@"), args.message),
        )
    print(f"Saved {args.name}.")


def due(_args):
    today = date.today().isoformat()
    with connect() as db:
        rows = db.execute(
            """SELECT name, username, message FROM friends
               WHERE last_confirmed_sent IS NULL
                  OR last_confirmed_sent != ?
               ORDER BY name COLLATE NOCASE""",
            (today,),
        ).fetchall()

    if not rows:
        print(f"All tracked friends are confirmed for {today}.")
        return

    print(f"MainStreak — pending friends for {today}")
    print("Send these messages manually in TikTok, then use the mark command.")
    for name, username, message in rows:
        print(f"- {name} (@{username}): {message}")


def mark_sent(args):
    today = date.today().isoformat()
    with connect() as db:
        cur = db.execute(
            "UPDATE friends SET last_confirmed_sent=? WHERE name=?",
            (today, args.name),
        )
    if cur.rowcount:
        print(f"Recorded today's send confirmation for {args.name}.")
    else:
        print(f"No friend named {args.name!r}. Add them first.")


def list_friends(_args):
    with connect() as db:
        rows = db.execute(
            """SELECT name, username, message, last_confirmed_sent
               FROM friends ORDER BY name COLLATE NOCASE"""
        ).fetchall()
    if not rows:
        print("No friends yet. Use the add command.")
        return
    for name, username, message, sent in rows:
        print(f"{name} (@{username}) | message={message!r} | last confirmed={sent or 'never'}")


def remove_friend(args):
    with connect() as db:
        cur = db.execute("DELETE FROM friends WHERE name=?", (args.name,))
    print("Removed." if cur.rowcount else f"No friend named {args.name!r}.")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Track daily streak messages; this tool does not send DMs."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("add", help="Add or update a friend")
    p.add_argument("--name", required=True)
    p.add_argument("--username", required=True)
    p.add_argument("--message", required=True)
    p.set_defaults(func=add_friend)

    p = commands.add_parser("due", help="Show friends not confirmed today")
    p.set_defaults(func=due)

    p = commands.add_parser("mark", help="Record a message you sent manually")
    p.add_argument("--name", required=True)
    p.set_defaults(func=mark_sent)

    p = commands.add_parser("list", help="List tracked friends")
    p.set_defaults(func=list_friends)

    p = commands.add_parser("remove", help="Remove a friend")
    p.add_argument("--name", required=True)
    p.set_defaults(func=remove_friend)
    return parser


if __name__ == "__main__":
    parsed = build_parser().parse_args()
    parsed.func(parsed)
