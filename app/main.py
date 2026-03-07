"""
Entry point for uvicorn app.main:app --reload (run from backend/).
Re-exports the FastAPI app from src.api.main.
"""
from src.api.main import app  # noqa: F401
