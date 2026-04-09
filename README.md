# TechPrep

A personal technical interview preparation app with spaced repetition (SM-2), an AI coach, practice sessions, and a Telegram bot.

## Features

- **AI Coach** — chat-based interface to build and manage your study plan (themes, questions, settings)
- **Interview Practice** — answer questions one by one with instant AI feedback and SM-2 grading
- **Mock Interview** — timed session with all feedback delivered at the end
- **Spaced Repetition** — SM-2 algorithm schedules reviews based on your performance
- **Dashboard** — progress overview, activity heatmap, per-theme stats
- **Multi-plan** — multiple independent study plans per user
- **Telegram Bot** — practice on your phone via voice or text messages
- **Voice answers** — OpenAI Whisper transcribes voice messages before evaluation

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy, Alembic |
| AI | Anthropic Claude (coach + evaluator), OpenAI Whisper (voice) |
| Auth | JWT (python-jose + passlib/bcrypt) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Frontend | React, Vite, Tailwind CSS |
| Bot | python-telegram-bot v21 |

## Project Structure

```
TechPrep/
├── backend/
│   ├── agents/          # Coach agent (tool-use loop) + Interview evaluator
│   ├── bot/             # Telegram bot
│   ├── routers/         # FastAPI route handlers
│   ├── services/        # SM-2 algorithm, Whisper transcription, question generation
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   └── database.py
├── frontend/
│   └── src/
│       ├── api/         # API client functions
│       ├── components/  # Navbar, ProtectedRoute, modals
│       ├── context/     # PlanContext (active plan state)
│       └── pages/       # Login, Plans, Coach, Interview, Dashboard
├── alembic/             # DB migrations
├── requirements.txt
├── railway.toml         # Railway deployment config (backend)
└── railway.bot.toml     # Railway deployment config (bot)
```

## Local Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- API keys: Anthropic, OpenAI, Telegram Bot Token

### Backend

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # fill in your API keys
alembic upgrade head           # run DB migrations

uvicorn backend.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Telegram Bot

```bash
source .venv/bin/activate
python -m backend.bot.telegram_bot
```

## Environment Variables

| Variable | Description |
|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (Claude) |
| `OPENAI_API_KEY` | OpenAI API key (Whisper) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token from @BotFather |
| `DATABASE_URL` | SQLAlchemy DB URL (defaults to `sqlite:///./techprep.db`) |
| `SECRET_KEY` | JWT signing secret (use a long random string in production) |
| `FRONTEND_URL` | Production frontend URL for CORS (e.g. `https://yourapp.vercel.app`) |

## Deployment

See deployment instructions for [Railway](https://railway.app) (backend + bot) and [Vercel](https://vercel.com) (frontend) in the project docs.

### Frontend env variable (Vercel)
```
VITE_API_URL=https://your-backend.up.railway.app
```

## Telegram Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and plan overview |
| `/link <code>` | Link to your web app account (get code from the app) |
| `/plan` | Switch active study plan |
| `/practice` | Start a practice session |
| `/mock` | Start a timed mock interview |
| `/stop` | End the current session |
| `/skip` | Skip the current question |
