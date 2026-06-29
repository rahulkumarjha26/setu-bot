# Setu Report Bot

A Telegram bot for reporting civic and development problems in India. Citizens send voice/video/photo reports, the bot structures them using AI, and an admin approves before public publication.

## Prerequisites

- Python 3.11+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- A Groq API key (from [console.groq.com](https://console.groq.com))
- A Supabase project (from [supabase.com](https://supabase.com))

## Setup

### 1. Clone & install

```bash
git clone https://github.com/rahulkumarjha26/setu-bot.git
cd setu-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

Copy `.env.example` to `.env` and fill in:

```bash
cp .env.example .env
```

| Variable | How to get |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather → /newbot → copy token |
| `GROQ_API_KEY` | https://console.groq.com → API Keys |
| `SUPABASE_URL` | Supabase → Project Settings → API → Project URL |
| `SUPABASE_SERVICE_KEY` | Supabase → Project Settings → API → service_role key (NOT anon) |
| `ADMIN_TELEGRAM_ID` | Message [@userinfobot](https://t.me/userinfobot) → copy your ID |
| `R2_ENDPOINT` | Cloudflare R2 → Bucket → Settings → S3 API endpoint |
| `R2_ACCESS_KEY` | Cloudflare R2 → Manage R2 API Tokens → Create → Access Key ID |
| `R2_SECRET_KEY` | Cloudflare R2 → Manage R2 API Tokens → Create → Secret Access Key |
| `R2_BUCKET` | `setu-media` (or your bucket name) |
| `R2_PUBLIC_URL` | R2 bucket public URL (must end without trailing slash) |

### 3. Supabase database

Open Supabase → SQL Editor → paste this:

```sql
create extension if not exists "pgcrypto";

create table if not exists problems (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz default now(),
  reporter_telegram_id bigint,
  reporter_handle text,
  media_type text,
  media_url text,
  transcript text,
  detected_language text,
  title text,
  description text,
  category text,
  legality_bin text,
  severity text,
  latitude double precision,
  longitude double precision,
  consent_public boolean default false,
  consent_contact boolean default false,
  status text default 'pending_review',
  upvotes integer default 0
);

create index if not exists idx_problems_status on problems(status);
```

### 4. Supabase Storage

Supabase → Storage → New bucket → name: `media` → toggle **Public bucket** → Create.

### 5. Run locally

```bash
source venv/bin/activate
python bot.py
```

You should see: `Setu bot running (polling)…`

## Deploy to Railway

1. Push the repo to GitHub: `git push origin main`
2. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
3. Select the `setu-bot` repository
4. Go to **Variables** tab and add all 5 environment variables (same as `.env`)
5. Railway auto-builds the Dockerfile and runs the bot
6. Check **Deployments** → **Logs** to confirm: `Setu bot running (polling)…`

## Acceptance criteria (CHECKPOINT 4)

1. Open Telegram → `/start` on @SetuReportBot
2. Send a voice note describing a problem (e.g., "The girls toilet at the school has been broken for a year")
3. Tap 📍 Share location
4. Tap ✅ Yes, I agree
5. Within ~10s, admin account receives an approval card with title, category, and 💚 fundable bin
6. Tap **Approve & Publish** → row flips to `published` in Supabase → reporter gets "live on the map" message

## Architecture

- **Python 3.11** + **python-telegram-bot v21** (async, polling)
- **Groq API**: `whisper-large-v3` for speech-to-text, `llama-3.3-70b-versatile` for structuring
- **Supabase**: PostgreSQL (problems table)
- **Cloudflare R2**: Media storage (S3-compatible, 10 GB free)
- **Railway**: Dockerized polling deployment (no webhooks)

## Rules

- Nothing is auto-published. Admin approval is mandatory.
- `reporter_telegram_id` is never returned in any public-facing query.
- All AI model calls live in `ai.py` for easy provider swap.
- Government routing is ASSISTED (citizen submits), never silent auto-submission.
- One service, one repo, polling, no frontend.

## Features

- **Multilingual greetings**: Bot responds in Hindi, Bengali, Tamil, Telugu, or Kannada based on script detection (zero API cost)
- **Main menu**: "Report a problem", "What is Setu?", "See the map" buttons
- **Catch-all handler**: Any message outside the report flow gets a warm greeting + menu
- **Cloudflare R2 storage**: Media stored in R2 (10 GB free), with Supabase Storage fallback
- **Assisted government routing**: For statutory wounds, citizen gets a pre-filled complaint with one-tap link to the official channel
