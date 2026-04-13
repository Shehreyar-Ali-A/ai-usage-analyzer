## AI Workspace Platform

Assignment-based AI workspace where students use AI directly inside the platform, then submit for analysis.

### Architecture

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL + OpenAI APIs
- **Frontend**: Next.js 14 + Tailwind CSS
- **AI Chat**: OpenAI Responses API with file search via Vector Stores
- **Analysis**: Multi-pass LLM pipeline with structured scoring

### Quick Start (Docker)

```bash
# Copy env file and add your OpenAI key
cp .env.example .env

# Start all services
docker-compose up --build
```

- Frontend: http://localhost:3333
- Backend API: http://localhost:8888
- API docs: http://localhost:8888/docs

### Quick Start (Local Development)

**Prerequisites**: Docker (for Postgres), Node.js 20+, Python 3.11+

```bash
# Copy env file and add your OpenAI key
cp .env.example .env

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Start Postgres + run migrations + start backend
bash dev.sh

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The `dev.sh` script handles everything for the backend:
- Starts a Postgres container on port 5433 (with persistent data)
- Loads env vars from `.env`
- Runs Alembic migrations
- Starts the FastAPI server on port 8888 with hot-reload

### Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5433/ai_workspace` |
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `OPENAI_CHAT_MODEL` | Model for chat | `gpt-4o` |
| `OPENAI_ANALYSIS_MODEL` | Model for analysis passes | `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL` | Model for embeddings | `text-embedding-3-large` |
| `OPENAI_USE_VECTOR_STORES` | Enable vector store file search | `true` |
| `FILE_STORAGE_MODE` | File storage backend | `local` |
| `LOCAL_STORAGE_PATH` | Local file storage path | `./uploads` |
| `MAX_UPLOAD_MB` | Max file upload size | `10` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3333` |

### API Routes

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/workspaces` | Create workspace |
| GET | `/api/workspaces` | List workspaces |
| GET | `/api/workspaces/{id}` | Get workspace |
| PATCH | `/api/workspaces/{id}` | Update workspace |
| DELETE | `/api/workspaces/{id}` | Soft delete workspace |
| POST | `/api/workspaces/{id}/chats` | Create chat |
| GET | `/api/workspaces/{id}/chats` | List chats |
| GET | `/api/chats/{id}` | Get chat with messages |
| PATCH | `/api/chats/{id}` | Update chat |
| DELETE | `/api/chats/{id}` | Soft delete chat |
| POST | `/api/chats/{id}/messages` | Send message (triggers AI) |
| POST | `/api/workspaces/{id}/files` | Upload file |
| GET | `/api/workspaces/{id}/files` | List files |
| PATCH | `/api/files/{id}` | Update file role/label |
| DELETE | `/api/files/{id}` | Soft delete file |
| POST | `/api/workspaces/{id}/submit` | Submit workspace |
| GET | `/api/workspaces/{id}/submission` | Get submission status |
| GET | `/api/workspaces/{id}/report` | Get analysis report |
