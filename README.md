# AI Planning Assistant

A self-evolving, AI-powered planning and scheduling assistant with Google Calendar integration.

## Features

- **AI Chatbot**: Natural language interface powered by GPT-4o
- **Google Calendar Integration**: Read from multiple calendars, schedule to Project Manager
- **Full Memory**: Remembers conversations, learns your preferences
- **Self-Modifying**: AI can update its own instructions, knowledge, and calendar config
- **Web Interface**: Modern React-based chat UI with settings page

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Node.js 18+
- Google Calendar API credentials (`credentials.json`)
- OpenAI API key

### 2. Setup

```bash
cd "/Users/hunterdonia/Documents/untitled folder/planner_app"

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### 3. Configure

Create a `.env` file (or copy from `.env.example`):

```
OPENAI_API_KEY=sk-...your-key-here...
```

Make sure you have `credentials.json` from Google Cloud Console.

### 4. Run

```bash
./run.sh
```

Or start manually:

```bash
# Terminal 1 - Backend
source .venv/bin/activate
uvicorn backend.main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### 5. Open

- **App**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

## First Time Setup

1. Open the app and click "Auto-detect calendars" in Settings
2. Add your calendars (work, personal, mastermind, etc.)
3. Mark "Project Manager" calendar as read/write for scheduling
4. Start chatting!

## What You Can Say

- "What's on my calendar today?"
- "Schedule a meeting with Sarah tomorrow at 2pm"
- "Find time for a 1-hour focus session this week"
- "Remember that Modern Stylist Movement is my hair education business"
- "Never schedule anything before 10am"
- "Add my new calendar called 'Client Sessions'"

## Architecture

```
planner_app/
├── backend/              # FastAPI Python backend
│   ├── api/              # REST + WebSocket endpoints
│   ├── services/         # Business logic
│   ├── models/           # SQLAlchemy + Pydantic
│   └── ai/               # OpenAI integration
├── frontend/             # React + Vite frontend
│   └── src/
│       ├── pages/        # Chat and Settings pages
│       ├── components/   # UI components
│       └── hooks/        # WebSocket + API hooks
├── data/                 # SQLite database
├── credentials.json      # Google OAuth credentials
├── token.json            # Google auth token (auto-generated)
└── .env                  # Environment variables
```

## Scalable & Self-Evolving

The AI can modify its own:

- **Calendars**: Add/remove calendars via conversation or settings
- **Knowledge**: Learns facts about you, your business, your preferences
- **Instructions**: Changes its behavior based on your feedback
- **Scheduling Rules**: Learns your time preferences

All configuration is stored in SQLite, not hardcoded.

## Troubleshooting

- **"Missing credentials.json"**: Download OAuth credentials from Google Cloud Console
- **"OPENAI_API_KEY not set"**: Add your key to `.env`
- **Calendar not showing**: Check Settings → Calendars and add your calendars
- **WebSocket disconnected**: Refresh the page or check if backend is running
