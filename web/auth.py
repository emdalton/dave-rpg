"""
web/auth.py — DAVE Web Frontend Authentication Routes

Developed with the assistance of Claude (model: claude-sonnet-4-6, Anthropic)

Handles user registration, login, and logout. Registration uses Cloudflare
Turnstile to block bots — no email address is collected or stored.

Routes:
    GET  /           — Landing page (redirects to /lobby if logged in)
    GET  /register   — Registration form
    POST /register   — Process registration + Turnstile verification
    GET  /login      — Login form
    POST /login      — Process login
    GET  /logout     — Log the user out and redirect to landing page

The login_required decorator is defined here and imported by game.py so
all protected routes share the same guard logic.
"""

import logging
from functools import wraps

import requests as http_requests
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from web import config

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__)


# =============================================================================
# Login guard decorator
# =============================================================================

def login_required(f):
    """
    Decorator: redirect to the login page if the user is not authenticated.

    Usage:
        @game_bp.route("/lobby")
        @login_required
        def lobby():
            ...

    The requested URL is not preserved for redirect-after-login; given the
    linear game flow (lobby → session) this is not needed.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# =============================================================================
# Landing page
# =============================================================================

@auth_bp.route("/")
def index():
    """Landing page. Redirects to lobby if already logged in."""
    if "user_id" in session:
        return redirect(url_for("game.lobby"))
    return render_template("index.html")


# =============================================================================
# Registration
# =============================================================================

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    GET:  Render the registration form. If no slots are available, render
          the slots-full page instead.
    POST: Validate Turnstile response, validate credentials, create account.
    """
    user_db = current_app.user_db  # type: ignore[attr-defined]

    # Slots-full check applies to both GET and POST so bots get no advantage
    # from submitting the form when it is no longer shown.
    if not user_db.slots_available():
        return render_template(
            "slots_full.html",
            message=config.SLOTS_FULL_MESSAGE,
            contact_url=config.CONTACT_URL,
        )

    if request.method == "GET":
        return render_template(
            "register.html",
            turnstile_site_key=config.TURNSTILE_SITE_KEY,
        )

    # ------------------------------------------------------------------
    # POST: process registration
    # ------------------------------------------------------------------
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    turnstile_response = request.form.get("cf-turnstile-response", "")

    # 1. Verify Turnstile token with Cloudflare.
    if not _verify_turnstile(turnstile_response):
        flash("CAPTCHA verification failed. Please try again.")
        return render_template(
            "register.html",
            turnstile_site_key=config.TURNSTILE_SITE_KEY,
        )

    # 2. Attempt registration.
    ok, reason = user_db.register(username, password)

    if not ok:
        if reason == "no_slots":
            # Slot filled between GET and POST (unlikely but handle it).
            return render_template(
                "slots_full.html",
                message=config.SLOTS_FULL_MESSAGE,
                contact_url=config.CONTACT_URL,
            )
        flash(reason)
        return render_template(
            "register.html",
            turnstile_site_key=config.TURNSTILE_SITE_KEY,
            username=username,  # re-populate the field on error
        )

    # 3. Registration succeeded — log the user in immediately.
    user = user_db.authenticate(username, password)
    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        logger.info("Auto-login after registration: user_id=%d", user["id"])

    return redirect(url_for("game.lobby"))


# =============================================================================
# Login
# =============================================================================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    GET:  Render the login form.
    POST: Authenticate credentials and redirect to lobby on success.
    """
    if "user_id" in session:
        return redirect(url_for("game.lobby"))

    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    user_db = current_app.user_db  # type: ignore[attr-defined]
    user = user_db.authenticate(username, password)

    if user is None:
        flash("Invalid username or password.")
        return render_template("login.html", username=username)

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    logger.info("Login: user_id=%d username=%r", user["id"], username)

    return redirect(url_for("game.lobby"))


# =============================================================================
# Logout
# =============================================================================

@auth_bp.route("/logout")
def logout():
    """
    End the user's session. Also discards any active GameEngine instance for
    this user so the game DB is cleanly closed.
    """
    user_id = session.get("user_id")
    if user_id is not None:
        # Clean up the server-side game session if one is active.
        from web.app import ACTIVE_SESSIONS
        engine_entry = ACTIVE_SESSIONS.pop(user_id, None)
        if engine_entry is not None:
            try:
                engine_entry["db"].close()
            except Exception:  # noqa: BLE001
                pass
            logger.info("GameEngine cleaned up on logout: user_id=%d", user_id)

    session.clear()
    return redirect(url_for("auth.index"))


# =============================================================================
# Turnstile verification helper
# =============================================================================

def _verify_turnstile(token: str) -> bool:
    """
    Verify a Cloudflare Turnstile response token with the Cloudflare API.

    Args:
        token: The cf-turnstile-response value submitted with the form.

    Returns:
        True if Cloudflare confirms the token is valid, False otherwise.
        Returns False (safe default) on any network or parsing error.
    """
    if not token:
        return False

    try:
        resp = http_requests.post(
            config.TURNSTILE_VERIFY_URL,
            data={
                "secret":   config.TURNSTILE_SECRET_KEY,
                "response": token,
                "remoteip": request.remote_addr,
            },
            timeout=5,
        )
        result = resp.json()
        success = bool(result.get("success", False))
        if not success:
            logger.warning(
                "Turnstile verification failed: %s",
                result.get("error-codes", []),
            )
        return success
    except Exception as exc:  # noqa: BLE001
        logger.error("Turnstile verification error: %s", exc)
        return False
