"""
Database module initialization
This file imports and exposes the required database functions to maintain backward compatibility
while allowing for a modular database structure.
"""

from .session import get_async_session_dep, get_or_create_user, get_async_session, engine as async_engine

# Define create_db_and_tables function in this module
async def create_db_and_tables():
    """Create database tables if they don't exist, and add missing Phase V columns."""
    from sqlmodel import SQLModel
    from sqlalchemy import text
    # Import ALL models so SQLAlchemy registers them
    from ..models import Task, User, Conversation, Message, AuditLog  # noqa: F401

    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Add Phase V columns if missing (SQLModel create_all doesn't alter existing tables)
    phase_v_columns = [
        ("tasks", "tags", "VARCHAR"),
        ("tasks", "recurring_interval", "VARCHAR"),
        ("tasks", "reminder_at", "VARCHAR"),
        ("tasks", "priority", "VARCHAR DEFAULT 'medium'"),
        ("tasks", "completed", "BOOLEAN DEFAULT false"),
    ]
    async with async_engine.begin() as conn:
        for table, column, col_type in phase_v_columns:
            try:
                await conn.execute(text(
                    f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
                ))
            except Exception:
                pass  # Column already exists or other non-critical error