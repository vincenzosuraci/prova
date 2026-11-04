from datetime import datetime, timezone

from ..extensions import db


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Article(db.Model):
    """Notizia di calcio raccolta da una fonte RSS."""

    __tablename__ = "articles"

    id = db.Column(db.Integer, primary_key=True)
    url = db.Column(db.String(1000), unique=True, nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False)
    summary = db.Column(db.Text)
    source = db.Column(db.String(120), nullable=False, index=True)
    language = db.Column(db.String(5), default="it")
    image_url = db.Column(db.String(1000))
    published_at = db.Column(db.DateTime, index=True)  # UTC naive
    collected_at = db.Column(db.DateTime, default=_now)

    # Rilevanza (ricalcolata a ogni raccolta)
    score = db.Column(db.Float, default=0.0, index=True)
    cluster_id = db.Column(db.Integer, index=True)
    cluster_size = db.Column(db.Integer, default=1)  # n. fonti diverse sulla stessa storia

    def __repr__(self):
        return f"<Article {self.source}: {self.title[:40]}>"


class CollectionRun(db.Model):
    """Log di ogni esecuzione della raccolta notizie."""

    __tablename__ = "collection_runs"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=_now)
    finished_at = db.Column(db.DateTime)
    new_articles = db.Column(db.Integer, default=0)
    triggered_by = db.Column(db.String(40))  # username o "cron"
    errors = db.Column(db.Text)  # una riga per fonte in errore
