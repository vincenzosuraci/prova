"""Controller dashboard: elenco notizie rilevanti e raccolta on-demand."""
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from ..extensions import db
from ..models import Article, CollectionRun
from ..services.news_collector import collect_news

bp = Blueprint("dashboard", __name__)
PER_PAGE = 30


@bp.route("/")
@login_required
def index():
    q = request.args.get("q", "").strip()
    source = request.args.get("source", "").strip()
    view = request.args.get("view", "top")  # top | latest
    page = request.args.get("page", 1, type=int)

    query = Article.query
    if q:
        like = f"%{q}%"
        query = query.filter(Article.title.ilike(like) | Article.summary.ilike(like))
    if source:
        query = query.filter(Article.source == source)

    if view == "latest":
        query = query.order_by(Article.published_at.desc().nullslast())
    else:
        # una sola notizia per "storia" (la migliore), ordinate per rilevanza
        best = (
            db.session.query(Article.cluster_id, func.max(Article.score).label("s"))
            .group_by(Article.cluster_id)
            .subquery()
        )
        query = query.join(
            best, (Article.cluster_id == best.c.cluster_id) & (Article.score == best.c.s)
        ).order_by(Article.score.desc())

    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    # notizie correlate (altre fonti sulla stessa storia)
    related = {}
    if view != "latest":
        ids = [a.cluster_id for a in pagination.items if a.cluster_size > 1]
        if ids:
            for a in Article.query.filter(Article.cluster_id.in_(ids)).all():
                related.setdefault(a.cluster_id, []).append(a)

    sources = [s for (s,) in db.session.query(Article.source).distinct().order_by(Article.source)]
    last_run = CollectionRun.query.order_by(CollectionRun.id.desc()).first()
    stats = dict(
        total=Article.query.count(),
        sources=len(sources),
        configured=len(current_app.config["NEWS_FEEDS"]),
    )
    return render_template(
        "dashboard/index.html",
        pagination=pagination,
        related=related,
        sources=sources,
        last_run=last_run,
        stats=stats,
        q=q,
        source=source,
        view=view,
    )


@bp.route("/collect", methods=["POST"])
@login_required
def collect():
    run = collect_news(triggered_by=current_user.username)
    msg = f"Raccolta completata: {run.new_articles} nuove notizie."
    if run.errors:
        msg += f" Fonti in errore: {len(run.errors.splitlines())}."
        flash(msg, "warning")
    else:
        flash(msg, "success")
    return redirect(url_for("dashboard.index"))


@bp.route("/runs")
@login_required
def runs():
    items = CollectionRun.query.order_by(CollectionRun.id.desc()).limit(50).all()
    return render_template("dashboard/runs.html", runs=items)
