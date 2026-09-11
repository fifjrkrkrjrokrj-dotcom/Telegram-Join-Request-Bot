# 🤖 Premium Telegram Join Request Verification Platform

A multi-tenant, SaaS-grade, asynchronous Telegram Join Request Verification Bot built with **Python 3.11+**, **Pyrogram (Pyrofork)**, and **MongoDB (Motor)**.

This platform allows community owners to automate user join request verifications by enforcing mandatory channel/group memberships before approving access.

---

## 🌟 Key Features

- **Multi-Tenant Architecture**: Every bot user acts as a separate owner/tenant managing their own chats, settings, and statistics with complete isolation.
- **Automated Verification Flow**:
  1. User submits Join Request on target Telegram channel/group.
  2. Bot instantly receives `ChatJoinRequest` event and dispatches a personalized verification DM with join buttons.
  3. User joins mandatory channels/groups and taps **VERIFY**.
  4. Bot checks membership in real-time using official Telegram API `get_chat_member` (no scraping).
  5. Upon success:
     - **Auto-Approve ON**: Instantly approves join request via Telegram API.
     - **Auto-Approve OFF**: Marks user as verified and alerts chat administrators.
- **Interactive UI/UX**: Premium Unicode card styling (`╭━━━╮`, `╰━━━╯`), dynamic status badges, and fast inline navigation.
- **Permission Validator**: Verifies administrator rights (`can_invite_users`, etc.) before connecting any chat.
- **Customizable Verification Messages**:
  - Full support for template variables: `{first_name}`, `{last_name}`, `{username}`, `{user_id}`, `{chat_title}`, `{chat_username}`.
  - Optional custom welcome banner photo upload.
- **Required Channels Builder**: Add, edit button labels, customize invite URLs, reorder (Move Up/Down), and delete required chat rules.
- **Rich Analytics & Telemetry**: Real-time counters for total requests, verified users, approved requests, conversion rates, and daily performance metrics.
- **Anti-Spam & Security**:
  - Sliding-window rate limiting on verification attempts and callback buttons.
  - Ownership validation on all administrative actions.
  - Session expiration and TTL tracking in MongoDB.
- **Production-Ready**: Docker, Docker Compose, Railway, Render, and VPS deployment support.

---

## 📁 Project Architecture

```
f:/REQEST SENDER AND ACCEPTER/
├── bot.py                     # Main application entry point & lifecycle
├── config.py                  # Pydantic Settings & environment validation
├── database/
│   ├── mongo.py               # Asynchronous Motor MongoDB connection & indexes
│   ├── users.py               # User and tenant repository
│   ├── chats.py               # Target chats repository & settings
│   ├── required_chats.py      # Mandatory verification chats repository
│   ├── verification.py        # Verification sessions & audit log repository
│   └── statistics.py          # Daily and cumulative analytics repository
├── handlers/
│   ├── start.py               # /start & /help command handlers
│   ├── dashboard.py           # Main tenant dashboard & global analytics
│   ├── add_chat.py            # FSM flow for adding target chats + admin check
│   ├── chat_settings.py       # Per-chat settings (auto-approve, timeout, welcome msg/photo)
│   ├── required_chats.py      # Mandatory chat rule builder (add, edit, reorder, remove)
│   ├── join_requests.py       # Telegram ChatJoinRequest incoming update handler
│   └── verification.py        # DM verification callback & membership verification
├── keyboards/
│   ├── main.py                # Main dashboard inline keyboards
│   ├── chats.py               # Chat list & settings keyboards
│   └── verification.py        # DM verification button markups
├── services/
│   ├── telegram.py            # Telegram API wrappers & permission checks
│   ├── membership.py          # Official API membership checking service
│   ├── approval.py            # Join request approval engine & error handling
│   └── statistics.py          # Formatted metric presenter
├── utils/
│   ├── logger.py              # Structured colored logging
│   ├── rate_limit.py          # Sliding-window rate limiter
│   ├── states.py              # In-memory conversation state manager
│   └── helpers.py             # UI cards, link parsers & variable interpolator
├── Dockerfile                 # Multi-stage production container
├── docker-compose.yml         # Full-stack local & VPS orchestration
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variables template
└── README.md                  # Documentation
```

---

## 🚀 Quick Setup & Local Run

### Prerequisites
- Python 3.11+
- MongoDB 6.0+ running locally or a free [MongoDB Atlas](https://www.mongodb.com/atlas) cluster.
- Telegram `API_ID` & `API_HASH` from [my.telegram.org](https://my.telegram.org).
- Telegram `BOT_TOKEN` from [@BotFather](https://t.me/BotFather).

### 1. Clone & Install Dependencies
```bash
git clone <your-repo-url>
cd "REQEST SENDER AND ACCEPTER"
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Edit `.env`:
```ini
API_ID=12345678
API_HASH=your_telegram_api_hash
BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ_EXAMPLE
MONGO_URI=mongodb://localhost:27017
DATABASE_NAME=telegram_verify_bot
```

### 3. Run the Bot
```bash
python bot.py
```

---

## 🐳 Docker Deployment

### Using Docker Compose
```bash
docker-compose up -d --build
```
To view logs:
```bash
docker-compose logs -f bot
```

---

## ☁️ Cloud Deployment Guides

### Deploy on Railway
1. Fork or push this repository to GitHub.
2. Log into [Railway](https://railway.app/) and click **New Project** ➜ **Deploy from GitHub repo**.
3. Add a **MongoDB** plugin service in Railway.
4. Set the following environment variables in the Bot service settings:
   - `API_ID`
   - `API_HASH`
   - `BOT_TOKEN`
   - `MONGO_URI` (Use `${{MongoDB.MONGO_URL}}` provided by Railway)
   - `DATABASE_NAME` = `telegram_verify_bot`
5. Railway will automatically build using `Dockerfile` and start the bot.

### Deploy on VPS (Systemd Service)
1. Create a service file `/etc/systemd/system/joinverify.service`:
```ini
[Unit]
Description=Telegram Join Request Verification Platform
After=network.target mongodb.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/join_verify_bot
ExecStart=/opt/join_verify_bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
2. Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now joinverify
sudo systemctl status joinverify
```

---

## 🛡️ Security & Multi-Tenancy

- **Callback Security**: Every callback contains explicit resource IDs (`chat_id`, `req_id`) validated against the authenticated caller's `user_id`.
- **Session Authentication**: Verification callbacks check `session["user_id"] == callback_query.from_user.id` to prevent session hijacking.
- **Anti-Flood & Rate Limiting**: Verification clicks have an in-memory sliding cooldown to prevent Telegram API FloodWait.
- **No Member List Scraping**: All checks utilize official individual status endpoints (`get_chat_member`), preserving Telegram API compliance and server memory.

---

## 📄 License
MIT License. Built for production reliability.
