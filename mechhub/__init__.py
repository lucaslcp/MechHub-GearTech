"""MechHub — plataforma SaaS integrada para Engenharia Mecânica.

Arquitetura: monólito modular em Flask. A Plataforma Central (core) cuida de
autenticação, usuários, organizações, painel e navegação; os Serviços
Compartilhados (shared) oferecem banco, gráficos, relatórios, histórico e
integração; cada módulo (modules/mXX_nome) é um Blueprint independente.
"""
from pathlib import Path

from flask import Flask, Response, render_template

from .config import INSTANCE_DIR, Config
from .extensions import db, login_manager


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    Path(INSTANCE_DIR).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    # Importar os modelos registra todas as tabelas no SQLAlchemy.
    from .core import models as core_models  # noqa: F401
    from .shared import models as shared_models  # noqa: F401
    from .modules.m03_geartech import models as geartech_models  # noqa: F401

    from .core.auth import bp as auth_bp
    from .core.dashboard import bp as dashboard_bp
    from .modules.m01_mechcalc import bp as mechcalc_bp
    from .modules.m03_geartech import bp as geartech_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(geartech_bp)
    app.register_blueprint(mechcalc_bp)

    from .core.registry import MODULES

    @app.context_processor
    def inject_navigation():
        return {"mechhub_modules": MODULES}

    from .shared.formatting import register_filters

    register_filters(app)

    @app.route("/vendor/plotly.min.js")
    def plotly_js():
        # Serve o Plotly.js que vem junto do pacote Python: os gráficos
        # funcionam mesmo sem internet.
        from plotly.offline import get_plotlyjs

        resp = Response(get_plotlyjs(), mimetype="application/javascript")
        resp.cache_control.max_age = 86400
        return resp

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404,
                               message="Página ou registro não encontrado."), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template("error.html", code=500,
                               message="Erro interno. A operação foi desfeita."), 500

    with app.app_context():
        db.create_all()
        if app.config.get("SEED_DEMO"):
            from .core.seed import seed_demo_data

            seed_demo_data()

    return app
