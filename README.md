# Sync Demo - Fake Third Party

Projet de démo pour tester une synchro ERP avec un faux third-party.

## Stack

- Backend: FastAPI (Python), stockage en mémoire
- Frontend: React + TypeScript + Vite

## Features

- `POST /customers/push`: endpoint pour push ERP -> fake third-party (upsert customer, pas de webhook retour)
- `GET /customers` et `GET /customers/{id}`: endpoints de lecture côté ERP
- `POST /webhook/config`: configuration de l'URL webhook ERP
- `POST /customers` et `PATCH /customers/{id}`: modifications côté fake third-party (déclenchent un webhook ERP)
- UI React: visualisation état + édition des customers + journal des tentatives webhook sortantes et appels entrants ERP (payload inclus)

Modèle `customer`:
- `id` (string, id interne third-party)
- `archived` (bool)
- `payment_term` (`Net 30`, `Net 60` ou `null`)

## Démarrage rapide

### Prérequis

- Python 3.11+ (ou 3.10+)
- uv (https://docs.astral.sh/uv/)
- Node.js 20+ et npm

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

### 3) Vérifier que tout tourne

- API: `http://localhost:8000/health` doit répondre `{"status":"ok"}`
- Front: ouvrir `http://localhost:5173`

## Exemple de flux

1. Configurer le webhook ERP dans l'UI (`/webhook/config`).
2. Pousser un customer depuis l'ERP (`POST /customers/push`) ou via l'UI bouton "Push from ERP".
3. Modifier le customer dans l'UI puis cliquer sur "Save" (webhook implicite).
4. Le backend met à jour la mémoire et appelle le webhook ERP avec l'event `customer.updated`.

URL webhook ERP par défaut:
- `http://localhost:8001/api/webhooks/third-party/sync`
