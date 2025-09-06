import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # MySQL connection settings — override via .env in production
    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB = os.getenv("MYSQL_DB", "inventory_db")

    # Flask settings
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production-please")
    DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

    # Pagination default
    DEFAULT_PAGE_SIZE = 10

    # Low-stock alert threshold multiplier
    # Alert fires when stock <= reorder_level
    ALERT_CHECK_ON_SALE = True
