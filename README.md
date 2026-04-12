# AI-Powered Real Estate Assistant API and Admin Dashboard

## Project Overview
This project is a standalone local demo for an AI-style real estate assistant. It now includes:
- A FastAPI backend with structured REST APIs
- A server-rendered admin dashboard under `/dashboard`
- Deterministic property query interpretation without an external LLM
- Lead routing with platform contact priority and realtor assignment
- A researched integrations catalog with editable connector settings

The dashboard is intentionally form-driven and human-readable. It uses cards, tables, labels, checkboxes, dropdowns, and masked secret fields only. It does not expose raw JSON in the UI.

## Architecture Summary
Core application areas:
- `app/api/v1/routes`: public and protected REST endpoints
- `app/web/routes`: admin dashboard pages and form handlers
- `app/services`: business logic for search, routing, seeding, settings, integrations, and dashboard queries
- `app/models`: SQLAlchemy ORM models for listings, realtors, leads, global settings, and integrations
- `app/templates`: Jinja templates for the dashboard
- `app/static`: bundled CSS and favicon served by FastAPI
- `seed/`: mock listings, realtors, and researched integration catalog data
- `tests/`: API, dashboard, and security behavior coverage

## Features
### Existing backend capabilities
- Property listing search with structured filters
- Property detail lookup
- Chat-style property search and summary generation
- Realtor assignment by property, city, or default fallback
- Lead persistence in SQLite

### New dashboard capabilities
- Local admin login
- Overview cards for listings, leads, realtors, and integrations
- Structured property, lead, and realtor tables
- Global settings management:
  - fixed platform contact number
  - default realtor
  - chat result limit
  - fallback city
  - dashboard density
  - table page size
  - feature toggles
- Integration catalog grouped by category with clean configuration forms
- Masked handling for stored connector secrets

## Integration Research Surface
The dashboard seeds a researched catalog of real-estate-adjacent integration targets:
- MLS / Listing Standards:
  - RESO Web API
  - RESO Common Format
  - Bridge API / Bridge Single Feed
- Property Intelligence / Public Records:
  - ATTOM Property Data APIs
- CRM and Lead Management:
  - HubSpot CRM
  - Follow Up Boss Open API
- Communications:
  - Twilio Messaging and Voice
- Mapping and Geocoding:
  - Google Geocoding API
- Scheduling and Showings:
  - Calendly API and webhooks
- Transaction Management / E-Sign:
  - DocuSign eSignature and Rooms workflows
- Payments and Deposits:
  - Stripe

These are seeded as researched connector definitions only. No live third-party integration is executed in v1.

## Research Sources
- RESO Data Dictionary: https://www.reso.org/data-dictionary/
- RESO certification / RCF note: https://www.reso.org/reso-certification-process/
- Bridge Single Feed: https://www.bridgeinteractive.com/bridge-single-feed/
- ATTOM API docs: https://api.developer.attomdata.com/docs
- HubSpot contacts overview: https://developers.hubspot.com/docs/methods/contacts/contacts-overview
- Follow Up Boss Open API: https://help.followupboss.com/hc/en-us/articles/7787906777751-Follow-Up-Boss-Open-API
- Google Geocoding overview: https://developers.google.com/maps/documentation/geocoding/overview
- Twilio Messaging API: https://www.twilio.com/docs/messaging/api/message-resource
- Twilio Voice API: https://www.twilio.com/docs/voice/api
- Calendly getting started: https://developer.calendly.com/getting-started/
- Calendly auth guidance: https://developer.calendly.com/when-to-choose-between-personal-access-tokens-and-oauth/
- DocuSign MyRealEstate / Rooms example: https://developers.docusign.com/html/newsletter/202103.html
- Stripe API reference: https://docs.stripe.com/api

## Setup Instructions
### Prerequisites
- Python 3.12 or newer

### Install dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Configure environment
```powershell
copy .env.example .env
```

Important environment values:
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SESSION_SECRET`
- `COOKIE_SECURE=false` for local HTTP usage
- `TRUSTED_HOSTS=127.0.0.1,localhost,testserver,*.vercel.app`

### Run locally
```powershell
python -m uvicorn app.main:app --reload
```

### Open the application
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Dashboard login: `http://127.0.0.1:8000/dashboard/login`

## Vercel Deployment
This repository is structured to deploy to Vercel as a single FastAPI application:
- `index.py` exports the top-level ASGI `app`
- `app/static` keeps dashboard assets inside the Python bundle

