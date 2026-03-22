# 🤖 Telegram AI Companion

A self-hosted, privacy-conscious AI companion chatbot for Telegram with multi-persona support, scoped memory per user per bot, proactive messaging, and vendor-agnostic LLM integration.

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Data Model](#data-model)
- [Feature Status](#feature-status)
- [Environment Configuration](#environment-configuration)
- [Development Setup](#development-setup)
- [Deployment](#deployment)
- [Developer Notes for AI Agents](#developer-notes-for-ai-agents)

---

## Project Overview

A Telegram bot system where each bot instance acts as a distinct AI persona (e.g. "Mia", "Alex") with its own character, memory, and relationship state per user. Designed to be:

- **Semi-public** — accessible via direct link, not searchable; family/friends only via allowlist + invite tokens
- **Privacy-conscious** — all data stored locally or on self-hosted infrastructure; Telegram cloud only sees message content (standard Telegram limitation for non-secret-chats)
- **Vendor-agnostic** — swap between KoboldCPP, Ollama, OpenAI, Anthropic by changing one env var
- **Scalable** — single app instance serves multiple personas; new persona = one DB row, no code change

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Users (you + family)                      │
│                    Telegram App (any device)                     │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTPS — Telegram cloud (not E2E for bots)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Telegram Bot API (Official)                  │
│  Webhook push OR long polling to your server                     │
│  Handles: text, voice, photo, sticker, document natively         │
└────────────────────────────┬─────────────────────────────────────┘
                             │ Webhook POST / polling
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Your Server (VPS / local)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  FastAPI + aiogram (Python)                              │   │
│  │                                                          │   │
│  │  Middleware Layer                                        │   │
│  │  ├── AllowlistMiddleware   (gate by user_id)             │   │
│  │  └── BotRouter             (resolve bot_id from path)    │   │
│  │                                                          │   │
│  │  Handlers                                                │   │
│  │  ├── commands.py           (/start, /help)               │   │
│  │  ├── messages.py           (plain text → LLM reply)      │   │
│  │  ├── media.py              (voice → whisper, image → vision) │
│  │  └── admin.py              (invite token generation)     │   │
│  │                                                          │   │
│  │  Services                                                │   │
│  │  ├── chat_service.py       (orchestrate: prompt → LLM)   │   │
│  │  ├── memory_service.py     (RAG retrieval + storage)     │   │
│  │  ├── media_service.py      (transcription, vision)       │   │
│  │  └── scheduler_service.py  (proactive message logic)     │   │
│  │                                                          │   │
│  │  LLM Layer                                               │   │
│  │  ├── adapter.py            (provider-agnostic client)    │   │
│  │  └── prompts.py            (system prompt builder)       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────┐   ┌──────────────────────────────────────┐ │
│  │   ChromaDB      │   │   SQLite (dev) / PostgreSQL (prod)   │ │
│  │   (vector/RAG)  │   │   managed via SQLAlchemy + Alembic   │ │
│  └─────────────────┘   └──────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  APScheduler — proactive messaging (interval + cron)     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  LLM Backend (one active at a time, set via .env)        │   │
│  │  ├── KoboldCPP  (local, http://localhost:5001/v1)        │   │
│  │  ├── Ollama     (local, http://localhost:11434/v1)       │   │
│  │  ├── OpenAI     (cloud, https://api.openai.com/v1)       │   │
│  │  └── Anthropic  (cloud, OpenAI-compat or native)         │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Access Control Flow

```
Incoming message
      │
      ▼
AllowlistMiddleware
      ├── user_id in allowlist? ──► pass through to handler
      └── not in allowlist?
              ├── has valid invite token? ──► add to allowlist, pass through
              └── no token? ──────────────► silently drop
```

### Multi-Persona Routing (webhook mode)

```
POST /webhook/mia    ──►  BotRouter resolves bot_id="mia"
POST /webhook/alex   ──►  BotRouter resolves bot_id="alex"
                          │
                          ▼
                    loads persona config from DB
                    scopes memory to (bot_id, user_id)
```

---

## Tech Stack

| Layer | Tool | Notes |
|---|---|---|
| Bot framework | `aiogram` 3.x | async, Router-based handlers |
| Web server | `FastAPI` + `uvicorn` | webhook mode only; not needed for polling |
| LLM client | `openai` Python SDK | pointed at any OpenAI-compatible base_url |
| ORM | `SQLAlchemy` 2.x async | database-agnostic |
| Migrations | `Alembic` | versioned schema, autogenerate supported |
| Vector DB | `ChromaDB` | local, no separate server needed |
| DB (dev) | `SQLite` + `aiosqlite` | file-based, zero config |
| DB (prod) | `PostgreSQL` + `asyncpg` | DigitalOcean managed DB |
| Scheduler | `APScheduler` | async, in-process, low maintenance |
| Config | `pydantic-settings` | typed env vars, validates at startup |
| Containerization | `Docker` + `docker compose` | same image for dev and prod |
| Transcription | `whisper` / Whisper API | for voice message handling |
| Vision | LLaVA (local) or GPT-4o | for image/meme handling |

---

## Project Structure

```
telegram-companion/
│
├── app/
│   ├── main.py                  # entry point; polling/webhook branch
│   ├── config.py                # pydantic-settings; single source of truth
│   ├── bot.py                   # Bot + Dispatcher singletons
│   │
│   ├── handlers/
│   │   ├── commands.py          # /start, /help
│   │   ├── messages.py          # plain text handler → chat_service
│   │   ├── media.py             # voice + image handlers (TODO)
│   │   └── admin.py             # invite token commands (TODO)
│   │
│   ├── services/
│   │   ├── chat_service.py      # prompt assembly, history, LLM call
│   │   ├── memory_service.py    # ChromaDB read/write, preference extract (TODO)
│   │   ├── media_service.py     # transcription + vision description (TODO)
│   │   └── scheduler_service.py # proactive message generation + sending (TODO)
│   │
│   ├── llm/
│   │   ├── adapter.py           # LLMAdapter; AsyncOpenAI wrapper
│   │   └── prompts.py           # build_system_prompt(); persona → string
│   │
│   ├── db/
│   │   ├── base.py              # SQLAlchemy DeclarativeBase
│   │   ├── session.py           # async engine + get_session() context manager
│   │   ├── models/
│   │   │   ├── bot.py           # Bot persona registry
│   │   │   ├── user.py          # Telegram user + allowlist
│   │   │   ├── relationship.py  # (bot_id, user_id) scoped state
│   │   │   ├── message.py       # message history log
│   │   │   └── companion_event.py  # life events for proactive messages
│   │   └── repositories/
│   │       ├── base.py          # GenericRepository (CRUD)
│   │       ├── user.py          # UserRepository + domain methods
│   │       ├── bot.py           # BotRepository (TODO)
│   │       └── relationship.py  # RelationshipRepository (TODO)
│   │
│   └── middleware/
│       ├── allowlist.py         # AllowlistMiddleware (TODO)
│       └── bot_router.py        # multi-persona webhook routing (TODO)
│
├── alembic/
│   ├── versions/                # migration files (auto-generated)
│   └── env.py                   # configured to read DATABASE_URL from settings
│
├── tests/
│   └── test_user_repository.py  # async CRUD tests (in-memory SQLite)
│
├── data/                        # gitignored; local runtime data
│   ├── sqlite/
│   │   └── companion.db
│   └── chroma/
│
├── .env                         # gitignored; actual secrets
├── .env.example                 # committed; template for new devs
├── .gitignore
├── alembic.ini
├── docker-compose.yml           # local dev
├── docker-compose.prod.yml      # production overrides
├── Dockerfile
└── requirements.txt
```

---

## Data Model

### SQLite / PostgreSQL (structured)

```
bots ──────────────────────────────────────────────────────
  bot_id          TEXT  PK          e.g. "mia", "alex"
  display_name    TEXT
  telegram_token  TEXT              encrypted at rest in prod
  persona_config  JSON              character card, nsfw_allowed, tone, etc.
  is_active       BOOL  default=True
  created_at      DATETIME

users ─────────────────────────────────────────────────────
  user_id         INT   PK          Telegram user_id
  username        TEXT  nullable
  first_name      TEXT  nullable
  is_allowed      BOOL  default=False
  invite_token    TEXT  nullable     one-time use
  joined_at       DATETIME nullable

bot_user_relationships ────────────────────────────────────
  bot_id          TEXT  FK → bots      ┐
  user_id         INT   FK → users     ┘ composite PK
  relationship_state  JSON             intimacy level, nicknames
  user_preferences    JSON             likes black, hates mornings...
  last_interaction    DATETIME
  message_count       INT  default=0

messages ──────────────────────────────────────────────────
  message_id      TEXT  PK  (uuid4)
  bot_id          TEXT  FK → bots
  user_id         INT   FK → users
  direction       ENUM  inbound | outbound
  content_type    ENUM  text | audio | image | sticker
  content         TEXT  nullable
  attachment_path TEXT  nullable
  metadata_       JSON             reply_latency, tokens_used, etc.
  created_at      DATETIME

companion_events ──────────────────────────────────────────
  event_id        TEXT  PK  (uuid4)
  bot_id          TEXT  FK → bots
  event_summary   TEXT             "went hiking at Bastei with Jane"
  event_date      DATE
  used_count      INT  default=0
  created_at      DATETIME

scheduled_messages ────────────────────────────────────────
  job_id          TEXT  PK
  bot_id          TEXT
  user_id         INT
  trigger_type    TEXT             interval | cron | one-shot
  trigger_config  JSON             {hours: 48, jitter: 3600}
  last_fired      DATETIME nullable
  is_active       BOOL  default=True
```

### ChromaDB (vector / RAG)

Collection naming convention: `{bot_id}__{scope}`

```
mia__user_123456       per-user memories for bot "mia" with user 123456
mia__life_events       mia's backstory and life event pool
alex__user_123456      alex's separate memory of the same user
```

Document metadata schema per collection entry:
```json
{
  "type": "preference | event | emotion | fact",
  "bot_id": "mia",
  "user_id": 123456,
  "source_message_id": "uuid",
  "timestamp": "ISO8601"
}
```

---

## Feature Status

| Feature | Status | Notes |
|---|---|---|
| Telegram polling mode | ✅ Done | |
| Telegram webhook mode | 🔲 Stubbed | needs FastAPI wiring + Cloudflare Tunnel |
| `/start` command | ✅ Done | |
| Plain text → LLM reply | ✅ Done | in-memory history |
| Vendor-agnostic LLM adapter | ✅ Done | KoboldCPP / Ollama / OpenAI compatible |
| `config.py` with pydantic-settings | ✅ Done | |
| Docker (local) | ✅ Done | |
| SQLAlchemy models (all 5) | ✅ Done | |
| Alembic migrations | ✅ Done | initial schema applied |
| UserRepository + tests | ✅ Done | |
| BotRepository | 🔲 TODO | |
| RelationshipRepository | 🔲 TODO | |
| AllowlistMiddleware | 🔲 TODO | gate by user_id |
| Invite token flow | 🔲 TODO | `/start INV_xxx` → auto-allowlist |
| DB-backed chat history | 🔲 TODO | replace in-memory `_histories` |
| ChromaDB RAG memory | 🔲 TODO | preference extraction + retrieval |
| Multi-persona BotRouter | 🔲 TODO | resolve bot_id from webhook path |
| Persona config from DB | 🔲 TODO | replace hardcoded system prompt |
| Voice message handling | 🔲 TODO | Whisper transcription |
| Image/meme handling | 🔲 TODO | vision model description |
| Proactive messaging scheduler | 🔲 TODO | APScheduler + companion_events |
| Birthday / holiday triggers | 🔲 TODO | cron jobs per user |
| Companion vulnerability state | 🔲 TODO | mood/energy in relationship JSON |
| PostgreSQL + prod docker-compose | 🔲 TODO | |
| CI/CD (GitHub Actions → VPS) | 🔲 TODO | |

---

## Environment Configuration

```ini
# .env.example — copy to .env and fill in values

# Telegram
TELEGRAM_BOT_TOKEN=            # from @BotFather
APP_MODE=polling               # polling | webhook

# Webhook (only needed when APP_MODE=webhook)
WEBHOOK_HOST=                  # https://your-domain.com
WEBHOOK_PATH=                  # /webhook/secret-string

# LLM
LLM_PROVIDER=koboldcpp         # koboldcpp | ollama | openai | anthropic
LLM_BASE_URL=http://host.docker.internal:5001/v1
LLM_MODEL=koboldcpp            # ignored by koboldcpp, required by openai
LLM_API_KEY=none               # placeholder for local providers
LLM_MAX_TOKENS=300
LLM_TEMPERATURE=0.9

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/sqlite/companion.db
# prod: postgresql+asyncpg://user:pass@host/dbname

# App
ENVIRONMENT=dev                # dev | prod
DATA_DIR=./data
```

---

## Development Setup

```bash
# 1. clone repo
git clone <repo>
cd telegram-companion

# 2. create conda env
conda create -n companion python=3.11
conda activate companion

# 3. install dependencies
pip install -r requirements.txt

# 4. configure secrets
cp .env.example .env
# edit .env with your bot token + LLM settings

# 5. run database migrations
alembic upgrade head

# 6. run locally (no Docker)
python -m app.main

# 7. run in Docker
docker compose build
docker compose up
```

### Testing

```bash
# run repository tests (in-memory SQLite, no .env needed)
python tests/test_user_repository.py
```

---

## Deployment

### DigitalOcean (recommended)

1. Provision a Droplet (min 1GB RAM) or use App Platform
2. Install Docker + docker compose on the Droplet
3. Set up DigitalOcean Managed PostgreSQL — copy the connection string
4. Set environment variables in DO dashboard (never in committed files)
5. Point your domain DNS to Droplet IP
6. Cloudflare proxies HTTPS automatically — or use Certbot for Let's Encrypt

```bash
# on VPS — pull and run
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### CI/CD (GitHub Actions — TODO)

```
push to main
    → build Docker image
    → push to ghcr.io
    → SSH to VPS
    → docker compose pull + up -d
```

---

## Developer Notes for AI Agents

> Read this section carefully before making any changes to this codebase.

### Project Philosophy

- **Handlers never touch the DB directly.** The call chain is always: `handler → service → repository`. If you find SQL or SQLAlchemy sessions in a handler file, that is a bug.
- **No hardcoded values anywhere.** All configuration flows through `app/config.py` via `settings`. Never add raw strings for tokens, URLs, or model names to source files.
- **Memory is always scoped to `(bot_id, user_id)`**, never just `user_id`. A user talking to "Mia" has completely separate state from the same user talking to "Alex". This is the central invariant of the system.
- **The LLM adapter is the only file that knows about providers.** `chat_service.py` calls `llm.chat(messages)` and receives a string. It does not know or care whether the backend is KoboldCPP, Ollama, or OpenAI.

### Key Conventions

| Convention | Detail |
|---|---|
| Async everywhere | All handlers, services, and DB calls are `async def`. Never use sync SQLAlchemy calls. |
| Session management | Always use `get_session()` context manager from `db/session.py`. Never create sessions manually in services. |
| Model column naming | Never name a column `metadata` — conflicts with SQLAlchemy internals. Use `metadata_` instead. |
| Enum types | Define Python `Enum` classes first, then reference in SQLAlchemy `Enum(MyEnum)` columns. |
| ChromaDB naming | Collections are always named `{bot_id}__{scope}`. Never create a flat unscoped collection. |
| Router registration order | In `main.py`, always register `command_router` before `message_router`. The `F.text` filter in messages.py would otherwise catch `/start` before the Command filter. |
| Migration workflow | Any model change → `alembic revision --autogenerate -m "description"` → `alembic upgrade head`. Never edit existing migration files. |

### What Is Currently Stubbed / In-Memory

The following are temporary implementations that must be replaced before production:

1. **`chat_service.py` `_histories` dict** — in-memory per-user chat history. Must be replaced with DB-backed message retrieval from `MessageRepository`. History should be loaded from the `messages` table filtered by `(bot_id, user_id)`, ordered by `created_at`, limited to last N turns.

2. **`llm/prompts.py` `build_system_prompt()`** — currently hardcoded persona. Must be replaced with a DB lookup: `BotRepository.get_by_id(bot_id)` → read `persona_config` JSON → format into prompt string.

3. **`chat_service.py` `get_reply()`** — receives `bot_id=None` placeholder. Once multi-persona routing is implemented, `bot_id` must be resolved from middleware context and passed through the full call chain.

### Next Implementation Priorities (in order)

1. `AllowlistMiddleware` — check `message.from_user.id` against `users.is_allowed`; drop silently if not allowed
2. Invite token flow — `/start INV_xxx` parses token, calls `UserRepository.get_by_invite_token()`, sets `is_allowed=True`
3. `BotRepository` and `RelationshipRepository`
4. Replace in-memory `_histories` with DB-backed message log
5. ChromaDB `memory_service.py` — preference extraction on each message, RAG retrieval injected into system prompt
6. Multi-persona `BotRouter` middleware — resolves `bot_id` from webhook path, injects into handler context
7. `media_service.py` — voice → Whisper, image → vision model
8. `scheduler_service.py` — APScheduler proactive messages using `companion_events` table

### Security Reminders

- `bots.telegram_token` should be encrypted at rest in production using `sqlalchemy-utils` `EncryptedType`
- Proactive messages generated by the scheduler must be filtered — never prompt users for sensitive media, financial info, credentials, or identification documents
- `data/` directory is gitignored — never commit database files or ChromaDB data
- In production, `DATABASE_URL` is injected as a runtime environment variable from DigitalOcean secrets, never stored in `.env` files on the server
