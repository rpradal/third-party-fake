# Frontend Fake Third-Party

## Run

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

App URL: `http://localhost:5173`

## Notes

- Customer changes are patched directly from the UI (no Save button).
- `payment_term` options are `None`, `Net 30`, and `Net 60`.
- Outbound and inbound webhook attempt panels are displayed side by side, each with internal scrolling.
