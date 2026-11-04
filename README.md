# Prova · Calcio News

Applicazione web Python (Flask) con architettura **MVC** che:

- gestisce la **registrazione degli utenti** (nome, cognome, username, password, foto, e-mail), login/logout e modifica profilo;
- offre una **dashboard** da cui raccogliere su internet le **notizie di calcio più rilevanti**, raggruppando la stessa storia riportata da più testate e ordinandola per rilevanza.

## Architettura

```
app/
├── models/          # MODEL  – SQLAlchemy: User, Article, CollectionRun
├── views/templates/ # VIEW   – template Jinja2 (auth, dashboard)
├── controllers/     # CONTROLLER – blueprint Flask (main, auth, dashboard) + form WTForms
├── services/        # logica di dominio: raccolta RSS, ranking, foto profilo
├── static/          # CSS, immagini, upload foto
├── config.py        # configurazione e fonti RSS
└── cli.py           # comando `flask collect-news`
```

### Come viene calcolata la rilevanza
Per ogni notizia (`app/services/relevance.py`):

1. i titoli vengono normalizzati e tokenizzati (senza stopword);
2. titoli simili (Jaccard ≥ 0.34 o ≥ 4 parole in comune) finiscono nella stessa **storia**;
3. `score = 4 × (fonti diverse − 1) + 10 × recency + bonus parole chiave`
   – recency con dimezzamento ogni 18 h; bonus per Serie A, Champions, calciomercato, big club, Nazionale…

La vista “Più rilevanti” mostra una notizia per storia con il badge “🔥 N fonti” e l'elenco delle altre testate.

### Fonti
Gazzetta dello Sport, Corriere dello Sport, Tuttosport, Sky Sport (via Google News), ANSA, Google News (calcio e calciomercato), Football Italia, BBC Sport. Si modificano in `NEWS_FEEDS` dentro `app/config.py`.
Le notizie si aggiornano dal pulsante in dashboard e automaticamente ogni 30 minuti (timer systemd). Sono conservate per 7 giorni (`NEWS_MAX_AGE_DAYS`).

## Sviluppo locale

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
python wsgi.py            # http://localhost:8000
flask --app wsgi collect-news
```

## Deploy su LXC (Debian/Ubuntu)

Come root nel container:

```bash
curl -fsSL https://raw.githubusercontent.com/vincenzosuraci/prova/main/deploy/install.sh | bash
```

Lo script installa nginx + gunicorn + virtualenv in `/opt/prova`, crea l'utente di servizio `prova`, genera la `SECRET_KEY` in `/opt/prova/.env` e abilita:

- `prova.service` – gunicorn su 127.0.0.1:8000 (dietro nginx sulla porta 80)
- `prova-news.timer` – raccolta notizie ogni 30 minuti

Rilanciare lo stesso comando aggiorna l'app all'ultimo commit di `main` (database e foto restano).

Comandi utili: `systemctl status prova`, `journalctl -u prova -f`, `systemctl list-timers prova-news.timer`.
