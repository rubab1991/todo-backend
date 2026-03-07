"""
Database module initialization
This file imports and exposes the required database functions to maintain backward compatibility
while allowing for a modular database structure.
"""

from .session import get_async_session_dep, get_or_create_user, get_async_session, engine as async_engine

# Define create_db_and_tables function in this module
async def create_db_and_tables():
    """Create database tables if they don't exist."""
    from sqlmodel import SQLModel
    from ..models import Task, User  # Import models here

    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)