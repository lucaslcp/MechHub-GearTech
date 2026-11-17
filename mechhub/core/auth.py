"""Autenticação: login, cadastro (com organização) e logout."""
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..shared.history import log_event
from .models import Organization, User

bp = Blueprint("auth", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=bool(request.form.get("remember")))
            next_url = request.args.get("next", "")
            # Só aceita redirecionamento interno (evita "open redirect").
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("dashboard.index")
            return redirect(next_url)
        flash("E-mail ou senha incorretos.", "danger")
    return render_template("auth/login.html")


@bp.route("/cadastro", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    form = {k: request.form.get(k, "").strip() for k in ("name", "email", "organization")}
    if request.method == "POST":
        password = request.form.get("password", "")
        errors = []
        if len(form["name"]) < 2:
            errors.append("Informe seu nome.")
        if not EMAIL_RE.match(form["email"]):
            errors.append("Informe um e-mail válido.")
        if len(password) < 6:
            errors.append("A senha precisa ter pelo menos 6 caracteres.")
        if len(form["organization"]) < 2:
            errors.append("Informe o nome da organização (empresa, equipe ou laboratório).")
        if User.query.filter_by(email=form["email"].lower()).first():
            errors.append("Já existe uma conta com esse e-mail.")
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register.html", form=form), 400

        org = Organization.query.filter_by(name=form["organization"]).first()
        role = "membro"
        if org is None:
            org = Organization(name=form["organization"])
            db.session.add(org)
            role = "admin"
        user = User(name=form["name"], email=form["email"].lower(), organization=org, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        log_event(org.id, user.id, "plataforma", "cadastro", f"Usuário {user.name} entrou na organização.")
        login_user(user)
        flash(f"Bem-vindo(a), {user.name}!", "success")
        return redirect(url_for("dashboard.index"))
    return render_template("auth/register.html", form=form)


@bp.route("/sair")
@login_required
def logout():
    logout_user()
    flash("Você saiu da plataforma.", "info")
    return redirect(url_for("auth.login"))
