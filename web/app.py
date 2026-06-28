"""
web/app.py — DAVE Web Frontend Flask Application Factory

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Creates and configures the Flask application. The create_app() factory pattern
allows the app to be created with different configurations for production vs
testing without importing at module level.

Architecture notes:
    - GameEngine instances are stored in a server-side dict (ACTIVE_SESSIONS)
      keyed by user_id. With a 10-user cap this avoids the complexity of a
      proper session store while remaining fully functional.
    - The user database (UserDatabase) is attached to the app object so all
      blueprints can access it via current_app.user_db.
    - Per-user game DBs live in the user_dbs/ directory, each named
      user_{id}_{module_slug}.db, copied from the module's template on first use.

To run locally:
    cd ~/dev/RPG
    export DAVE_LLM_BACKEND=scaleway
    export SCW_SECRET_KEY=your-key
    python -m web.app

To run with gunicorn (production):
    gunicorn "web.app:create_app()" --bind 0.0.0.0:8000 --workers 1 --threads 4
    (single worker required — ACTIVE_SESSIONS is in-process memory)
"""

import logging
import os
from pathlib import Path

from flask import Flask

from web import config
from web.user_db import UserDatabase

logger = logging.getLogger(__name__)

# =============================================================================
# Server-side session store
#
# Maps user_id (int) → GameEngine instance.
# Populated on session start, cleared on exit or server restart.
# Not shared across processes — use a single gunicorn worker.
# =============================================================================
ACTIVE_SESSIONS: dict = {}


def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Sets up:
        - Secret key and debug flag from web.config
        - User database (schema applied if needed)
        - Blueprint registration (auth, game)
        - Logging (INFO to stderr; engine logs go to their own file)

    Returns:
        Configured Flask app instance.
    """
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )

    # ------------------------------------------------------------------
    # Flask configuration
    # ------------------------------------------------------------------
    app.secret_key = config.SECRET_KEY
    app.config["DEBUG"] = config.DEBUG

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_level = logging.DEBUG if config.DEBUG else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    # Suppress noisy third-party loggers.
    for noisy in ("httpx", "httpcore", "anthropic", "openai", "werkzeug"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # ------------------------------------------------------------------
    # User database
    # ------------------------------------------------------------------
    user_db = UserDatabase(config.USER_DB_PATH)
    user_db.init_schema()
    app.user_db = user_db  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Ensure user_dbs/ directory exists for per-user game database copies
    # ------------------------------------------------------------------
    Path(config.USER_DB_DIR).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Blueprint registration
    # ------------------------------------------------------------------
    from web.auth import auth_bp
    app.register_blueprint(auth_bp)

    from web.game import game_bp
    app.register_blueprint(game_bp)

    logger.info(
        "DAVE web app started: debug=%s max_users=%d budget=€%.2f",
        config.DEBUG,
        config.MAX_USERS,
        config.BUDGET_EUROS,
    )

    return app


# =============================================================================
# Development entry point
# =============================================================================

if __name__ == "__main__":
    app = create_app()
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("DAVE_WEB_PORT", "5000")),
        debug=config.DEBUG,
        # Disable reloader in debug mode to avoid double-initialisation of the
        # user database and ACTIVE_SESSIONS dict.
        use_reloader=False,
    )
