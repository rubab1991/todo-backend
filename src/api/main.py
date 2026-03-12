import asyncio
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.routes import tasks
from src.routes.websocket import router as ws_router
from src.routes.events import router as events_router
from src.api.chat_router import router as chat_router
from src import db
from src.services.event_publisher import get_kafka_producer, close_kafka_producer
from src.consumers.reminder_consumer import run_reminder_consumer
from src.consumers.audit_consumer import run_audit_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_reminder_consumer_task = None
_audit_consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _reminder_consumer_task, _audit_consumer_task
    try:
        await db.create_db_and_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error("Database initialization failed: %s", e)

    # Warm up Redpanda producer and start consumers
    await get_kafka_producer()
    _reminder_consumer_task = asyncio.create_task(run_reminder_consumer())
    _audit_consumer_task = asyncio.create_task(run_audit_consumer())

    yield

    # Graceful shutdown
    for task in (_reminder_consumer_task, _audit_consumer_task):
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    await close_kafka_producer()


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


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return JSON with details."""
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s: %s\n%s", request.method, request.url.path, exc, tb)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "traceback": tb.split("\n")[-4:]},
    )


@app.get("/")
async def root():
    return {"message": "Todo API v2 (Phase V — Event-Driven)"}


@app.get("/debug/tables")
async def debug_tables():
    """Temporary endpoint to check DB tables — remove after debugging."""
    from sqlalchemy import text, inspect
    from src.db import async_engine
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = [row[0] for row in result]
            # Also try to create tables if missing
            if "tasks" not in tables:
                await db.create_db_and_tables()
                result2 = await conn.execute(text(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                ))
                tables = [row[0] for row in result2]
                return {"tables": tables, "note": "Tables were missing, attempted creation"}
            return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}


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
