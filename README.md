## AI Usage Analyzer MVP v0

Stateless web app that analyzes how a student used AI while completing an assignment.

### Backend (FastAPI)

- Location: `backend/`
- Main app: `main.py` with `/health` and `/analyze` endpoints.
- Requirements: `backend/requirements.txt`

Run locally:

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (Next.js)

- Location: `frontend/`
- Entry: `app/page.tsx`

Run locally:

```bash
cd frontend
npm install
npm run dev
```

By default the frontend expects the API at `http://localhost:8000` (configurable via `NEXT_PUBLIC_API_BASE_URL`).

### Docker (stateless deployment)

Use Docker Compose to run both services:

```bash
docker-compose up --build
```

Then open `http://localhost:3000` to use the app.

