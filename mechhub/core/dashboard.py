"""Painel da plataforma e páginas dos módulos que ainda não foram entregues."""
from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..shared.history import recent_events
from .registry import MODULES, get_module

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    from ..modules.m03_geartech.services import organization_summary

    return render_template(
        "dashboard.html",
        modules=MODULES,
        events=recent_events(current_user.organization_id, limit=8),
        geartech=organization_summary(current_user.organization_id),
    )


@bp.route("/modulo/<key>")
@login_required
def module_page(key: str):
    module = get_module(key)
    if module is None:
        abort(404)
    if module.endpoint:
        return redirect(url_for(module.endpoint))
    return render_template("module_placeholder.html", module=module)
