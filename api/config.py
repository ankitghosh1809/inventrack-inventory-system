import os
import warnings
from dotenv import load_dotenv
load_dotenv()


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    DEFAULT_PAGE_SIZE = 10
    ALERT_CHECK_ON_SALE = True

    # ── Auth ──────────────────────────────────────────────
    # Single-admin login (see api/auth.py). Fine for a small business /
    # single-operator tool; swap for a real users table + per-user
    # roles if this ever needs more than one login.
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-this-in-production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Vercel terminates TLS in front of the function, so the app itself
    # sees plain HTTP — only require "Secure" cookies when explicitly
    # told we're behind HTTPS (Vercel sets the VERCEL env var on every
    # deployment; SESSION_COOKIE_SECURE=true works anywhere else).
    SESSION_COOKIE_SECURE = os.getenv("VERCEL") is not None or os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours

    # ── CORS ──────────────────────────────────────────────
    # Frontend and API are served from the same Vercel deployment in
    # production, so cross-origin requests normally shouldn't happen
    # at all there. This only matters for local dev, where the two are
    # sometimes served from different ports/origins. Comma-separated;
    # override with FRONTEND_ORIGINS in .env if your setup differs.
    CORS_ORIGINS = [
        o.strip() for o in os.getenv(
            "FRONTEND_ORIGINS",
            "http://localhost:5000,http://127.0.0.1:5000,http://localhost:5500,http://127.0.0.1:5500"
        ).split(",") if o.strip()
    ]


if Config.SECRET_KEY == "change-this-in-production" or Config.ADMIN_PASSWORD == "change-this-in-production":
    warnings.warn(
        "SECRET_KEY and/or ADMIN_PASSWORD are still set to their insecure defaults. "
        "Set them in api/.env locally, and in Vercel -> Settings -> Environment Variables "
        "for the deployed app, before relying on login to actually keep anyone out.",
        stacklevel=2,
    )
