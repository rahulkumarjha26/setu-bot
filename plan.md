# Setu Report Bot — Build Plan

## Stack
Python 3.11 · python-telegram-bot v21 (async) · Groq API (whisper-large-v3, llama-3.3-70b-versatile) · Supabase (Postgres + Storage) · Railway (polling, no webhooks)

## PHASE 0 — Project scaffold
Create:
- bot.py
- ai.py
- db.py
- config.py
- requirements.txt
- Dockerfile
- .env.example
- .gitignore
- README.md
- migrations/001_init.sql

## PHASE 1 — Config loader
`config.py` loads from env vars via python-dotenv.

## PHASE 2 — Database & Storage (Supabase)
- SQL schema in `migrations/001_init.sql`
- `db.py`: upload_media, insert_problem, update_status

## PHASE 3 — AI module (Groq)
`ai.py`: transcribe() + structure(), isolated so provider is swappable.

## PHASE 4 — The bot (conversation + admin approval)
`bot.py`: ConversationHandler for citizen flow, admin approve/reject via CallbackQueryHandler.

## PHASE 5 — Containerize & deploy on Railway
Dockerfile, deploy steps.

## Hard rules
- Nothing auto-published. Admin approval mandatory.
- reporter_telegram_id never exposed publicly.
- All model calls only in ai.py.
- Polling, no webhooks, no frontend.

## Credentials
- GitHub: https://github.com/rahulkumarjha26/setu-bot
- Admin: @setuindia (ID: 882210906)
- Bot: t.me/SetuReportBot (token: 8807691006:AAE2o8zBV4EqkY0pMpmCldDhr0P-kco8Uyo)
- Supabase: https://lspvejiwouhkqdtphxzn.supabase.co
