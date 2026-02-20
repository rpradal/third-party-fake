# Backend Fake Third-Party

## Run

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

API base URL: `http://localhost:8000`

## API Notes

- Customers are seeded in memory on startup (`hs-001`, `hs-002`, `hs-003`).
- `payment_term` accepted values: `Net 30`, `Net 60`, or `null`.
- Customer updates (`PATCH /customers/{customer_id}`) trigger outbound webhook calls.
- Inbound ERP requests (`POST`/`PUT`/`PATCH`, excluding frontend-origin requests) are tracked with payloads and exposed in `/state`.
- Manual outbound webhook trigger endpoint is still available: `POST /customers/{customer_id}/call-erp`.
