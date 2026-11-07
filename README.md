# Checklist Bot

A Telegram bot that replaces the paperwork which in return saves trees from cutting ^^.

Agents fill a flight with buttons (one tap stamps the current time), and the bot
produces a one-page PDF that looks like the paper form.

The layout comes from
`template/cover_sheet.xlsx`.

- Many users can work at the same time. Each user sees and edits **only the flights they created**.
- The signature on the PDF is the user's name (asked once at `/start`).
- The bot speaks **English (default) and Russian**. Each user picks a language. Only the chat is
  translated: the Excel template and the PDF stay the same.
- Data is stored in SQLite and **deleted automatically after 3 days**.
- Everything installs inside a Python virtualenv. No system packages and no LibreOffice.

## Folder layout

```
checklist-air/
├── main.py              # entry point (long polling), access control, hourly cleanup
├── handlers.py          # all bot conversations and buttons
├── views.py             # message texts + inline / reply keyboards
├── i18n.py              # English / Russian interface texts
├── db.py                # SQLite storage (aiosqlite)
├── fields.py            # form definition: fields, checklist, events, template cells
├── pdf.py               # fills the Excel template and draws it to PDF (reportlab)
├── template/
│   └── cover_sheet.xlsx # the form (single sheet) – edit in Excel if needed (git-ignored, see below)
├── fonts/               # Carlito (Calibri-compatible) + DejaVu Sans (for ✓)
├── requirements.txt
└── .env.example
```

## Install (Linux server)

Requires Python **3.10+** (`python3 --version`). On Debian/Ubuntu, `python3 -m venv` may need
the `python3-venv` package. That is the only possible system dependency.

```bash
cd checklist-air
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env            # put your BOT_TOKEN from @BotFather
```

## Run

```bash
.venv/bin/python main.py
```

Stop with `Ctrl+C`. The database `data.sqlite3` is created next to `main.py`.

### Run as a service (systemd, starts on boot)

Create `/etc/systemd/system/coversheet-bot.service` (adjust `User` and paths):

```ini
[Unit]
Description=Cover Sheet Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
User=youruser
WorkingDirectory=/home/youruser/checklist-air
ExecStart=/home/youruser/checklist-air/.venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now coversheet-bot
journalctl -u coversheet-bot -f      # logs
```

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `BOT_TOKEN` | required | Token from @BotFather |
| `ALLOWED_USERS` | empty = everyone | Comma-separated Telegram user IDs. A blocked user gets a message with their ID to send you. |
| `RETENTION_DAYS` | `3` | Flights older than this are deleted (checked every hour) |
| `DB_PATH` | `data.sqlite3` | Database file location |

After editing `.env`, restart the bot.

## How agents use it

1. `/start`, then send your full name (printed as the signature). Change it later with **👤 My name**.
   The welcome message has **🇬🇧 English / 🇷🇺 Русский** buttons. Switch any time with
   **🌐 Language** or `/lang`.
2. **➕ New flight**: a short wizard asks Date, Flight number, From, To, Type/Registration, STA,
   STD and Park position. For the date, tap **Today** or **Tomorrow** (Tashkent time) or type
   one (`dd.mm.yy`). Other steps show recent values as buttons. Optional steps have **⏭ Skip**.
3. The **flight card** opens with these buttons:
   - **🧾 Header**: edit any header field (PAX IN/OUT, TRS.PX, CGO IN/OUT, BAG IN/OUT, Delay, …).
   - **📑 Documents**: tap an item to cycle ✅ YES → ❌ NO → ➖ N/A → empty.
     **⚡ Apply default** sets the usual pattern in one tap.
   - **⏱ Timeline**: tap an event, then **Now** (current Tashkent time) or **✏️** to type HHMM.
     Start/finish events have two "now" buttons.
   - **📝 Remarks**: free text, wrapped onto the dotted lines of the form (max 450 characters).
   - **📄 Generate PDF**: sends the filled cover sheet as a PDF, e.g. `HY742-741_071126.pdf`.
   - **🗑 Delete**: removes the flight.
4. **📋 My flights** lists your flights from the last 3 days.

Commands: `/start`, `/new`, `/flights`, `/name`, `/lang`, `/cancel`. The bot sets this command menu
in Telegram itself: Russian for users whose Telegram app is in Russian, English for everyone else.

## Languages

All bot texts live in `i18n.py`: `TEXTS` for messages and buttons, `LABELS` for field, document
and event names. English is the default, and a missing Russian text falls back to English.
To change a wording, edit it there and restart the bot. To add a language, add a block to
`TEXTS` and `LABELS` and an entry to `LANGUAGES`.

Each user's choice is stored in the `users.lang` column. A database from an older version gets this
column added automatically on start, with English for existing users. In the same way, new header
fields such as BAG IN/OUT become new `flights` columns on start; nothing needs to be done by hand.

## Editing the template

`template/cover_sheet.xlsx` is a normal Excel file, and the PDF follows it: column widths, row
heights, merged cells, borders, fonts, font sizes, colours, the logo and margins.
You can change wording, fonts or sizes freely.

If you **move** a field to a different cell, update its address in `fields.py`
(`HEADER`, `CHECKLIST_FIRST_ROW`, `CHECK_COLUMNS`, `EVENTS_FIRST_ROW`, `EVENT_COLUMN`,
`REMARK_LINES`, `SIGNATURE_CELL`). The default checklist pattern is `CHECKLIST_DEFAULT` in the same file.

Note: `.gitignore` excludes `template/`, so the template is **not** in the git repository.
Keep a copy of `template/cover_sheet.xlsx` on the server. The bot needs it to make PDFs.
If you want it versioned, remove the `template/` line from `.gitignore`.

PDF fonts: the `Calibri` font in the template is drawn with the bundled **Carlito**, which has the
same letter widths, so the text fits the same way. `DejaVu Sans` is used for the ✓ marks.
Both fonts are free to redistribute (licences are in `fonts/`).

## Data & cleanup

- Tables: `users` (Telegram ID → name, language), `flights`, `checks` (document ticks), `times` (timeline).
- Every query filters by the flight owner, so users never see each other's flights.
- Every hour the bot deletes flights older than `RETENTION_DAYS`, together with their ticks and
  times, then compacts the database file. User names are kept.
- PDFs are generated in memory and never saved on the server.
- Unfinished conversation steps (e.g. a half-done wizard) are lost if the bot restarts. Saved flight data is not affected.

## Backup / reset

Stop the bot, then copy or delete `data.sqlite3` (and any `data.sqlite3-wal` / `-shm` files next to it).
