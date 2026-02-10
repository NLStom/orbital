# Orbital

**AI-powered data analysis agent.** Upload your data, ask questions in plain English, and Orbital explores, models, and visualizes — all through conversation.

Built with **Gemini 3 Pro** (via Vertex AI), FastAPI, and Next.js.

---

## Quick Start

### Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **PostgreSQL** running locally
- **uv** (Python package manager) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Google Cloud** credentials with Vertex AI enabled, OR a `GOOGLE_API_KEY`

### 1. Create the database

```bash
createdb orbital
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your credentials:

```env
# Option A: Vertex AI (recommended)
GOOGLE_GENAI_USE_VERTEXAI=true
# Authenticate via: gcloud auth application-default login

# Option B: Google AI Studio API key
GOOGLE_API_KEY=your-key-here
```

### 3. Install dependencies

```bash
# Backend
cd api && uv sync && cd ..

# Frontend
cd web && npm install && cd ..
```

### 4. Start dev servers

```bash
./pm2-dev.sh start
```

- **Frontend:** http://localhost:3737
- **Backend API:** http://localhost:8787

To view logs or stop:

```bash
./pm2-dev.sh logs    # tail logs
./pm2-dev.sh stop    # stop servers
```

---

## Demo Flow (Hackathon Judges)

This walkthrough demonstrates Orbital's core loop: **upload data → ask questions → AI analyzes → discover gaps → add more data → accuracy improves**.

### Setup

1. Start the servers (`./pm2-dev.sh start`)
2. Open http://localhost:3737

### Step-by-step

1. **Create a new session** — click "New Session" on the home page
2. **Upload data** — drag `data/home_values.csv` into the chat panel
3. **Ask a question** — type: *"What drives home values? Build a predictive model."*
4. **Watch the agent work** — Orbital will:
   - Inspect the schema (`get_schema`)
   - Explore column statistics (`get_stats`)
   - Run SQL queries to understand the data
   - Train a regression model (`train_model`)
   - Visualize actual vs predicted values (`create_chart`)
   - Report model performance (~R² 0.65 — mediocre)
5. **Agent identifies gaps** — it will note that errors cluster around certain periods and suggest adding economic indicators
6. **Upload more data** — drag `data/economic.csv` into chat
7. **Ask to retrain** — *"Retrain the model with the economic data included."*
8. **See improvement** — R² jumps to ~0.80+
9. **Upload even more** — drag `data/mortgage_rates.csv` and ask to retrain again
10. **Final result** — R² reaches ~0.85+, demonstrating the iterative discovery loop
11. **Generate a report** — click the **Export → Generate Report** button (or type *"Generate a report summarizing our analysis"*). Orbital creates a shareable report page with charts and narrative.

### What to look for

| Capability | What happens |
|-----------|-------------|
| Natural language SQL | Agent writes and runs SQL from plain English |
| Auto-visualization | Charts appear automatically when they add clarity |
| Predictive modeling | `train_model` builds scikit-learn models, reports metrics |
| Iterative discovery | Agent diagnoses model weaknesses and suggests new data |
| Shareable reports | `create_report` generates a standalone artifact page |
| Session memory | Agent remembers context across the conversation |

---

## Architecture

```
orbital/
├── api/                  # FastAPI backend (port 8787)
│   ├── app/
│   │   ├── agent/        # OrbitalAgent — LLM tool-calling loop
│   │   ├── providers/    # Gemini / Vertex AI provider
│   │   ├── routers/      # REST + WebSocket endpoints
│   │   ├── data/         # PostgreSQL connector, DataLoader
│   │   ├── tools/        # 7 agent tools (see below)
│   │   ├── prompts/      # System prompt
│   │   └── config.py     # Settings (env vars)
│   └── pyproject.toml
├── web/                  # Next.js 15 frontend (port 3737)
│   └── app/
│       ├── _components/  # React components (ChatPanel, VizPanel, etc.)
│       ├── _stores/      # Zustand state management
│       └── _lib/         # API client, types
├── data/                 # Demo CSV files
├── scripts/              # Utility scripts
└── pm2-dev.sh            # Dev server launcher
```

### Agent Tools

| Tool | Purpose |
|------|---------|
| `get_schema` | Inspect table schemas and relationships |
| `get_stats` | Column-level statistics (nulls, distributions, min/max) |
| `run_sql` | Execute read/write SQL against PostgreSQL |
| `create_chart` | Generate chart specs (bar, line, scatter, pie, area) |
| `train_model` | Train scikit-learn regression/classification models |
| `update_memory` | Persist facts and insights across conversation turns |
| `create_report` | Generate shareable multi-section reports |

### Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | Gemini 3 Pro (via Vertex AI / Google GenAI) |
| Backend | FastAPI, uvicorn, psycopg (async PostgreSQL) |
| Frontend | Next.js 15, React 19, Tailwind CSS, Zustand, Recharts |
| ML | scikit-learn (regression, classification) |
| Data | PostgreSQL, pandas, pyarrow |
| Process mgmt | PM2 |

---

## For Coding Agents (Gemini / Cursor)

If you're an AI coding assistant working on this project, here's what you need to know.

### Running the project

```bash
# Install deps
cd api && uv sync && cd ../web && npm install && cd ..

# Create database (one-time)
createdb orbital

# Set env vars (copy .env.example to .env, add Google credentials)

# Start both servers
./pm2-dev.sh start

# Check logs
./pm2-dev.sh logs
```

### Key files to understand

| File | What it does |
|------|-------------|
| `api/app/agent/agent.py` | `OrbitalAgent` — main LLM loop, tool dispatch |
| `api/app/agent/tool_definitions.py` | Tool schemas sent to Gemini |
| `api/app/providers/factory.py` | LLM provider setup (Gemini only) |
| `api/app/routers/sessions.py` | Session CRUD + WebSocket chat endpoint |
| `api/app/data/pg_connector.py` | PostgreSQL query execution, table access control |
| `api/app/prompts/system.md` | System prompt defining agent behavior |
| `web/app/_stores/workspace-store.ts` | Frontend state (Zustand) |
| `web/app/_components/ChatPanel.tsx` | Chat UI with message rendering |
| `web/app/_components/VizPanel.tsx` | Visualization + data tabs |
| `web/app/_lib/api.ts` | Frontend API client + types |

### Common commands

```bash
# Backend — run API server directly
cd api && uv run uvicorn app.main:app --host 0.0.0.0 --port 8787 --reload

# Frontend — run Next.js dev server directly
cd web && npm run dev -- -p 3737

# Frontend — type check
cd web && npx tsc --noEmit

# Frontend — build
cd web && npm run build
```

### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GOOGLE_API_KEY` | Yes* | Google AI Studio API key |
| `GOOGLE_GENAI_USE_VERTEXAI` | No | Set `true` to use Vertex AI instead |
| `DATABASE_URL` | No | PostgreSQL URL (default: `postgresql://localhost/orbital`) |
| `DEFAULT_MODEL` | No | Model name (default: `vertex-gemini-3-pro`) |

*Either `GOOGLE_API_KEY` or Vertex AI credentials (via `gcloud auth`) required.

### Adding a new agent tool

1. Create `api/app/tools/your_tool.py` — implement a class with an `execute()` method
2. Add tool schema to `api/app/agent/tool_definitions.py`
3. Register in `api/app/tools/__init__.py`
4. Add initialization + dispatch branch in `api/app/agent/agent.py`

---

## License

Hackathon submission — not yet licensed for distribution.
