"""Application factory: assembla Model, View (template Jinja) e Controller (blueprint)."""
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from .config import BASE_DIR, Config
from .extensions import csrf, db, login_manager


def create_app(config_class=Config):
    load_dotenv(BASE_DIR / ".env")
    app = Flask(
        __name__,
        template_folder="views/templates",
        static_folder="static",
        instance_path=str(BASE_DIR / "instance"),
    )
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import models  # noqa: F401  (registra i modelli)
    from .controllers import register_blueprints

    register_blueprints(app)

    from .cli import register_cli

    register_cli(app)

    with app.app_context():
        db.create_all()

    return app
