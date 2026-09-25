# TrueTerms RAG — Setup Guide

---

## 📁 Folder Structure

```
trueterms/
├── .env
├── config.py
├── anthropic_client.py
├── gemini_client.py
├── query.py
├── run_ingestion.py
├── api_server.py
├── requirements.txt
├── start_frontend.bat
├── start_terminal.bat
├── start_uvicorn.bat
│
├── agents/
│   ├── router_agent.py
│   ├── retriever_agent.py
│   ├── generator_agent.py
│   ├── grader_agent.py
│   ├── hallucination_agent.py
│   ├── rewriter_agent.py
│   └── web_search_agent.py
│
├── graph/
│   ├── graph.py
│   ├── nodes.py
│   ├── edges.py
│   └── state.py
│
├── prompts/
│   ├── generator_prompts.py
│   ├── grader_prompts.py
│   ├── hallucination_prompts.py
│   ├── rewriter_prompts.py
│   └── router_prompts.py
│
├── db/
│   └── vector_store.py
│
├── ingestion/
│   ├── document_loader.py
│   ├── document_chunker.py
│   ├── embedder.py
│   └── indexer.py
│
├── data_collections/
│   ├── data_collection_1(standards)/
│   │   ├── actus-dictionary-taxonomy.json
│   │   ├── actus-dictionary-terms.json
│   │   └── actus-dictionary-applicability.json
│   ├── data_collection_2(example_contracts)/
│   │   ├── l3PAMwRF.txt
│   │   ├── l3PAMnoRF.txt
│   │   ├── l3ANNwRF.txt
│   │   └── l3ANNnoRF.txt
│   └── data_collection_3(about_ACTUS)/
│       ├── actus_about_page.txt
│       └── FINANCE SPEAKS ONE LANGUAGE.md
│
├── frontend/
│   ├── .gitignore
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── src/
│       ├── App.jsx
│       ├── main.jsx
│       ├── components/
│       │   ├── ActusRunner.jsx
│       │   ├── AtMentionMenu.jsx
│       │   ├── ChatInput.jsx
│       │   ├── ChatWindow.jsx
│       │   ├── ConnectorsMarketplace.jsx
│       │   ├── FloatingChat.jsx
│       │   ├── MessageBubble.jsx
│       │   ├── Sidebar.jsx
│       │   ├── ToolsPanel.jsx
│       │   └── VoiceWaveform.jsx
│       ├── hooks/
│       │   ├── useChat.js
│       │   ├── useContractHistory.js
│       │   ├── useMCPConfig.js
│       │   ├── useTheme.js
│       │   └── useVoice.js
│       ├── i18n/
│       │   ├── index.js
│       │   ├── en.json
│       │   ├── de.json
│       │   ├── es.json
│       │   ├── fr.json
│       │   ├── hi.json
│       │   ├── id.json
│       │   ├── it.json
│       │   ├── ja.json
│       │   ├── ko.json
│       │   ├── pt.json
│       │   ├── ta.json
│       │   └── tanglish.json
│       ├── pages/
│       │   ├── ActusReferencePage.jsx
│       │   ├── AgentsPage.jsx
│       │   ├── ArchivePage.jsx
│       │   ├── ChatPage.jsx
│       │   ├── ContractGeneratorPage.jsx
│       │   ├── ContractHistoryPage.jsx
│       │   ├── HelpPage.jsx
│       │   ├── MCPCreatePage.jsx
│       │   ├── MCPServersPage.jsx
│       │   ├── NotFoundPage.jsx
│       │   ├── PipelineStatsPage.jsx
│       │   ├── SettingsPage.jsx
│       │   └── WorkflowPage.jsx
│       ├── services/
│       │   └── api.js
│       └── styles/
│           └── index.css
│
└── chroma_db/                     ← Auto-created after ingestion
    └── chroma.sqlite3
```

---

## ✅ Prerequisites

Install these before starting:

- **Python 3.11+** → https://python.org/downloads
- **Node.js** → https://nodejs.org
- **Git** → https://git-scm.com

---

## 🚀 Step 1 — Clone the Repo

```bash
git clone https://github.com/mramaran/trueterms.git
cd trueterms
```

---

## 🐍 Step 2 — Create Python Virtual Environment

```bash
python -m venv env
```

Activate it:

```bash
# Windows
env\Scripts\activate

# Mac/Linux
source env/bin/activate
```

---

## 🔑 Step 3 — Setup .env File

Create a `.env` file in the root folder and add:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
LLM_MODEL="your model"
```

> Get your API key from: https://console.anthropic.com

---

## 📦 Step 4 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

---

## 🗃️ Step 5 — Run Ingestion (Only Once)

```bash
python run_ingestion.py
```

> This creates the `chroma_db/` folder automatically.
> Run again only if you add new data files.

**Expected Output:**

```
TRUETERMS — INGESTION
  Embedding model: all-MiniLM-L6-v2 (FREE, local)

Loading: data_collection_1(standards)
  [OK] Dictionary: 27 entries from actus-dictionary-taxonomy.json
  [OK] Dictionary: 89 entries from actus-dictionary-terms.json

Loading: data_collection_2(example_contracts)
  [OK] l3PAMwRF.txt loaded

INGESTION COMPLETE
  actus_standards          | Docs: 180
  actus_example_contracts  | Docs: 95
  actus_about              | Docs: 12
  actus_unified            | Docs: 287  ✅
```

---

## 🔍 Step 6 — Test with a Query

```bash
python query.py "what is a PAM contract"
python query.py "generate a PAM contract"
python query.py "ANN with risk factor and UST5Y"
python query.py "what contracts are in ACTUS"
python query.py "generate a PAM contract with semi-annual interest"
```

**Expected Output:**

```
============================================================
  ANSWER
============================================================

[Answer generated strictly from your data source]

──────────────────────────────────────────────────────────
  Pipeline Info:
  Route      : vectorstore
  Docs used  : 4/5
  Grounded   : yes
  Sources (from your data):
    ✅ l3PAMwRF.txt
    ✅ actus-dictionary-taxonomy.json
    ✅ ACTUS PAM Contracts - 20 Examples.postman_collection.json
──────────────────────────────────────────────────────────
```

---

## 🌐 Step 7 — Start the Backend API

```bash
# Option A — Windows batch file
start_uvicorn.bat

# Option B — Manual
uvicorn api_server:app --reload --port 8000
```

---

## 💻 Step 8 — Start the Frontend

```bash
# Option A — Windows batch file
start_frontend.bat

# Option B — Manual
cd frontend
npm install
npm run dev
```


---

## 🔄 Adding New Data Files

```bash
# 1. Add new file into the appropriate folder:
#    data_collections/data_collection_2(example_contracts)/l3LAMwRF.txt

# 2. Delete existing vector database and re-ingest:

# Windows
rmdir /s /q chroma_db
python run_ingestion.py

# Mac/Linux
rm -rf chroma_db
python run_ingestion.py

# 3. Query
python query.py "generate a LAM contract"
```

---

## ❗ Common Errors

| Error | Fix |
|---|---|
| `ANTHROPIC_API_KEY not found` | Check your `.env` file has the correct key |
| `ChromaDB empty` | Run `python run_ingestion.py` |
| `Module not found` | Run `pip install -r requirements.txt` |
| `npm not found` | Install Node.js from https://nodejs.org |
| `uvicorn not found` | Run `pip install uvicorn` |
