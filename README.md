# MainStreak

A lightweight daily TikTok streak tracker for Ubuntu. It stores friends, per-friend message templates, and daily send confirmations in SQLite.

> Important: This project does not log in to TikTok or send DMs. TikTok does not provide unrestricted personal-account DM automation. The app tracks who is due and records confirmations after you send messages yourself. Do not add password storage, CAPTCHA bypasses, private API calls, or other access-control workarounds.

## Requirements

- Ubuntu 22.04+ (also works on most recent Debian-based distributions)
- Python 3.10+
- No third-party Python packages

## Install

    sudo apt update
    sudo apt install -y python3
    git clone https://github.com/valentinohrynt/MainStreak.git
    cd MainStreak
    python3 -m venv .venv
    source .venv/bin/activate

## Add friends

    python main.py add --name "Alex" --username "alex123" --message "streak 🔥"
    python main.py add --name "Sam" --username "sam456" --message "daily streak check!"

## See who is due

    python main.py due

After sending a DM manually in TikTok, record it:

    python main.py mark --name "Alex"

List tracked friends:

    python main.py list

Remove a friend:

    python main.py remove --name "Alex"

## Daily report at 20:30

Set the server timezone:

    sudo timedatectl set-timezone Asia/Jakarta

Edit your crontab with crontab -e and add this line, replacing YOUR_USERNAME:

    30 20 * * * cd /home/YOUR_USERNAME/MainStreak && /usr/bin/python3 main.py due >> mainstreak.log 2>&1

Cron writes the daily pending-friend report to mainstreak.log. It does not send TikTok messages.

## Data and privacy

- SQLite data is stored locally in mainstreak.db.
- Do not commit the database, browser profiles, session cookies, or credentials.
- This repository intentionally contains no TikTok credentials or unofficial API integration.

## Roadmap

- [x] Local friend list and message templates
- [x] Daily due list and send confirmations
- [x] SQLite persistence
- [ ] Optional Telegram reminder
- [ ] Dashboard
- [ ] Official TikTok messaging integration, only if the account and use case are approved by TikTok
