import io
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

from app import create_app
from app.config import TestConfig
from app.extensions import db
from app.models import Article, User
from app.services.news_collector import collect_news
from app.services.relevance import cluster, tokens


def _rss(items):
    now = datetime.now(timezone.utc)
    body = "".join(
        f"<item><title>{t}</title><link>{l}</link><description>{t} desc</description>"
        f"<pubDate>{(now - timedelta(hours=h)).strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate></item>"
        for t, l, h in items
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title>{body}</channel></rss>'.encode()


FEEDS = {
    "Fonte A": ("http://a/rss", "it"),
    "Fonte B": ("http://b/rss", "it"),
    "Rotta": ("http://broken/rss", "it"),
}
CONTENT = {
    "http://a/rss": _rss([
        ("Inter, Lautaro operato: salta il derby con il Milan", "http://a/1", 1),
        ("Calciomercato Juventus: offerta per il centrocampista", "http://a/2", 5),
    ]),
    "http://b/rss": _rss([
        ("Lautaro operato, l'Inter perde l'attaccante per il derby", "http://b/1", 2),
        ("Vecchia notizia", "http://b/old", 24 * 30),
    ]),
}


def fake_fetch(url, timeout=10, ua=""):
    if url not in CONTENT:
        raise ConnectionError("offline")
    return CONTENT[url]


@pytest.fixture
def app(tmp_path):
    class Cfg(TestConfig):
        UPLOAD_FOLDER = tmp_path / "uploads"
        NEWS_FEEDS = FEEDS

    app = create_app(Cfg)
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


def _png():
    buf = io.BytesIO()
    Image.new("RGB", (400, 300), "red").save(buf, "PNG")
    buf.seek(0)
    return buf


def register(client, username="mrossi", email="m@rossi.it", photo=True):
    data = dict(nome="Mario", cognome="Rossi", username=username, email=email,
                password="password123", conferma="password123")
    if photo:
        data["foto"] = (_png(), "me.png")
    return client.post("/auth/register", data=data, content_type="multipart/form-data",
                       follow_redirects=True)


def test_register_login_logout(client, app):
    r = register(client)
    assert r.status_code == 200 and "Benvenuto, Mario" in r.text
    with app.app_context():
        u = User.query.filter_by(username="mrossi").one()
        assert u.foto and u.check_password("password123")
        assert (app.config["UPLOAD_FOLDER"] / u.foto).exists()
    client.post("/auth/logout")
    r = client.post("/auth/login", data=dict(username="m@rossi.it", password="password123"),
                    follow_redirects=True)
    assert "Ciao Mario" in r.text


def test_duplicate_and_bad_photo(client):
    register(client)
    client.post("/auth/logout")
    r = register(client, photo=False)
    assert "Username già in uso" in r.text
    r = client.post("/auth/register", data=dict(
        nome="A", cognome="B", username="abc", email="a@b.it", password="password123",
        conferma="password123", foto=(io.BytesIO(b"not an image"), "x.png")),
        content_type="multipart/form-data")
    assert "Immagine non valida" in r.text


def test_dashboard_requires_login(client):
    r = client.get("/dashboard/")
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_clustering():
    t = [tokens("Inter, Lautaro operato: salta il derby"),
         tokens("Lautaro operato, l'Inter perde il derby"),
         tokens("Calciomercato Juventus, offerta")]
    roots = cluster(t)
    assert roots[0] == roots[1] != roots[2]


def test_collect_and_rank(app, client):
    with app.app_context():
        run = collect_news(fetch=fake_fetch)
        assert run.new_articles == 3  # la notizia vecchia è scartata
        assert "Rotta" in run.errors
        top = Article.query.order_by(Article.score.desc()).first()
        assert "Lautaro" in top.title and top.cluster_size == 2
        # seconda raccolta: nessun duplicato
        assert collect_news(fetch=fake_fetch).new_articles == 0

    register(client)
    r = client.get("/dashboard/")
    assert "2 fonti" in r.text and "Calciomercato Juventus" in r.text
    # in vista "top" la storia Lautaro compare una volta sola come principale
    assert r.text.count("<article") == 2
    r = client.get("/dashboard/?view=latest")
    assert r.text.count("<article") == 3
    r = client.get("/dashboard/?q=juventus")
    assert r.text.count("<article") == 1
