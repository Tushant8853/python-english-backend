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
    from app.core.logging import configure_logging

    settings = get_settings()
    # Configure logging before uvicorn bootstraps so our formatter/colors win.
    configure_logging(is_production=settings.is_production)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_production,
        reload_excludes=[".git", ".git/*", ".venv", ".venv/*", "__pycache__", "__pycache__/*"],
        # Prevent uvicorn from overriding app/core/logging.py formatting (colors + single-line output).
        # This keeps all logs (uvicorn + app) consistent in the terminal.
        log_config=None,
        log_level=None,
        access_log=False,
    )


if __name__ == "__main__":
    run()
