"""Uvicorn entrypoint.

Run with PORT from `.env`:
  python main.py

Or explicitly:
  uvicorn main:app --reload --host 0.0.0.0 --port 4001
"""

from app.main import app

__all__ = ["app"]


def run() -> None:
    import uvicorn

    from app.core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_production,
        reload_excludes=[".git", ".git/*", ".venv", ".venv/*", "__pycache__", "__pycache__/*"],
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    run()
