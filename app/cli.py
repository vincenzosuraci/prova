import click


def register_cli(app):
    @app.cli.command("collect-news")
    def collect_news_cmd():
        """Raccoglie le notizie di calcio (usato dal timer systemd)."""
        from .services.news_collector import collect_news

        run = collect_news(triggered_by="cron")
        click.echo(f"Nuove notizie: {run.new_articles}")
        if run.errors:
            click.echo("Errori:\n" + run.errors, err=True)
