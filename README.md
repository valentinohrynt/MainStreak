# MainStreak

A lightweight daily TikTok streak helper for Ubuntu. It stores friends, per-friend message templates, and daily send confirmations in SQLite. It includes a CLI, local dashboard, supervised browser helper, and an optional Playwright sender for TikTok Web.

## Requirements

- Ubuntu 22.04+ (also works on recent Debian-based distributions)
- Python 3.10+
- Chromium installed by Playwright for the optional browser sender

## Install

    sudo apt update
    sudo apt install -y python3 python3-venv git
    git clone https://github.com/valentinohrynt/MainStreak.git
    cd MainStreak
    python3 -m venv .venv
    . .venv/bin/activate
    pip install -r requirements.txt
    python -m playwright install chromium

If Playwright reports missing system libraries, install its OS dependencies with:

    sudo .venv/bin/python -m playwright install-deps chromium

## Add friends

    .venv/bin/python main.py add --name "Alex" --username "alex123" --message "streak 🔥"
    .venv/bin/python main.py add --name "Sam" --username "sam456" --message "daily streak check!"

The username is the TikTok handle without @. Each friend can have a different message. Friend data and send dates are stored in the local SQLite database `mainstreak.db`.

## Optional TikTok Web automation

This uses a regular Playwright-controlled Chromium browser and TikTok's visible web interface. It does not use TikTok private endpoints, stealth plugins, browser fingerprint spoofing, CAPTCHA bypasses, or credential extraction.

**Platform note:** TikTok may restrict automated interactions under its terms and may show security checks or change its interface. Use only for friends who expect these messages. If TikTok presents a security challenge or blocks the action, stop; do not try to bypass it. UI automation is best-effort and is not an official TikTok integration.

### 1. Sign in once

    .venv/bin/python tiktok_sender.py --login

A normal Chromium window opens. Sign in to TikTok yourself, then return to the terminal and press Enter. The browser profile is saved in `browser-profile/` on this machine. It contains your authenticated session: do not share it, upload it, or commit it to Git.

### 2. Test a send while watching the browser

    .venv/bin/python tiktok_sender.py --send

The script processes friends who have not been recorded as sent today. It opens each TikTok profile, uses the visible Message control, fills the message composer, and clicks Send. A friend is marked for today only after the visible composer clears. This is a UI confirmation, not proof that the recipient received or read the message.

If a recipient cannot be messaged, the page layout changes, or a browser error occurs, that friend remains pending and the script reports the failure. Review the output before retrying. Do not run multiple sender instances at the same time.

### 3. Run headless or schedule once per day

After a successful visible test, a headless run can be used for a scheduled job:

    .venv/bin/python tiktok_sender.py --send --headless

To schedule it daily at 20:30, set the machine timezone and edit your crontab:

    sudo timedatectl set-timezone Asia/Jakarta
    crontab -e

Add this line, replacing `YOUR_USERNAME` with your Linux username:

    30 20 * * * cd /home/YOUR_USERNAME/MainStreak && /home/YOUR_USERNAME/MainStreak/.venv/bin/python tiktok_sender.py --send --headless >> tiktok_sender.log 2>&1

Cron only runs while the laptop is powered on. If it is asleep or powered off at 20:30, the job will not run at that time. Keep the machine awake and connected to the internet. A headless run may fail if TikTok requires a fresh login or interactive verification; run `--login` again manually when needed.

The sender uses one Chromium process and a small local SQLite database. On an 8 GB machine, close other browser windows during scheduled sending if memory is constrained.

## Local dashboard

Start the dashboard:

    .venv/bin/python webapp.py

Open http://127.0.0.1:8765 in your browser. Add friends, view who is pending, and record manual confirmations. The dashboard itself does not send TikTok messages.

The dashboard binds only to localhost. Do not change this to 0.0.0.0 or expose the port to the internet.

## Supervised browser helper

For manual sending without Playwright:

    .venv/bin/python browser_assist.py

For each pending friend, MainStreak opens their profile and copies the saved template to the clipboard. You click Message, paste and send it yourself, then type `s` in the terminal to record the confirmation. Install `wl-clipboard` for automatic clipboard copying on Wayland:

    sudo apt install -y wl-clipboard

## Command-line usage

    .venv/bin/python main.py due
    .venv/bin/python main.py list
    .venv/bin/python main.py mark --name "Alex"
    .venv/bin/python main.py remove --name "Alex"

## Data and privacy

- SQLite data is stored locally in `mainstreak.db`.
- The Playwright browser profile is stored in `browser-profile/` and contains your logged-in session.
- Both paths are ignored by Git. Never commit the database, browser profile, cookies, passwords, or session data.
- The dashboard listens only on `127.0.0.1`.
- The sender does not attempt to defeat TikTok security controls. If the normal web interface blocks an action, leave the friend pending and resolve it manually.
