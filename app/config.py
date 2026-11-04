"""Configurazione dell'applicazione (letta da variabili d'ambiente / file .env)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env(name, default=None):
    return os.environ.get(name, default)


class Config:
    SECRET_KEY = _env("SECRET_KEY", "dev-change-me")
    SQLALCHEMY_DATABASE_URI = _env(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'prova.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload foto profilo
    UPLOAD_FOLDER = Path(_env("UPLOAD_FOLDER", BASE_DIR / "app" / "static" / "uploads"))
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB
    ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
    PHOTO_SIZE = (256, 256)

    # Raccolta notizie
    NEWS_HTTP_TIMEOUT = int(_env("NEWS_HTTP_TIMEOUT", "10"))
    NEWS_MAX_AGE_DAYS = int(_env("NEWS_MAX_AGE_DAYS", "7"))
    NEWS_USER_AGENT = _env(
        "NEWS_USER_AGENT", "Mozilla/5.0 (compatible; ProvaNewsBot/1.0)"
    )
    # Fonti RSS: nome -> (url, lingua)
    NEWS_FEEDS = {
        "Gazzetta dello Sport": ("https://www.gazzetta.it/rss/calcio.xml", "it"),
        "Corriere dello Sport": ("https://www.corrieredellosport.it/rss/calcio", "it"),
        "Tuttosport": ("https://www.tuttosport.com/rss/calcio", "it"),
        "Sky Sport": (
            "https://news.google.com/rss/search?q=site:sport.sky.it+calcio&hl=it&gl=IT&ceid=IT:it",
            "it",
        ),
        "ANSA Calcio": ("https://www.ansa.it/sito/notizie/sport/calcio/calcio_rss.xml", "it"),
        "Google News - Calcio": (
            "https://news.google.com/rss/search?q=calcio&hl=it&gl=IT&ceid=IT:it",
            "it",
        ),
        "Google News - Calciomercato": (
            "https://news.google.com/rss/search?q=calciomercato&hl=it&gl=IT&ceid=IT:it",
            "it",
        ),
        "Football Italia": ("https://football-italia.net/feed/", "en"),
        "BBC Sport Football": ("https://feeds.bbci.co.uk/sport/football/rss.xml", "en"),
    }

    WTF_CSRF_ENABLED = True


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test"
