"""
web/game.py — DAVE Web Frontend Game Routes

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Handles the game session lifecycle: module/model selection (lobby), Green Room
character creation, the main turn loop, and session exit.

Routes:
    GET  /lobby          — Module and model selector (post-login landing)
    POST /lobby          — Start a new session with the chosen module
    GET  /green_room     — Character creation form (green_room modules only)
    POST /green_room     — Submit character description → LLM extraction
    POST /green_room/confirm  — Accept or correct the extracted character
    GET  /session        — Main game session view
    POST /session/turn   — Submit a player turn, return prose
    POST /session/exit   — End the session cleanly

All game routes require login (enforced by @login_required from web.auth).
Token usage is recorded after every LLM call and checked before each turn.

NOTE: This module is a work in progress. The lobby and session routes are
implemented; Green Room and turn processing will be completed in the next
session.
"""

import logging
import shutil
from pathlib import Path

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from web import config
from web.auth import login_required
from web.app import ACTIVE_SESSIONS

logger = logging.getLogger(__name__)

game_bp = Blueprint("game", __name__)


# =============================================================================
# Lobby — module and model selection
# =============================================================================

@game_bp.route("/lobby", methods=["GET", "POST"])
@login_required
def lobby():
    """
    GET:  Show the module/model selector. If the user has an active session
          already, offer to continue it or start fresh.
    POST: Start a new session with the chosen module. Provisions the per-user
          game DB if it does not yet exist, then redirects to /session (or
          /green_room if the module requires character creation).
    """
    user_id = session["user_id"]
    user_db = current_app.user_db  # type: ignore[attr-defined]

    # Turn-limit check — show contact message if exhausted.
    turns = user_db.get_turn_status(user_id)
    if turns["exhausted"]:
        return render_template(
            "turns_exhausted.html",
            message=config.TURNS_EXHAUSTED_MESSAGE.format(max_turns=config.MAX_TURNS),
            contact_url=config.CONTACT_URL,
            turns=turns,
        )

    if request.method == "GET":
        has_active_session = user_id in ACTIVE_SESSIONS
        return render_template(
            "lobby.html",
            modules=config.AVAILABLE_MODULES,
            has_active_session=has_active_session,
            turns=turns,
            username=session.get("username"),
        )

    # ------------------------------------------------------------------
    # POST: start a new session
    # ------------------------------------------------------------------
    module_name = request.form.get("module", "")
    if module_name not in config.AVAILABLE_MODULES:
        flash("Please select a valid module.")
        return redirect(url_for("game.lobby"))

    # Close any existing session for this user before starting a new one.
    _close_session(user_id)

    # Provision per-user game DB.
    # Always copy fresh and run reset_instance.sql so the user starts from a
    # clean state regardless of what the source DB was left in.
    module_cfg   = config.AVAILABLE_MODULES[module_name]
    template_path  = module_cfg["db"]
    reset_script   = module_cfg["reset_script"]
    module_slug    = _slugify(module_name)
    user_db_path   = _user_game_db_path(user_id, module_slug)

    shutil.copy2(template_path, user_db_path)
    logger.info(
        "Copied template DB for user_id=%d module=%r → %s",
        user_id, module_name, user_db_path,
    )
    _run_reset_script(user_db_path, reset_script)

    # Open the database and create the GameEngine.
    try:
        from engine.db import Database
        from engine.engine import GameEngine
        import engine.config as engine_config

        # Point the engine at the user's personal game DB.
        db = Database(str(user_db_path))
        engine = GameEngine(db, game_id=1)

        ACTIVE_SESSIONS[user_id] = {
            "engine": engine,
            "db":     db,
            "module": module_name,
        }
        logger.info(
            "Session started: user_id=%d module=%r", user_id, module_name
        )
    except Exception as exc:
        logger.error("Failed to start session for user_id=%d: %s", user_id, exc)
        flash(f"Could not start session: {exc}")
        return redirect(url_for("game.lobby"))

    # Route to Green Room if the module requires it.
    if engine.needs_green_room():
        return redirect(url_for("game.green_room"))

    # Otherwise go straight to the game session.
    return redirect(url_for("game.game_session"))


# =============================================================================
# Green Room — character creation
# =============================================================================

