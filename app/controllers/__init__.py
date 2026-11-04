def register_blueprints(app):
    from .auth import bp as auth_bp
    from .dashboard import bp as dashboard_bp
    from .main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
