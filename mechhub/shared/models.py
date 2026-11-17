"""Modelos de dados compartilhados entre módulos.

Regra da plataforma: um módulo nunca lê as tabelas privadas de outro
(prefixos gt_, mc_ ...). A troca de dados acontece por estas tabelas
compartilhadas, sempre por meio das funções de `shared/integration.py`.
"""
from ..core.models import utcnow
from ..extensions import db


class HistoryEntry(db.Model):
    """Histórico de ações (serviço compartilhado de Histórico)."""

    __tablename__ = "shared_history"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("core_organization.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("core_user.id"), nullable=True)
    module = db.Column(db.String(40), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)

    user = db.relationship("User")


class TransmissionLoadRecord(db.Model):
    """Esforços de um eixo publicados pelo GearTech para o MechCalc.

    Cada linha é um eixo de um conjunto de transmissão: rotação, torque,
    potência e as forças que as engrenagens/polias/rodas aplicam nele.
    """

    __tablename__ = "shared_transmission_load"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("core_organization.id"), nullable=False, index=True)
    source_module = db.Column(db.String(40), nullable=False, default="geartech")
    source_ref = db.Column(db.String(60), nullable=False, index=True)  # ex.: "geartech:set:3"
    set_name = db.Column(db.String(120), nullable=False)
    shaft_index = db.Column(db.Integer, nullable=False)
    shaft_label = db.Column(db.String(80), nullable=False)
    speed_rpm = db.Column(db.Float, nullable=False)
    torque_nm = db.Column(db.Float, nullable=False)
    power_kw = db.Column(db.Float, nullable=False)
    tangential_force_n = db.Column(db.Float, nullable=True)
    radial_force_n = db.Column(db.Float, nullable=True)
    axial_force_n = db.Column(db.Float, nullable=True)
    published_by = db.Column(db.Integer, db.ForeignKey("core_user.id"), nullable=True)
    published_at = db.Column(db.DateTime, default=utcnow, nullable=False)
