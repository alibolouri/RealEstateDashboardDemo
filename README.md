# Doorviser Real-Estate Agent

A standalone real-estate AI assistant for Doorviser, built as a 1-day trial MVP.

## What it does
- conversational property search
- property detail retrieval from realistic seeded listings
- grounded buyer, renter, seller, and area guidance
- Doorviser-first human handoff
- realtor recommendation by property, city, then fallback
- ChatGPT-like console with streaming responses and resumable conversations

## Architecture
- `backend/app/main.py`: FastAPI API and SSE streaming endpoints
- `backend/app/agent.py`: Doorviser conversation agent with LangGraph-ready orchestration and deterministic fallback
- `backend/app/tools.py`: real-estate search, knowledge, contact, and routing tools
- `backend/app/database.py`: SQLite-backed conversation and handoff memory
- `backend/app/data/*.json`: properties, realtors, and Doorviser knowledge
- `frontend/src/components/Dashboard.tsx`: standalone chat console

## API
- `GET /health`
- `GET /conversations`
- `POST /conversations`
- `POST /conversations/{conversation_id}/messages`
- `POST /conversations/{conversation_id}/messages/stream`
- `GET /conversations/{conversation_id}/history`
- `POST /handoff`

## Local setup

### Backend
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
uvicorn backend.app.main:app --reload
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
```

Backend runs on `http://localhost:8000`. Frontend runs on `http://localhost:5173`.

## Data and behavior
- 20 seeded listings across Houston, Austin, Dallas, San Antonio, Miami, and Miami Beach
- 8 seeded realtors with coverage and specialties
- curated Doorviser knowledge documents for buyers, renters, sellers, short stays, and handoff behavior
- if `OPENAI_API_KEY` is missing, the app uses a deterministic agent fallback so the trial still works offline

## Example prompts
- `Find 3-bedroom homes in Houston under $500000`
- `What should I know before renting in Austin?`
- `Show me short stays in Miami Beach`
- `Tell me about prop-017`
- `Connect me to a realtor for Austin condos`

## Test
```powershell
python -m pytest
```

## Notes
- This trial is intentionally scoped to search + handoff.
- The frontend is standalone for the trial, but the backend and UI shape are suitable for later embedding into `doorviser.com`.
- The old dashboard/admin work was intentionally removed from the product path and replaced with a focused conversational assistant architecture.
