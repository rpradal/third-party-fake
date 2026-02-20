# Backend fake third-party

## Lancer

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

API base URL: `http://localhost:8000`

## Notes API

- Customers pré-remplis en mémoire au démarrage.
- Plus de création de customer via API fake app.
- Appel ERP manuel par customer: `POST /customers/{customer_id}/call-erp`
