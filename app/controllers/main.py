from flask import Blueprint, current_app, redirect, render_template, url_for
from flask_login import current_user

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    return render_template("index.html")


@bp.route("/favicon.ico")
def favicon():
    return current_app.send_static_file("img/favicon.ico")


@bp.route("/health")
def health():
    return {"status": "ok"}
