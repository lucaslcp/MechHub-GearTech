"""Extensões Flask compartilhadas por toda a plataforma.

Ficam num arquivo separado para que qualquer módulo possa importar `db`
sem criar importação circular com `create_app`.
"""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Entre na plataforma para acessar esta página."
login_manager.login_message_category = "warning"
