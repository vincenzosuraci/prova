"""Form (input dei controller) con validazione lato server."""
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, Optional, Regexp, ValidationError

from ..models import User

PHOTO_EXT = ["jpg", "jpeg", "png", "gif", "webp"]


class RegistrationForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=80)])
    cognome = StringField("Cognome", validators=[DataRequired(), Length(max=80)])
    username = StringField(
        "Username",
        validators=[
            DataRequired(),
            Length(min=3, max=40),
            Regexp(r"^[A-Za-z0-9_.-]+$", message="Solo lettere, numeri, . _ -"),
        ],
    )
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=128)])
    conferma = PasswordField(
        "Conferma password",
        validators=[DataRequired(), EqualTo("password", message="Le password non coincidono")],
    )
    foto = FileField("Foto", validators=[Optional(), FileAllowed(PHOTO_EXT, "Solo immagini")])
    submit = SubmitField("Registrati")

    def validate_username(self, field):
        if User.query.filter(User.username.ilike(field.data)).first():
            raise ValidationError("Username già in uso.")

    def validate_email(self, field):
        if User.query.filter(User.email.ilike(field.data)).first():
            raise ValidationError("E-mail già registrata.")


class LoginForm(FlaskForm):
    username = StringField("Username o e-mail", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Ricordami")
    submit = SubmitField("Accedi")


class ProfileForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=80)])
    cognome = StringField("Cognome", validators=[DataRequired(), Length(max=80)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    foto = FileField("Nuova foto", validators=[Optional(), FileAllowed(PHOTO_EXT, "Solo immagini")])
    password = PasswordField("Nuova password (opzionale)", validators=[Optional(), Length(min=8, max=128)])
    conferma = PasswordField(
        "Conferma nuova password",
        validators=[EqualTo("password", message="Le password non coincidono")],
    )
    submit = SubmitField("Salva")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user

    def validate_email(self, field):
        other = User.query.filter(User.email.ilike(field.data)).first()
        if other and other.id != self._user.id:
            raise ValidationError("E-mail già registrata.")
