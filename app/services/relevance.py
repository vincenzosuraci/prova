"""Calcolo della rilevanza delle notizie.

Idea: una notizia è tanto più rilevante quanto più
  1. è coperta da più fonti diverse (raggruppiamo i titoli simili in "storie"),
  2. è recente,
  3. riguarda temi "caldi" (Serie A, Champions, calciomercato, big club, Nazionale...).
"""
import math
import re
import unicodedata
from datetime import datetime, timezone

STOPWORDS = set(
    """
    il lo la i gli le un uno una di da del dello della dei degli delle al allo alla ai agli alle
    dal dallo dalla dai dagli dalle nel nello nella nei negli nelle sul sullo sulla sui sugli sulle
    con per tra fra che chi cui non piu più come dove quando anche ancora solo dopo prima contro
    sono era sara sarà stato essere avere ha hanno ecco tutto tutti questa questo quello quella
    the and for with from that this was are will has have his her their into over after before
    about against new says said live video foto gallery news oggi ieri domani ufficiale
    """.split()
)

HOT_KEYWORDS = {
    "serie": 1.0, "champions": 2.0, "europa": 1.0, "conference": 0.5, "calciomercato": 2.0,
    "mercato": 1.0, "nazionale": 1.5, "azzurri": 1.5, "mondiale": 2.0, "mondiali": 2.0,
    "scudetto": 2.0, "derby": 1.5, "juventus": 1.0, "juve": 1.0, "inter": 1.0, "milan": 1.0,
    "napoli": 1.0, "roma": 1.0, "lazio": 1.0, "atalanta": 0.7, "fiorentina": 0.5,
    "bologna": 0.5, "torino": 0.5, "infortunio": 0.7, "esonero": 1.5, "allenatore": 0.7,
    "premier": 0.7, "liga": 0.5, "real": 0.5, "barcellona": 0.5, "barcelona": 0.5,
}

SIMILARITY_THRESHOLD = 0.34
RECENCY_HALF_LIFE_H = 18.0


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def tokens(title: str) -> set:
    words = re.findall(r"[a-z0-9]+", normalize(title))
    return {w for w in words if len(w) >= 3 and w not in STOPWORDS}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _find(parent, i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]
        i = parent[i]
    return i


def cluster(token_sets):
    """Union-find greedy: due titoli finiscono nella stessa storia se abbastanza simili."""
    n = len(token_sets)
    parent = list(range(n))
    for i in range(n):
        for j in range(i + 1, n):
            a, b = token_sets[i], token_sets[j]
            shared = len(a & b)
            if shared >= 2 and (jaccard(a, b) >= SIMILARITY_THRESHOLD or shared >= 4):
                ri, rj = _find(parent, i), _find(parent, j)
                if ri != rj:
                    parent[rj] = ri
    return [_find(parent, i) for i in range(n)]


def keyword_boost(tok: set) -> float:
    return min(3.0, sum(HOT_KEYWORDS.get(t, 0.0) for t in tok))


def recency(published_at, now=None) -> float:
    if published_at is None:
        return 0.3
    now = now or datetime.now(timezone.utc).replace(tzinfo=None)
    age_h = max(0.0, (now - published_at).total_seconds() / 3600)
    return math.pow(0.5, age_h / RECENCY_HALF_LIFE_H)


def score_articles(articles, now=None):
    """Assegna cluster_id, cluster_size e score a una lista di Article (in place)."""
    if not articles:
        return
    toks = [tokens(a.title) for a in articles]
    roots = cluster(toks)

    sources_per_cluster = {}
    for a, r in zip(articles, roots):
        sources_per_cluster.setdefault(r, set()).add(a.source)

    for a, r, t in zip(articles, roots, toks):
        n_sources = len(sources_per_cluster[r])
        root = articles[r]
        a.cluster_id = root.id if root.id is not None else -(r + 1)
        a.cluster_size = n_sources
        a.score = round(
            4.0 * (n_sources - 1) + 10.0 * recency(a.published_at, now) + keyword_boost(t), 3
        )
