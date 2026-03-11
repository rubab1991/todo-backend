import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import tasks
from src.routes.websocket import router as ws_router
from src.routes.events import router as events_router
from src.api.chat_router import router as chat_router
from src import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await db.create_db_and_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)
    yield


app = FastAPI(title="Todo API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Authorization"],
)

# Task CRUD routes
app.include_router(tasks.router, prefix="/api", tags=["tasks"])

# Chat / AI agent routes
app.include_router(chat_router, prefix="/api/{user_id}", tags=["chat"])

# WebSocket real-time updates
app.include_router(ws_router, tags=["websocket"])

# Dapr pub/sub subscription + event handlers
app.include_router(events_router, tags=["events"])


@app.get("/")
async def root():
    return {"message": "Todo API v2 (Phase V — Event-Driven)"}


@app.get("/health")
async def health():
    import os
    from src.config import settings
    # Quick DB connectivity check
    db_ok = False
    db_error = None
    try:
        from sqlalchemy import text
        from src.db import async_engine
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        db_error = str(e)
    return {
        "status": "healthy",
        "auth_configured": bool(settings.better_auth_secret),
        "db_configured": bool(settings.database_url_resolved),
        "db_connected": db_ok,
        "db_error": db_error,
        "cohere_configured": bool(settings.cohere_api_key),
    }
