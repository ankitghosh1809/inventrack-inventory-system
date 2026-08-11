"""
auth.py — single-admin session login.

InvenTrack originally shipped with every /api/* route wide open: anyone
with the URL could read or rewrite the entire inventory, no login of
any kind. This is the minimum fix for that — not a full user-accounts
system with roles/permissions, just enough that the app actually has a
door with a lock on it.

The session is Flask's built-in signed-cookie session (keyed off
Config.SECRET_KEY, already present in config.py but previously unused).
That means it needs no server-side session storage, which is exactly
what you want on Vercel's serverless functions — no per-instance state
to lose between cold starts.

If this ever needs more than one login (multiple staff accounts, roles,
etc.), replace ADMIN_USERNAME/ADMIN_PASSWORD with a real `users` table
and hash passwords with werkzeug.security.generate_password_hash.
"""

import hmac
from flask import Blueprint, session, request, jsonify, current_app

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Routes that must stay reachable without a session — the login
# endpoint itself, the logout endpoint (so a stale session can always
# be cleared client-side), the "am I logged in" check the frontend
# polls on load, and the health check (uptime monitors won't have a
# session cookie). Every other /api/* route requires login — see the
# before_request hook in app.py.
OPEN_PATHS = {"/api/health", "/api/auth/login", "/api/auth/logout", "/api/auth/me"}


def _check_credentials(username, password):
    if not username or not password:
        return False
    expected_user = current_app.config["ADMIN_USERNAME"]
    expected_pass = current_app.config["ADMIN_PASSWORD"]
    # hmac.compare_digest instead of == so a mistyped password can't be
    # brute-forced faster by timing how quickly the comparison fails.
    valid_user = hmac.compare_digest(username, expected_user)
    valid_pass = hmac.compare_digest(password, expected_pass)
    return valid_user and valid_pass


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    if _check_credentials(username, password):
        session.clear()
        session["logged_in"] = True
        session["username"] = username
        session.permanent = True
        return jsonify({"success": True, "message": "Logged in", "data": {"username": username}}), 200

    return jsonify({"success": False, "message": "Invalid username or password", "data": None}), 401


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out", "data": None}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    """Always 200 (even when logged out) — the frontend polls this on
    every load to decide whether to show the login screen, and treating
    'not logged in' as a request failure would just add noise."""
    if session.get("logged_in"):
        payload = {"authenticated": True, "username": session.get("username")}
    else:
        payload = {"authenticated": False, "username": None}
    return jsonify({"success": True, "message": "OK", "data": payload}), 200