@game_bp.route("/green_room", methods=["GET", "POST"])
@login_required
def green_room():
    """
    GET:  Show the character creation form with the module's prompt.
    POST: Submit character description → LLM extraction → confirmation display.
    """
    user_id = session["user_id"]
    entry = ACTIVE_SESSIONS.get(user_id)
    if entry is None:
        flash("No active session. Please start a new game.")
        return redirect(url_for("game.lobby"))

    engine = entry["engine"]
    gr_config = engine.get_green_room_config()

    if request.method == "GET":
        return render_template("green_room.html", gr_config=gr_config)

    # POST: player submitted their description.
    player_input = request.form.get("description", "").strip()
    if not player_input:
        flash("Please describe your character before continuing.")
        return render_template("green_room.html", gr_config=gr_config)

    try:
        extracted = engine.extract_green_room_character(player_input)
        _record_last_tokens(user_id, entry["engine"])
    except Exception as exc:
        logger.error("Green Room extraction failed for user_id=%d: %s", user_id, exc)
        flash("Character extraction failed — please try again.")
        return render_template("green_room.html", gr_config=gr_config)

    # Store the player_input in session so /green_room/confirm can append corrections.
    session["gr_input"] = player_input

    return render_template(
        "green_room_confirm.html",
        gr_config=gr_config,
        extracted=extracted,
        player_input=player_input,
    )


@game_bp.route("/green_room/confirm", methods=["POST"])
@login_required
def green_room_confirm():
    """
    Accept or reject the extracted character data.
    - confirmed=yes → finalise and go to session
    - confirmed=no  → player provides a correction, re-run extraction
    """
    user_id = session["user_id"]
    entry = ACTIVE_SESSIONS.get(user_id)
    if entry is None:
        return redirect(url_for("game.lobby"))

    engine = entry["engine"]
    confirmed = request.form.get("confirmed", "no").lower()

    if confirmed == "yes":
        engine.confirm_green_room()
        return redirect(url_for("game.game_session"))

    # Player wants to correct — append correction to prior input and re-extract.
    correction = request.form.get("correction", "").strip()
    prior_input = session.get("gr_input", "")
    updated_input = (
        prior_input + "\n\nPlayer correction: " + correction
        if correction else prior_input
    )

    gr_config = engine.get_green_room_config()
    try:
        extracted = engine.extract_green_room_character(updated_input)
        _record_last_tokens(user_id, entry["engine"])
    except Exception as exc:
        logger.error("Green Room re-extraction failed: %s", exc)
        flash("Extraction failed — please try again.")
        return render_template("green_room.html", gr_config=gr_config)

    session["gr_input"] = updated_input
    return render_template(
        "green_room_confirm.html",
        gr_config=gr_config,
        extracted=extracted,
        player_input=updated_input,
    )


# =============================================================================
# Game session
# =============================================================================

@game_bp.route("/session")
@login_required
def game_session():
    """
    Main session view. Renders the game terminal UI and fetches the opening
    scene prose on first visit.
    """
    user_id = session["user_id"]
    entry = ACTIVE_SESSIONS.get(user_id)
    if entry is None:
        flash("No active session. Please start a new game.")
        return redirect(url_for("game.lobby"))

    user_db = current_app.user_db  # type: ignore[attr-defined]
    turns = user_db.get_turn_status(user_id)
    if turns["exhausted"]:
        return render_template(
            "turns_exhausted.html",
            message=config.TURNS_EXHAUSTED_MESSAGE.format(max_turns=config.MAX_TURNS),
            contact_url=config.CONTACT_URL,
            turns=turns,
        )

    # Generate opening scene on first visit (session flag prevents re-rendering).
    opening = None
    if not session.get("session_opened"):
        try:
            opening = entry["engine"].get_opening_scene()
            _record_last_tokens(user_id, entry["engine"])
            session["session_opened"] = True
        except Exception as exc:
            logger.error("Opening scene failed for user_id=%d: %s", user_id, exc)
            opening = f"You are {entry['engine']._player['name']}."

    return render_template(
        "session.html",
        opening=opening,
        module=entry["module"],
        turns=turns,
        username=session.get("username"),
    )


