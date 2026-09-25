# ⚡ TrueTerms MCP

> AI-powered financial contract assistant built on the ACTUS standard — featuring agentic RAG, voice input, XBRL parsing, and MCP server integration.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-agentic_RAG-orange)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-purple?logo=anthropic)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector_store-green)

---

## 🌟 What is TrueTerms?

TrueTerms is an intelligent assistant that helps users understand, generate, and simulate [ACTUS](https://www.actusfrf.org/) financial contracts using natural language. It combines:

- 🤖 **Agentic RAG pipeline** (LangGraph + ChromaDB + Claude)
- 🎙️ **Voice input** with Whisper transcription
- 📄 **XBRL parsing** for IFRS / US-GAAP financial reports
- ⚡ **Live ACTUS server** contract simulation
- 🔌 **MCP server** for Claude Desktop integration
- 🌍 **Multilingual** support (English, Tamil, Hindi, French, German + more)


  🚀 How to Use TrueTerms
🌐 Host Link : http://52.73.253.140/

Step 1 — Open the link in your browser

Go to http://52.73.253.140/

Step 2 — Find the chat input box at the bottom of the screen
Step 3 — Type your question and press Enter
Step 4 — The AI searches the ACTUS standards knowledge base and gives you an instant answer
Step 5 — Try these example queries to explore:
Query 1: 
Generate a ACTUS PAM contract for a loan of USD 10000 for 5 years
for an interest rate of 5 % and a US Treasury rates as a risk factor rate of 1 percent every year

Query 2 :
I want to model a floating rate mortgage where the principal reduces every month and the interest resets every 6 months using LIBOR + 200bps. Which ACTUS contract type should I use? Generate the full JSON.

---

## 🏗️ Project Structure

```
trueterms/
├── .env                          ← API keys (never committed)
├── .gitignore
│
├── backend/
│   ├── api_server.py             ← FastAPI server (port 8000)
│   ├── mcp_server.py             ← MCP server entry point
│   ├── config.py                 ← Paths, model settings
│   ├── anthropic_client.py       ← Claude API client
│   ├── query.py                  ← CLI query tool
│   ├── run_ingestion.py          ← Load docs into ChromaDB
│   ├── requirements.txt
│   │
│   ├── agents/                   ← 7 agentic pipeline agents
│   │   ├── router_agent.py
│   │   ├── retriever_agent.py
│   │   ├── generator_agent.py
│   │   ├── grader_agent.py
│   │   ├── hallucination_agent.py
│   │   ├── rewriter_agent.py
│   │   └── web_search_agent.py
│   │
│   ├── graph/                    ← LangGraph pipeline
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── edges.py
│   │   └── state.py
│   │
│   ├── src/
│   │   ├── mcpcore/tools.py      ← MCP tool definitions
│   │   └── mcpserver/server.py   ← MCP server core
│   │
│   ├── ingestion/                ← Document ingestion pipeline
│   ├── db/                       ← ChromaDB vector store
│   ├── models/                   ← Data models
│   ├── prompts/                  ← LLM prompt templates
│   └── data_collections/         ← ACTUS standards & example contracts
│
└── frontend/                     ← React + Vite UI (port 5173)
    ├── index.html
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── components/           ← Chat, Voice, ACTUS Runner, etc.
        ├── pages/                ← 13 pages
        ├── hooks/                ← Custom React hooks
        ├── services/api.js       ← Backend API calls
        ├── i18n/                 ← 12 language translations
        └── styles/
```

---

## ✅ Prerequisites

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | https://python.org/downloads |
| Node.js | 18+ | https://nodejs.org |
| Git | any | https://git-scm.com |
| FFmpeg | any | https://ffmpeg.org (required for voice) |

---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/mramaran/trueterms.git
cd trueterms
```

### 2. Setup `.env`

Create a `.env` file in the root folder:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_MODEL=claude-sonnet-4-6
```

> Get your API key from: https://console.anthropic.com

### 3. Create Python virtual environment

```bash
# Windows
cd backend
python -m venv env
env\Scripts\activate

# Mac/Linux
cd backend
python -m venv env
source env/bin/activate
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Run ingestion (one-time)

```bash
# From the project root folder:
cd ..
C:\...\backend\env\Scripts\python.exe -m python backend/run_ingestion.py
```

> This creates `chroma_db/` automatically. Re-run only when you add new data files.

### 6. Start the backend

```bash
# From the project root folder:
C:\path\to\backend\env\Scripts\python.exe -m uvicorn backend.api_server:app --port 8000 --reload
```

Backend runs at: **http://localhost:8000**


### 7. Start the frontend

```bash
cd frontend
npm install      # first time only
npm run dev
```

Frontend runs at: **http://localhost:5173**

---

## 🔌 MCP Server (Claude Desktop)

To use TrueTerms as an MCP tool inside Claude Desktop, add this to your `claude_desktop_config.json`:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "trueterms": {
      "command": "python",
      "args": ["PATH_TO_PROJECT\\backend\\mcp_server.py"],
      "env": {
        "ANTHROPIC_API_KEY": "your-key-here",
        "LLM_MODEL": "claude-sonnet-4-6"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `query-trueterms` | Ask any ACTUS question — agentic RAG pipeline |
| `generate-actus-contract` | Generate PAM / ANN / LAM / ... contract JSON |
| `search-actus-standards` | Direct ChromaDB lookup of ACTUS dictionary |
| `run-actus-ingestion` | Reload all documents into ChromaDB |
| `get-actus-contract-types` | List all 17 supported ACTUS contract types |

---

## 🧠 Agentic RAG Pipeline

```
User Query
    │
    ▼
Router Agent ──────────────────────────────────┐
    │                                           │
    ▼ (vectorstore)                             ▼ (web_search)
Retriever Agent                           Web Search Agent
    │                                           │
    ▼                                           │
Grader Agent (relevance check)                 │
    │                                           │
    ├─ irrelevant → Rewriter Agent → retry      │
    │                                           │
    ▼                                           ▼
Generator Agent ◄──────────────────────────────┘
    │
    ▼
Hallucination Agent (grounded check)
    │
    ▼
Answer Grader
    │
    ▼
Final Answer
```

---

## 🌍 Supported Languages

English · Tamil · Tanglish · Hindi · French · German · Spanish · Portuguese · Japanese · Korean · Italian · Indonesian

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/chat` | Main RAG query |
| POST | `/transcribe` | Voice → text (Whisper) |
| POST | `/generate-contract` | Generate ACTUS contract |
| POST | `/run-contract` | Run contract on ACTUS server |
| POST | `/parse-xbrl` | Parse XBRL financial report |
| POST | `/generate-xbrl-report` | Generate XBRL compliance report |
| POST | `/share` | Share a conversation |
| GET | `/docs` | Swagger UI |

---

## ❗ Troubleshooting

| Error | Fix |
|-------|-----|
| `No module named 'backend'` | Run from the project root, not `backend/` |
| `ChromaDB empty` | Run `python run_ingestion.py` |
| `ANTHROPIC_API_KEY not found` | Check `.env` file in root folder |
| `Transcription failed: WinError 2` | Install FFmpeg: `winget install Gyan.FFmpeg` |
| `Fatal error in launcher` | Use full path to `env\Scripts\python.exe` |
| `npm not found` | Install Node.js from https://nodejs.org |

---

## 🏛️ ACTUS Contract Types 

PAM · ANN · LAM · NAM · CLM · STK · COM · CSH · CEG · CEC · SWAPS · SWPPV · FXOUT · OPTNS · FUTUR · UMP · CSH

---


---

<div align="center">
Built with ❤️ using Claude · LangGraph · ChromaDB · FastAPI · React
</div>
