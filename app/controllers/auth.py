"""Controller autenticazione: registrazione, login, logout, profilo."""
from urllib.parse import urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from PIL import UnidentifiedImageError

from ..extensions import db
from ..models import User
from ..services.photos import delete_profile_photo, save_profile_photo
from .forms import LoginForm, ProfileForm, RegistrationForm

bp = Blueprint("auth", __name__)


def _handle_photo(form):
    """Ritorna (filename|None, ok)."""
    f = form.foto.data
    if not f or not getattr(f, "filename", ""):
        return None, True
    try:
        return save_profile_photo(f), True
    except (UnidentifiedImageError, OSError):
        form.foto.errors.append("Immagine non valida.")
        return None, False


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        foto, ok = _handle_photo(form)
        if ok:
            user = User(
                nome=form.nome.data.strip(),
                cognome=form.cognome.data.strip(),
                username=form.username.data.strip(),
                email=form.email.data.strip().lower(),
                foto=foto,
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash(f"Benvenuto, {user.nome}! Registrazione completata.", "success")
            return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = LoginForm()
    if form.validate_on_submit():
        ident = form.username.data.strip()
        user = User.query.filter(
            (User.username.ilike(ident)) | (User.email.ilike(ident))
        ).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            nxt = request.args.get("next")
            if not nxt or urlparse(nxt).netloc or not nxt.startswith("/"):
                nxt = url_for("dashboard.index")
            return redirect(nxt)
        flash("Credenziali non valide.", "danger")
    return render_template("auth/login.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Disconnesso.", "info")
    return redirect(url_for("main.index"))


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(current_user, obj=current_user)
    if form.validate_on_submit():
        foto, ok = _handle_photo(form)
        if ok:
            current_user.nome = form.nome.data.strip()
            current_user.cognome = form.cognome.data.strip()
            current_user.email = form.email.data.strip().lower()
            if foto:
                delete_profile_photo(current_user.foto)
                current_user.foto = foto
            if form.password.data:
                current_user.set_password(form.password.data)
            db.session.commit()
            flash("Profilo aggiornato.", "success")
            return redirect(url_for("auth.profile"))
    return render_template("auth/profile.html", form=form)
