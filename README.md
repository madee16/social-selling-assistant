# Social Selling Assistant

An AI-powered omnichannel social commerce platform built for merchants selling via **WhatsApp**, **Facebook Messenger**, and an **embeddable web chat widget** — with native support for **Tunisian Darija**, **French**, and **English**, Cash-on-Delivery (COD / TND) workflows, automated SEO share pages, and PDF invoice generation.

---

## Key Features

- **Omnichannel Conversational AI & Embeddable Widget**
  - Meta **WhatsApp Cloud API** and **Messenger** webhooks (`GET/POST /api/webhooks/whatsapp`, `/api/webhooks/messenger`) with `X-Hub-Signature-256` HMAC verification.
  - Lightweight storefront chat widget (`GET /widget.js`) embeddable on any website or product share page.
- **AI Orchestration & Native Tool Calling**
  - Structured function calling (`TOOLS_SCHEMA`: `check_inventory`, `create_order`, `request_merchant_approval`) with full session, message, and tool-call audit logging (`AISession`, `AIMessage`, `AIToolCall`).
  - **n8n Workflow Integration** (`n8n/darija-workflow.json`) protected by a fast circuit breaker (`1.5s` connect timeout, opens after `2` consecutive failures for `30s` cooldown) with direct LLM fallback via **NVIDIA NIM** (`nvidia/nemotron-3-super-120b-a12b`) or **Google Gemini**.
- **Catalog, Inventory & Order Management**
  - Multi-store catalog (`Store`, `Product`, `ProductVariant`, `Category`, `Collection`), buyers CRM, and bulk Excel/CSV catalog imports (`openpyxl`, `pandas`).
  - Automatic COD order creation and **ReportLab PDF generation** (*Bon de Livraison / Facture*) at `GET /api/orders/{order_id}/invoice.pdf`.
- **Governance & Rules Engine**
  - Event-driven `RulesEngine` automations, merchant approval workflows for buyer discounts/negotiations (`/governance`), product scoring, and seller trust scoring.
- **Auto-SEO & SSR Share Pages**
  - AI-generated SEO metadata and rubric scoring (`POST /api/seo/{entity_type}/{entity_id}/generate`).
  - Public dynamic sitemap (`GET /sitemap.xml`) and server-rendered OpenGraph product/store share pages (`GET /share/{entity_type}/{slug_or_id}`) with embedded AI chat ordering.
- **Merchant Dashboard**
  - React + TypeScript + Tailwind CSS dashboard featuring analytics (`recharts`), live conversation monitoring, store/widget configuration, and **English / French** localization (`i18next`).
- **Security**
  - JWT authentication with RBAC, Fernet encryption for stored integration tokens (`token_encryption_key`), request logging middleware, and `slowapi` rate limiting.

---

## Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend** | Python, FastAPI (`0.115.6`), SQLAlchemy Async (`2.0.36`), PostgreSQL (`asyncpg`), Alembic, Pydantic Settings, ReportLab, SlowAPI |
| **Frontend** | React (`19`), TypeScript, Vite (`8`), Tailwind CSS (`4`), React Router (`7`), Recharts, i18next, Axios |
| **AI & Automation** | NVIDIA NIM, Google Gemini (`google-generativeai`), n8n Webhook Workflow |
| **Infrastructure** | Docker & Docker Compose, Nginx (frontend production container) |

---

## Project Structure

```text
.
├── backend/                 # FastAPI app, SQLAlchemy models, routers, services, Alembic & pytest suite
│   ├── alembic/             # Database migrations
│   ├── app/
│   │   ├── models/          # ORM models (orders, products, AI sessions, approvals, SEO, etc.)
│   │   ├── prompts/         # Multilingual system prompts
│   │   ├── routers/         # REST, webhook, widget, and public SSR endpoints
│   │   ├── schemas/         # Pydantic v2 schemas
│   │   └── services/        # Orchestrator, RulesEngine, AI/n8n circuit breaker, PDF generator
│   ├── scripts/             # Utility & seeding scripts
│   └── tests/               # Async pytest test suite
├── frontend/                # React + Vite merchant dashboard & public widget.js
├── n8n/                     # Darija/FR/EN conversational agent n8n workflow export
├── docker-compose.yml       # Backend (port 8001) + Frontend (port 80) containers
└── start.ps1                # Windows PowerShell quick-start script
```

---

## Quick Start

### 1. Configure Environment Variables

Copy the example environment files and fill in your credentials:

- `backend/.env.example` → `backend/.env`
- `frontend/.env.example` → `frontend/.env`

Key backend variables (defined in `backend/app/config.py`):

| Variable | Description |
| :--- | :--- |
| `SUPABASE_DB_URL` | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `SECRET_KEY` | Random secret key for JWT signing |
| `FRONTEND_URL` | Allowed CORS frontend origin (default: `http://localhost:5173`) |
| `NVIDIA_API_KEY` / `GEMINI_API_KEY` | LLM provider API key(s) |
| `N8N_WEBHOOK_URL` / `N8N_API_KEY` | Optional n8n conversational agent endpoint |
| `WHATSAPP_ENABLED` | Master toggle (`false` by default) |
| `WHATSAPP_VERIFY_TOKEN` / `MESSENGER_VERIFY_TOKEN` | Custom Meta webhook verification tokens |
| `WHATSAPP_APP_SECRET` | Meta App Secret for `X-Hub-Signature-256` HMAC validation |
| `TOKEN_ENCRYPTION_KEY` | Secret used for encrypting integration tokens at rest |

### 2. Run Locally (Windows Quick Start)

```powershell
# First run (creates backend venv, installs backend & frontend deps, starts both servers)
.\start.ps1 -Install

# Subsequent runs
.\start.ps1
```

- **Backend API & Swagger Docs:** `http://localhost:8001` (`/docs`, `/health`)
- **Frontend Dashboard:** `http://localhost:5173`

<details>
<summary>Manual Setup (Linux / macOS / Windows)</summary>

**Backend:**
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate | Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

</details>

### 3. Run with Docker

```bash
docker compose up --build
```

- Backend runs on port `8001`
- Frontend runs on port `80`

---

## Running Tests

The backend test suite targets a PostgreSQL `social_test` database (`TEST_DB_HOST`, defaulting to `localhost`):

```bash
cd backend
pytest
```
