# 🔍 Prior Approval AI — Warranty Claim Validation with LangGraph RAG

An AI-assisted warranty claim validation system that uses a multi-agent RAG architecture to validate whether requested parts are logically justified by the technician's narrative. Built for XYZ Company's Prior Approval (Pre-Repair) process.

## Features

- 🔍 AI-powered claim narrative parsing (entity extraction)
- 📚 RAG retrieval from historical claims, part mappings, and repair references (ChromaDB)
- ✅ Per-part relevance scoring (0.0–1.0) with evidence-based reasoning
- 🏷️ Automatic decision categorization (AUTO_APPROVE / REVIEW / FLAG)
- 🧠 Multi-agent orchestration with LangGraph (5 sequential agents)
- 🌐 FastAPI backend with a web interface
- 💾 Conversation state persistence using PostgreSQL
- 📄 Copy and PDF download of validation reports

## Tech Stack

- Python 3.10+
- FastAPI + Uvicorn
- Jinja2 + HTML/CSS/JavaScript frontend
- LangGraph + LangChain
- Groq LLMs (GPT-OSS 120B)
- PostgreSQL (state persistence via LangGraph CheckPointer)
- ChromaDB (in-memory vector store for RAG)

## Project Structure

```
.
├── app.py                # FastAPI server (endpoints + frontend serving)
├── backend.py            # LangGraph multi-agent workflow (5 agents)
├── models.py             # Data models (ParsedClaim, PartResult, ClaimDecision)
├── decision.py           # Decision categorization logic (thresholds)
├── knowledge_base.py     # ChromaDB vector store + seed data
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── static/
│   ├── style.css         # Dark-themed UI styles
│   └── script.js         # Frontend logic (form, results, PDF)
├── templates/
│   └── index.html        # Claim submission form + results display
├── tools/                # Reserved for future tool integrations
└── tests/
    ├── conftest.py       # Shared Hypothesis strategies
    ├── test_models.py    # Property tests: serialization round trips, score invariants
    ├── test_decision_logic.py  # Property tests: categorization correctness
    ├── test_api.py       # Property tests: input validation
    ├── test_agents.py    # Property tests: part evaluation completeness
    ├── test_knowledge_base.py  # Property tests: retrieval bounds
    └── test_api_response.py    # Property tests: response completeness, state round trip
```

## How the Workflow Works

1. Technician submits a claim (narrative + parts list) via web UI
2. **Claim Parser Agent** — extracts structured entities (vehicle system, symptom, diagnosis, repair action) from the narrative using LLM
3. **RAG Retrieval** — queries ChromaDB for similar historical claims, part-system mappings, and repair references
4. **Parts Validator Agent** — scores each requested part (0.0–1.0) against the diagnosis and retrieved evidence
5. **Reasoning Agent** — generates a human-readable explanation referencing specific evidence
6. **Aggregation Agent** — assigns a decision category:
   - **AUTO_APPROVE**: all parts scored > 0.8
   - **FLAG**: any part scored < 0.3
   - **REVIEW**: everything else

## Prerequisites

- Python 3.10+ (or `uvx` as a runner)
- PostgreSQL database (Render, local, or any provider)
- Groq API key ([console.groq.com](https://console.groq.com))

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
GROQ_API_KEY=your_groq_api_key_here
```

## Running Locally

### With Python installed

```bash
pip install -r requirements.txt
python app.py
```

### With uvx (no Python install required)

```bash
uvx --with fastapi --with uvicorn --with jinja2 --with langchain-groq --with langgraph --with langchain --with chromadb --with "psycopg[binary]" --with python-dotenv --with langgraph-checkpoint-postgres --with certifi --with pydantic --with langchain-community python app.py
```

Then open: http://127.0.0.1:8000/

## Running Tests

```bash
# All tests (32 tests across 6 files)
uvx --with hypothesis --with chromadb pytest tests/ -v

# Just pure-logic tests (no ChromaDB dependency, faster)
uvx --with hypothesis pytest tests/test_models.py tests/test_decision_logic.py tests/test_api.py tests/test_agents.py tests/test_api_response.py -v
```

## Deploying on Render

1. Push to a GitHub repository (`.env` is gitignored)
2. Create a **PostgreSQL** database on Render
3. Create a **Web Service** on Render:
   - **Root directory**: `rag-project-1`
   - **Build command**: `pip install -r requirements.txt`
   - **Start command**: `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. Add environment variables in the Render dashboard:
   - `DATABASE_URL` — use the **internal** PostgreSQL URL (both services on Render's network)
   - `GROQ_API_KEY` — your Groq API key

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Web interface |
| `POST` | `/api/validate` | Submit a claim for validation |
| `GET` | `/health` | Health check |

### Example API Request

```bash
curl -X POST http://127.0.0.1:8000/api/validate \
  -H "Content-Type: application/json" \
  -d '{
    "narrative": "Customer states vehicle has oil leak from rear end. Found oil leak at pinion seal on rear differential. Recommend replacing pinion seal.",
    "parts": ["Pinion seal", "Differential oil", "Spark plug set"]
  }'
```

## Sample Claims for Testing

The web UI includes quick-prompt buttons:

- **Valid Claim**: Rear differential oil leak → pinion seal, differential oil, crush sleeve (all justified)
- **Suspicious Parts**: Rear differential oil leak → includes spark plugs and alarm kit (unjustified parts flagged)
- **Mixed Claim**: Engine overheating → thermostat + brake pads (one unrelated part)
