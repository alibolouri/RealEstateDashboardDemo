# White-Label MLS-Powered Real-Estate Agent

A standalone real-estate AI concierge built as a 1-day trial MVP. It is white-label by design, uses a ChatGPT-style console, and is structured around official-feed-ready source connectors rather than treating local JSON as the long-term data architecture.

## What it does
- conversational listing search
- listing detail retrieval from a normalized listing schema
- grounded buying, renting, selling, and area guidance
- brokerage-first human handoff
- realtor recommendation by listing, city, then fallback
- streaming chat responses with resumable conversations

## Current architecture
- `backend/app/main.py`: FastAPI API and SSE streaming endpoints
- `backend/app/agent.py`: source-aware conversation agent with LangGraph-ready orchestration and deterministic fallback
- `backend/app/connectors.py`: listing, knowledge, and routing source interfaces plus demo JSON connectors
- `backend/app/tools.py`: query interpretation and connector-backed tool wrappers
- `backend/app/database.py`: SQLite-backed conversation and handoff memory
- `backend/app/data/*.json`: demo listing, realtor, and guidance content for the connector-ready trial
- `frontend/src/components/Dashboard.tsx`: standalone chat console

## Source model
The app is designed around three source classes:

- **Listing sources**
  - intended target: MLS / RESO / IDX / broker-approved feeds
  - current implementation: `demo_json` connector
- **Knowledge sources**
  - curated guidance content for buying, renting, selling, neighborhoods, and process questions
- **Routing sources**
  - brokerage contact number
  - realtor roster
  - service-area routing rules

Every listing-backed response includes source provenance and data status:
- `live`
- `cached`
- `demo`

## API
- `GET /`
- `GET /health`
- `GET /conversations`
- `POST /conversations`
- `POST /conversations/{conversation_id}/messages`
- `POST /conversations/{conversation_id}/messages/stream`
- `GET /conversations/{conversation_id}/history`
- `POST /handoff`

## Environment
Copy `.env.example` to `.env` and adjust as needed.

Core settings:
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `DATABASE_URL`
- `BROKERAGE_NAME`
- `BROKERAGE_CONTACT_NUMBER`
- `ASSISTANT_BRAND_NAME`
- `LISTING_SOURCE_MODE`

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

## Example prompts
- `Find 3-bedroom homes in Houston under $500000`
- `What should I know before renting in Austin?`
- `Show me short stays in Miami Beach`
- `Tell me about prop-017`
- `Connect me to a realtor for Austin condos`

## Trial defaults
- the active listing source is `demo_json`
- demo listings model an MLS-like normalized feed
- the app remains fully usable without an OpenAI key through deterministic fallback behavior
- with `OPENAI_API_KEY`, the LangGraph/OpenAI path becomes active

## MLS integration path
This codebase is intentionally staged:

### Phase 1
- keep the demo JSON connector for local development
- standardize agent, API, and UI on normalized listing source contracts

### Phase 2
- add an official MLS / RESO / IDX / broker-approved feed connector
- introduce sync and caching while preserving the same chat and API contract

### Phase 3
- support multiple approved feeds
- add licensed market data and neighborhood guidance sources
- merge/rank results by source freshness and quality

## Test
```powershell
python -m pytest -q
```

## Notes
- This trial is intentionally scoped to search + guidance + handoff.
- The app is white-label and can be skinned later to resemble a client presentation site.
- Scraping is not the core architecture. The connector layer is designed so official feeds can replace the demo source cleanly.
