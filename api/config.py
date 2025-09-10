import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL")
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
    DEBUG = False
    DEFAULT_PAGE_SIZE = 10
    ALERT_CHECK_ON_SALE = True
