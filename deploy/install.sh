#!/usr/bin/env bash
# Installa/aggiorna "prova" su un LXC Debian/Ubuntu (eseguire come root).
#   curl -fsSL https://raw.githubusercontent.com/vincenzosuraci/prova/main/deploy/install.sh | bash
set -euo pipefail

REPO="${REPO:-https://github.com/vincenzosuraci/prova.git}"
BRANCH="${BRANCH:-main}"
APP_DIR="${APP_DIR:-/opt/prova}"
APP_USER="${APP_USER:-prova}"
PORT="${PORT:-80}"

echo "==> Pacchetti di sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip nginx ca-certificates curl >/dev/null

echo "==> Utente di servizio"
id -u "$APP_USER" >/dev/null 2>&1 || useradd --system --home "$APP_DIR" --shell /usr/sbin/nologin "$APP_USER"

echo "==> Codice sorgente"
if [ -d "$APP_DIR/.git" ]; then
  # il repo appartiene all'utente di servizio: evita l'errore "dubious ownership"
  git -c safe.directory="$APP_DIR" -C "$APP_DIR" fetch -q origin "$BRANCH"
  git -c safe.directory="$APP_DIR" -C "$APP_DIR" reset -q --hard "origin/$BRANCH"
else
  git clone -q -b "$BRANCH" "$REPO" "$APP_DIR"
fi

echo "==> Virtualenv e dipendenze"
[ -d "$APP_DIR/.venv" ] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"

echo "==> Configurazione (.env)"
if [ ! -f "$APP_DIR/.env" ]; then
  echo "SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')" > "$APP_DIR/.env"
fi
mkdir -p "$APP_DIR/instance" "$APP_DIR/app/static/uploads"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> systemd"
cp "$APP_DIR/deploy/prova.service" /etc/systemd/system/prova.service
cp "$APP_DIR/deploy/prova-news.service" /etc/systemd/system/prova-news.service
cp "$APP_DIR/deploy/prova-news.timer" /etc/systemd/system/prova-news.timer
systemctl daemon-reload
systemctl enable -q --now prova.service prova-news.timer
systemctl restart prova.service

echo "==> nginx (porta $PORT -> gunicorn 127.0.0.1:8000)"
sed "s/__PORT__/$PORT/" "$APP_DIR/deploy/nginx.conf" > /etc/nginx/sites-available/prova
ln -sf /etc/nginx/sites-available/prova /etc/nginx/sites-enabled/prova
rm -f /etc/nginx/sites-enabled/default
nginx -t -q
systemctl enable -q nginx
systemctl reload nginx || systemctl restart nginx

echo "==> Prima raccolta notizie"
systemctl start prova-news.service || true

sleep 2
curl -fsS "http://127.0.0.1:$PORT/health" && echo
echo "OK: http://$(hostname -I | awk '{print $1}'):$PORT/"
