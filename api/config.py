import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    DEFAULT_PAGE_SIZE = 10
    ALERT_CHECK_ON_SALE = True

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
