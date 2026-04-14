# White-Label MLS-Powered Real-Estate Agent

A standalone real-estate AI concierge built as a trial MVP. It is white-label by design, uses a premium agent-workspace UI, and is structured around official-feed-ready source connectors rather than treating local JSON as the long-term data architecture.

## What it does
- conversational listing search
- listing detail retrieval from a normalized listing schema
- grounded buying, renting, selling, and area guidance
- brokerage-first human handoff
- realtor recommendation by listing, city, then fallback
- streaming chat responses with resumable conversations
- seeded multi-turn demo threads with citations and clickable external references

## Current architecture
- `backend/app/main.py`: FastAPI API and SSE streaming endpoints
- `backend/app/agent.py`: source-aware conversation agent with LangGraph-ready orchestration and deterministic fallback
- `backend/app/connectors.py`: listing, knowledge, and routing source interfaces plus demo JSON connectors
- `backend/app/tools.py`: query interpretation and connector-backed tool wrappers
- `backend/app/database.py`: SQLite-backed conversation and handoff memory
- `backend/app/data/*.json`: demo listing, realtor, guidance, and seeded demo-conversation content for the connector-ready trial
- `frontend/src/components/Dashboard.tsx`: standalone chat console

## Demo conversations included
When `SEED_DEMO_CONVERSATIONS=1`, a fresh database is populated with four realistic sample threads so the product does not open as an empty shell.

Included demo threads:
- Houston buyer shortlist and school trade-offs
- Austin renter screening and shortlist
- Dallas payment planning and next steps
- Seller prep and brokerage handoff

Each seeded thread includes:
- multi-step narrowing questions from the assistant
- explicit confirmations and choices from the user
- complete final recommendations instead of placeholder one-liners
- listing context and handoff cards where appropriate
- cited sources with live external links for credibility

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

The runtime now supports:
- primary and fallback listing providers
- primary and fallback knowledge providers
- primary and fallback routing providers
- remote JSON-style APIs for listings, knowledge, and routing
- local markdown guidance directories
- connector readiness reporting through `/health`

Every listing-backed response includes source provenance and data status:
- `live`
- `cached`
- `demo`

## Runtime settings
- public chat remains open
- runtime configuration is managed through `/settings`
- settings are stored in the app database with `.env` acting as boot defaults
- secret values are masked after save and applied on the next request

Admin session env vars:
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SESSION_SECRET`
- `SEED_DEMO_CONVERSATIONS`

Platform-ready runtime fields:
- `LISTING_SOURCE_MODE`
- `LISTING_FALLBACK_MODES`
- `LISTING_SEARCH_PATH`
- `LISTING_DETAIL_PATH`
- `KNOWLEDGE_SOURCE_MODE`
- `KNOWLEDGE_FALLBACK_MODES`
- `KNOWLEDGE_LOCAL_PATH`
- `KNOWLEDGE_REMOTE_URL`
- `ROUTING_SOURCE_MODE`
- `ROUTING_FALLBACK_MODES`
- `EXTERNAL_ROSTER_URL`

## API
- `GET /`
- `GET /health`
- `GET /settings`
- `GET /settings/schema`
- `PUT /settings`
- `POST /admin/login`
- `POST /admin/logout`
- `GET /admin/session`
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
- `SEED_DEMO_CONVERSATIONS`
- `LISTING_SOURCE_MODE`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SESSION_SECRET`

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
- `Build me a Houston family-home shortlist under $600k and ask the right follow-up questions first.`
- `Help me compare Austin rentals for a hybrid commute, pet policy, parking, and total move-in cost.`
- `Walk me through Dallas monthly-payment trade-offs around a $400k purchase before recommending listings.`
- `Give me a seller-ready prep checklist for Houston, then route me to the right agent.`
- `Tell me about prop-017 and explain the next best action.`

## Trial defaults
- the active listing source is `demo_json`
- demo listings model an MLS-like normalized feed
- a fresh runtime includes seeded sample threads unless `SEED_DEMO_CONVERSATIONS=0`
- the app remains fully usable without an OpenAI key through deterministic fallback behavior
- with `OPENAI_API_KEY`, the LangGraph/OpenAI path becomes active
- if a configured live source is unavailable, the app falls back through the configured provider chain and can end on sample listings instead of failing hard

## MLS integration path
This codebase is intentionally staged:

### Phase 1
- keep the demo JSON connector for local development
- standardize agent, API, and UI on normalized listing source contracts

### Phase 2
- add an official MLS / RESO / IDX / broker-approved feed connector
- introduce sync and caching while preserving the same chat and API contract
- point `MLS_API_BASE_URL`, `BROKER_FEED_API_BASE_URL`, or related runtime settings at a real provider without changing the UI or the agent contract

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
