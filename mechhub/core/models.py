"""Modelos compartilhados da Plataforma Central: organizações e usuários."""
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Organization(db.Model):
    """Empresa/cliente do SaaS. Todos os dados dos módulos pertencem a uma organização."""

    __tablename__ = "core_organization"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    users = db.relationship("User", back_populates="organization")


class User(UserMixin, db.Model):
    __tablename__ = "core_user"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="membro")
    organization_id = db.Column(db.Integer, db.ForeignKey("core_organization.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    organization = db.relationship("Organization", back_populates="users")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
