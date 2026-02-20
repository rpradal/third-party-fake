# Sync Demo - Fake Third Party

Demo project to test ERP synchronization with a fake third-party service.

<img width="1161" height="800" alt="image" src="https://github.com/user-attachments/assets/285be1fd-8a70-4fbc-bc1c-e7eddc8e2dc9" />

## Stack

- Backend: FastAPI (Python), in-memory storage
- Frontend: React + TypeScript + Vite

## Features

- `POST /customers/push`: endpoint for ERP -> fake third-party push (upsert customer, no webhook back)
- `GET /customers` and `GET /customers/{id}`: read endpoints for ERP
- `POST /webhook/config`: configure the ERP webhook URL
- `POST /customers` and `PATCH /customers/{id}`: changes on the fake third-party side (trigger ERP webhook)
- React UI: state visualization + customer editing + outbound webhook attempts and inbound ERP calls log (payload included)

`customer` model:
- `id` (string, internal third-party id)
- `archived` (boolean)
- `payment_term` (`Net 30`, `Net 60`, or `null`)

## Quick Start

### Prerequisites

- Python 3.11+ (or 3.10+)
- uv (https://docs.astral.sh/uv/)
- Node.js 20+ and npm

### 1) Terminal A - Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 2) Terminal B - Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

UI: `http://localhost:5173`

### 3) Verify everything is running

- API: `http://localhost:8000/health` should return `{"status":"ok"}`
- Frontend: open `http://localhost:5173`

## Example Flow

1. Configure the ERP webhook in the UI (`/webhook/config`).
2. Push a customer from ERP (`POST /customers/push`) or from the UI "Push from ERP" button.
3. Edit the customer in the UI (changes are patched directly).
4. The backend updates in-memory state and calls the ERP webhook.

Default ERP webhook URL:
- `http://localhost:8001/api/webhooks/third-party/sync`
