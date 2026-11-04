"""Raccolta delle notizie di calcio da fonti RSS su internet."""
import calendar
import html
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from flask import current_app

from ..extensions import db
from ..models import Article, CollectionRun
from .relevance import score_articles

log = logging.getLogger(__name__)

TAG_RE = re.compile(r"<[^>]+>")


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def clean_html(text: str, limit: int = 600) -> str:
    text = html.unescape(TAG_RE.sub(" ", text or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("…" if len(text) > limit else "")


def _entry_datetime(entry):
    for key in ("published_parsed", "updated_parsed"):
        st = entry.get(key)
        if st:
            ts = calendar.timegm(st)
            return datetime.fromtimestamp(ts, timezone.utc).replace(tzinfo=None)
    return None


def _entry_image(entry):
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key) or []:
            if m.get("url"):
                return m["url"]
    for enc in entry.get("enclosures") or []:
        if (enc.get("type") or "").startswith("image") and enc.get("href"):
            return enc["href"]
    m = re.search(r'<img[^>]+src="([^"]+)"', entry.get("summary", "") or "")
    return m.group(1) if m else None


def http_fetch(url: str, timeout: int = 10, user_agent: str = "ProvaNewsBot/1.0") -> bytes:
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": user_agent})
    resp.raise_for_status()
    return resp.content


def parse_feed(source: str, language: str, content: bytes):
    feed = feedparser.parse(content)
    if feed.bozo and not feed.entries:
        raise ValueError(f"feed non valido: {feed.bozo_exception}")
    items = []
    for e in feed.entries:
        link, title = e.get("link"), clean_html(e.get("title", ""), 500)
        if not link or not title:
            continue
        # Google News aggiunge " - Testata" in coda al titolo: lo togliamo
        publisher = (e.get("source") or {}).get("title")
        if publisher and title.endswith(f" - {publisher}"):
            title = title[: -len(publisher) - 3].strip()
        items.append(
            dict(
                url=link[:1000],
                title=title,
                summary=clean_html(e.get("summary", "")),
                source=source,
                language=language,
                image_url=(_entry_image(e) or "")[:1000] or None,
                published_at=_entry_datetime(e),
            )
        )
    return items


def rescore_all():
    articles = Article.query.all()
    score_articles(articles)
    db.session.commit()


def collect_news(triggered_by: str = "cron", fetch=http_fetch, feeds=None) -> CollectionRun:
    """Scarica tutte le fonti, salva le notizie nuove, ricalcola la rilevanza."""
    cfg = current_app.config
    feeds = feeds or cfg["NEWS_FEEDS"]
    run = CollectionRun(triggered_by=triggered_by)
    db.session.add(run)
    errors, new_count = [], 0
    max_age = _utcnow() - timedelta(days=cfg["NEWS_MAX_AGE_DAYS"])

    # Download in parallelo (fuori dal contesto Flask)
    timeout, ua = cfg["NEWS_HTTP_TIMEOUT"], cfg["NEWS_USER_AGENT"]

    def _download(item):
        source, (url, lang) = item
        try:
            return source, lang, fetch(url, timeout, ua), None
        except Exception as exc:
            return source, lang, None, exc

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_download, feeds.items()))

    known_urls = {u for (u,) in db.session.query(Article.url)}
    for source, lang, content, err in results:
        try:
            if err:
                raise err
            items = parse_feed(source, lang, content)
        except Exception as exc:  # una fonte giù non deve bloccare le altre
            log.warning("Errore fonte %s: %s", source, exc)
            errors.append(f"{source}: {exc}")
            continue
        for it in items:
            if it["url"] in known_urls:
                continue
            if it["published_at"] and it["published_at"] < max_age:
                continue
            db.session.add(Article(**it))
            known_urls.add(it["url"])
            new_count += 1

    # Pulizia notizie troppo vecchie
    Article.query.filter(
        Article.published_at.isnot(None), Article.published_at < max_age
    ).delete(synchronize_session=False)
    db.session.flush()

    score_articles(Article.query.all())
    run.new_articles = new_count
    run.errors = "\n".join(errors) or None
    run.finished_at = _utcnow()
    db.session.commit()
    return run
