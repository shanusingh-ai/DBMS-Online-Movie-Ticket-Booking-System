import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-this-secret-key")

    database_url = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://127.0.0.1:3306/movie_booking_system"
    )

    if database_url.startswith("mysql://"):
        database_url = database_url.replace(
            "mysql://",
            "mysql+pymysql://",
            1
        )

    SQLALCHEMY_DATABASE_URI = database_url

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
    }

    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
    TMDB_BASE_URL = "https://api.themoviedb.org/3"

    DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Hyderabad")

    SEAT_ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"]
    SEATS_PER_ROW = 10