@game_bp.route("/session/turn", methods=["POST"])
@login_required
def session_turn():
    """
    Process one player turn. Expects JSON body: {"input": "..."}
    Returns JSON: {"prose": "...", "budget": {...}, "ended": false}

    If the player types an exit command, returns {"ended": true}.
    On budget exhaustion, returns {"exhausted": true}.
    """
    user_id = session["user_id"]
    entry = ACTIVE_SESSIONS.get(user_id)
    if entry is None:
        return jsonify({"error": "No active session."}), 400

    user_db = current_app.user_db  # type: ignore[attr-defined]

    # Turn-limit check before processing.
    turns = user_db.get_turn_status(user_id)
    if turns["exhausted"]:
        return jsonify({
            "exhausted":   True,
            "message":     config.TURNS_EXHAUSTED_MESSAGE.format(
                               max_turns=config.MAX_TURNS),
            "contact_url": config.CONTACT_URL,
            "turns":       turns,
        })

    data = request.get_json(silent=True) or {}
    player_input = data.get("input", "").strip()
    if not player_input:
        return jsonify({"error": "Empty input."}), 400

    try:
        from engine.llm.base import LLMError, LLMJSONError
        prose = entry["engine"].step(player_input)
        _record_last_tokens(user_id, entry["engine"])
    except (LLMError, LLMJSONError) as exc:
        logger.error("LLM error during turn for user_id=%d: %s", user_id, exc)
        return jsonify({"error": str(exc)}), 500
    except Exception as exc:
        logger.error("Unexpected error during turn for user_id=%d: %s", user_id, exc)
        return jsonify({"error": "An unexpected error occurred."}), 500

    if prose is None:
        # Player typed exit.
        _close_session(user_id)
        session.pop("session_opened", None)
        return jsonify({"ended": True, "turns": user_db.get_turn_status(user_id)})

    # Record the turn only after successful prose rendering.
    user_db.record_turn(user_id)
    turns = user_db.get_turn_status(user_id)

    return jsonify({
        "prose": prose,
        "turns": turns,
        "ended": False,
    })


@game_bp.route("/session/exit", methods=["POST"])
@login_required
def session_exit():
    """End the session cleanly and return to the lobby."""
    user_id = session["user_id"]
    _close_session(user_id)
    session.pop("session_opened", None)
    session.pop("gr_input", None)
    return redirect(url_for("game.lobby"))


# =============================================================================
# Helpers
# =============================================================================

def _run_reset_script(db_path: Path, script_path: str) -> None:
    """
    Run a reset_instance.sql script against the given database file.

    Called immediately after copying a fresh user DB so the instance starts
    in a known clean state. Uses stdlib sqlite3 directly — no engine DB
    wrapper is open yet at this point.

    Args:
        db_path:     Path to the user's personal game database copy.
        script_path: Path to the reset_instance.sql script for this module.
    """
    import sqlite3 as _sqlite3
    sql = Path(script_path).read_text()
    conn = _sqlite3.connect(str(db_path))
    try:
        conn.executescript(sql)
        conn.commit()
        logger.info("Reset script applied: %s → %s", script_path, db_path)
    finally:
        conn.close()


def _user_game_db_path(user_id: int, module_slug: str) -> Path:
    """Return the path for a user's personal game database copy."""
    return Path(config.USER_DB_DIR) / f"user_{user_id}_{module_slug}.db"


def _slugify(name: str) -> str:
    """Convert a module display name to a safe filename slug."""
    return name.lower().replace(" ", "_").replace("-", "_")


def _close_session(user_id: int) -> None:
    """
    Discard the active GameEngine and close the game DB for the given user.
    Safe to call even if no session is active.
    """
    entry = ACTIVE_SESSIONS.pop(user_id, None)
    if entry is not None:
        try:
            entry["db"].close()
        except Exception:  # noqa: BLE001
            pass
        logger.info("Session closed: user_id=%d", user_id)


def _record_last_tokens(user_id: int, engine) -> None:
    """
    Read the most recent token counts from the LLM client and record them
    against the user's budget. Called after every LLM call.

    The Scaleway backend accumulates a running total; we compare against the
    last recorded value to get the delta for this call. For backends that
    don't track tokens, this is a no-op.
    """
    llm = getattr(engine, "llm", None)
    if llm is None:
        return

    # The Scaleway backend logs tokens at INFO level but does not currently
    # expose a programmatic running total (unlike the Claude backend which has
    # token_totals()). We read from the response usage object stored on the
    # LLM client, if available.
    #
    # TODO (next session): add a get_last_call_tokens() method to
    # ScalewayLLMClient so this can be wired up precisely. For now, budget
    # tracking is approximate (tokens are logged but not credited here).
    pass