Recommended deployment flow:
```powershell
npx vercel
```

Required Vercel environment variables:
- `DATABASE_URL`
- `FIXED_CONTACT_NUMBER`
- `DEFAULT_REALTOR_ID`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `SESSION_SECRET`
- `COOKIE_SECURE=true`
- `TRUSTED_HOSTS=<your-vercel-domain>,*.vercel.app`

Deployment notes:
- Vercel automatically detects FastAPI when `fastapi` is present in `requirements.txt`
- If `DATABASE_URL` is left at the local default on Vercel, the app now automatically rewrites it to `sqlite:////tmp/real_estate.db` so the serverless runtime can boot
- A file-based SQLite database is acceptable for demo use but not for a production multi-instance deployment
- For a shared hosted environment, move the database to Postgres or another managed database before real usage

## Database and Seeding
On startup the app:
1. creates missing SQLite tables
2. seeds mock realtors and properties if missing
3. seeds the researched integrations catalog if missing
4. creates a default app settings row if missing
5. creates connector config rows for each catalog item if missing

No separate seed command is required.

## Example API Calls
### Health
```powershell
curl http://127.0.0.1:8000/health
```

### List properties
```powershell
curl "http://127.0.0.1:8000/api/v1/properties?city=Houston&bedrooms=3&max_price=500000&status=for_sale"
```

### Chat query
```powershell
curl -X POST http://127.0.0.1:8000/api/v1/chat/query `
  -H "Content-Type: application/json" `
  -d "{\"message\":\"Show me 3-bedroom homes in Houston under 500000\",\"user_name\":\"John Doe\",\"user_email\":\"john@example.com\",\"user_phone\":\"+1-555-111-2222\"}"
```

### Protected lead routing
This endpoint now requires an authenticated admin session from the dashboard.

## Dashboard Pages
- `/dashboard/login`
- `/dashboard`
- `/dashboard/properties`
- `/dashboard/properties/{property_id}`
- `/dashboard/leads`
- `/dashboard/leads/{lead_id}`
- `/dashboard/realtors`
- `/dashboard/settings`
- `/dashboard/integrations`
- `/dashboard/integrations/{catalog_id}`

## Testing
### Run the automated suite
```powershell
python -m pytest
```

### Run the browser smoke test
This uses Playwright CLI against a running local server and checks the dashboard login, settings save, property filtering, and integration settings flow.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\playwright_smoke.ps1
```

Optional parameters:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\playwright_smoke.ps1 `
  -BaseUrl http://127.0.0.1:8000 `
  -Username admin `
  -Password changeme-demo-only
```

Current coverage includes:
- health endpoint
- property filtering
- chat query behavior
- admin login and protected dashboard access
- protected API write enforcement
- CSRF protection on dashboard form posts
- settings persistence affecting routing behavior
- integrations catalog rendering
- masked connector secret handling
- HTML escaping for saved notes
- security headers on dashboard responses

## Security Review Summary
Implemented security controls:
- Session-based admin authentication for dashboard pages
- Auth requirement for `POST /api/v1/leads/route`
- CSRF tokens on all dashboard form posts
- Signed session cookies with configurable secure-cookie mode
- Trusted host middleware for local/demo hosts
- Security headers on dashboard and static responses:
  - `X-Frame-Options`
  - `X-Content-Type-Options`
  - `Referrer-Policy`
  - Content Security Policy
- Jinja auto-escaping for HTML responses
- Secret masking in the dashboard after connector settings are saved

Known demo limitations:
- Admin credentials are environment-based and intended only for local demo use
- Stored connector secrets are masked in the UI but not encrypted at rest
- Swagger remains available for demo convenience
- No rate limiting, audit log, MFA, or production-grade secret management is included

## Assumptions
- This remains a local demo, not a production SaaS deployment
- Live third-party integrations are intentionally out of scope
- Dashboard interaction is server-rendered and form-driven by design
- Public read APIs remain available for demo use
- State-changing admin behavior is protected by the dashboard session

## Future Improvements
- Add a richer broker or operations UI with charts, saved filters, and advanced pagination
- Add live connector testing and health probes per integration
- Integrate with a real frontend application or broker portal
- Connect to Doorviser internal systems through adapter services
- Replace deterministic parsing with a real LLM plus retrieval and guardrails
- Push leads into a CRM such as HubSpot or Follow Up Boss
- Add SMS and phone workflows through Twilio
- Add production authentication, role-based access control, multi-tenancy, audit logs, and encrypted secret storage
