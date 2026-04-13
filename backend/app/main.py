"""AI Workspace Platform -- FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import health, workspaces, chats, files, submissions, analysis

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(title="AI Workspace Platform", version="1.0.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(workspaces.router, prefix="/api", tags=["workspaces"])
app.include_router(chats.router, prefix="/api", tags=["chats"])
app.include_router(files.router, prefix="/api", tags=["files"])
app.include_router(submissions.router, prefix="/api", tags=["submissions"])
app.include_router(analysis.router, prefix="/api", tags=["analysis"])
