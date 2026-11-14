#!/usr/bin/env python3
"""MainStreak local dashboard. Binds to localhost; does not send TikTok DMs."""

import html
import secrets
import sqlite3
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs

DB_PATH = Path(__file__).with_name("mainstreak.db")
HOST = "127.0.0.1"
PORT = 8765
FORM_TOKEN = secrets.token_urlsafe(32)


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


def esc(value):
    return html.escape(str(value), quote=True)


class Handler(BaseHTTPRequestHandler):
    def send_page(self, content, status=200):
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def page(self, notice=""):
        today = date.today().isoformat()
        with connect() as db:
            rows = db.execute(
                """SELECT name, username, message, last_confirmed_sent
                   FROM friends ORDER BY name COLLATE NOCASE"""
            ).fetchall()

        pending = sum(1 for row in rows if row[3] != today)
        cards = []
        for name, username, message, sent in rows:
            done = sent == today
            status = "Confirmed today" if done else "Pending today"
            action = ""
            if not done:
                action = f"""
                <form method="post" action="/mark">
                  <input type="hidden" name="token" value="{FORM_TOKEN}">
                  <input type="hidden" name="name" value="{esc(name)}">
                  <button type="submit">Mark sent</button>
                </form>"""
            cards.append(f"""
              <article class="friend">
                <div class="friend-head">
                  <div><h2>{esc(name)}</h2><p class="muted">@{esc(username)}</p></div>
                  <span class="status {'done' if done else 'pending'}">{status}</span>
                </div>
                <p class="message">{esc(message)}</p>
                <p class="muted">Last confirmation: {esc(sent or 'Never')}</p>
                {action}
                <form method="post" action="/remove" class="remove"
                      onsubmit="return confirm('Remove {esc(name)}?')">
                  <input type="hidden" name="token" value="{FORM_TOKEN}">
                  <input type="hidden" name="name" value="{esc(name)}">
                  <button class="quiet" type="submit">Remove</button>
                </form>
              </article>""")

        if not cards:
            cards_html = '<p class="empty">No friends added yet. Add your first friend below.</p>'
        else:
            cards_html = "\n".join(cards)

        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MainStreak Dashboard</title>
<style>
:root {{ color-scheme: dark; font-family: system-ui, sans-serif; }}
body {{ margin:0; background:#10141d; color:#edf1f7; }}
main {{ max-width:850px; margin:0 auto; padding:32px 18px 60px; }}
header {{ display:flex; justify-content:space-between; align-items:end; gap:16px; flex-wrap:wrap; }}
h1 {{ margin:0; font-size:2rem; }} h2 {{ margin:0; font-size:1.1rem; }}
.muted {{ color:#9aa6b7; font-size:.9rem; }}
.stats {{ background:#202938; border-radius:14px; padding:14px 18px; }}
.stats strong {{ font-size:1.5rem; display:block; }}
.notice {{ margin:18px 0; color:#a9d7ff; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:14px; margin:20px 0 34px; }}
.friend, .panel {{ background:#1a2230; border:1px solid #2b3749; border-radius:14px; padding:18px; }}
.friend-head {{ display:flex; justify-content:space-between; gap:10px; align-items:start; }}
.status {{ font-size:.78rem; border-radius:30px; padding:5px 9px; white-space:nowrap; }}
.done {{ background:#163d31; color:#8ce0b8; }} .pending {{ background:#49371b; color:#ffd58a; }}
.message {{ background:#111925; padding:11px; border-radius:8px; overflow-wrap:anywhere; }}
button {{ border:0; border-radius:8px; padding:10px 14px; background:#80bfff; color:#102033; font-weight:650; cursor:pointer; }}
.quiet {{ background:transparent; color:#aab6c6; padding:6px 0; }}
.remove {{ margin-top:8px; }}
label {{ display:block; margin:12px 0 5px; color:#c4cedb; }}
input, textarea {{ width:100%; box-sizing:border-box; padding:11px; border-radius:8px; border:1px solid #3b485b; background:#111925; color:#edf1f7; }}
textarea {{ min-height:80px; resize:vertical; }}
.add-button {{ margin-top:14px; width:100%; }}
.empty {{ color:#9aa6b7; padding:20px 0; }}
footer {{ color:#9aa6b7; font-size:.85rem; line-height:1.5; margin-top:24px; }}
</style></head><body><main>
<header><div><h1>MainStreak</h1><p class="muted">Daily streak checklist · {today}</p></div>
<div class="stats"><strong>{pending} / {len(rows)}</strong><span class="muted">pending today</span></div></header>
{f'<p class="notice">{esc(notice)}</p>' if notice else ''}
<h2>Friends</h2><section class="grid">{cards_html}</section>
<section class="panel"><h2>Add or update a friend</h2>
<form method="post" action="/add">
<input type="hidden" name="token" value="{FORM_TOKEN}">
<label for="name">Display name</label><input id="name" name="name" maxlength="80" required>
<label for="username">TikTok username (without @)</label><input id="username" name="username" maxlength="80" required>
<label for="message">Message template</label><textarea id="message" name="message" maxlength="500" required></textarea>
<button class="add-button" type="submit">Save friend</button></form></section>
<footer>Local dashboard only. MainStreak does not log in to TikTok or send messages. Send the DM yourself, then select “Mark sent”. The server listens only on 127.0.0.1.</footer>
</main></body></html>"""

    def do_GET(self):
        if self.path != "/":
            self.send_page("Not found", 404)
            return
        self.send_page(self.page())

    def do_POST(self):
        if self.path not in ("/add", "/mark", "/remove"):
            self.send_page("Not found", 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length > 10000:
            self.send_page("Request too large", 413)
            return
        data = parse_qs(self.rfile.read(length).decode("utf-8", "replace"))
        if not secrets.compare_digest(data.get("token", [""])[0], FORM_TOKEN):
            self.send_page("Invalid form token. Refresh the page and try again.", 403)
            return

        name = data.get("name", [""])[0].strip()
        notice = "No change made."
        if self.path == "/add":
            username = data.get("username", [""])[0].strip().lstrip("@")
            message = data.get("message", [""])[0].strip()
            if not name or not username or not message:
                notice = "Please complete all fields."
            elif len(name) > 80 or len(username) > 80 or len(message) > 500:
                notice = "One or more fields exceed the allowed length."
            else:
                with connect() as db:
                    db.execute(
                        """INSERT INTO friends(name, username, message)
                           VALUES (?, ?, ?)
                           ON CONFLICT(name) DO UPDATE SET
                           username=excluded.username, message=excluded.message""",
                        (name, username, message),
                    )
                notice = f"Saved {name}."
        elif self.path == "/mark":
            with connect() as db:
                cur = db.execute(
                    "UPDATE friends SET last_confirmed_sent=? WHERE name=?",
                    (date.today().isoformat(), name),
                )
            notice = f"Recorded today's confirmation for {name}." if cur.rowcount else "Friend not found."
        elif self.path == "/remove":
            with connect() as db:
                cur = db.execute("DELETE FROM friends WHERE name=?", (name,))
            notice = f"Removed {name}." if cur.rowcount else "Friend not found."

        self.send_page(self.page(notice))

    def log_message(self, fmt, *args):
        # Keep request logs quiet; no message templates or form values are logged.
        return


if __name__ == "__main__":
    print(f"MainStreak dashboard: http://{HOST}:{PORT}")
    print("Press Ctrl+C to stop. This app does not send TikTok DMs.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
