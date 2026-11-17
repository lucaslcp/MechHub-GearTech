"""Tabelas privadas do GearTech (prefixo gt_). Outros módulos não as acessam."""
import json

from ...core.models import utcnow
from ...extensions import db


class TransmissionSet(db.Model):
    """Funcionalidade 1: conjunto de transmissão cadastrado."""

    __tablename__ = "gt_transmission_set"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("core_organization.id"), nullable=False, index=True)
    created_by = db.Column(db.Integer, db.ForeignKey("core_user.id"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    application = db.Column(db.String(120), nullable=True)   # ex.: "esteira transportadora"
    description = db.Column(db.Text, nullable=True)
    input_power_kw = db.Column(db.Float, nullable=False)
    input_speed_rpm = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    author = db.relationship("User")
    stages = db.relationship("Stage", back_populates="transmission_set", order_by="Stage.position",
                             cascade="all, delete-orphan")
    snapshots = db.relationship("ResultSnapshot", back_populates="transmission_set",
                                order_by="ResultSnapshot.created_at.desc()", cascade="all, delete-orphan")

    @property
    def source_ref(self) -> str:
        return f"geartech:set:{self.id}"


class Stage(db.Model):
    """Um estágio (par engrenado, polias ou corrente) de um conjunto."""

    __tablename__ = "gt_stage"

    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey("gt_transmission_set.id"), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)
    label = db.Column(db.String(80), nullable=True)
    stage_type = db.Column(db.String(40), nullable=False)
    driver = db.Column(db.Float, nullable=False)        # Z1 ou d1
    driven = db.Column(db.Float, nullable=False)        # Z2 ou d2
    efficiency = db.Column(db.Float, nullable=False)
    module_mm = db.Column(db.Float, nullable=True)
    pitch_mm = db.Column(db.Float, nullable=True)
    helix_angle_deg = db.Column(db.Float, nullable=False, default=0.0)

    transmission_set = db.relationship("TransmissionSet", back_populates="stages")


class ResultSnapshot(db.Model):
    """Resultado calculado e gravado a cada cadastro/edição (histórico de versões do conjunto)."""

    __tablename__ = "gt_result_snapshot"

    id = db.Column(db.Integer, primary_key=True)
    set_id = db.Column(db.Integer, db.ForeignKey("gt_transmission_set.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    total_ratio = db.Column(db.Float, nullable=False)
    total_efficiency = db.Column(db.Float, nullable=False)
    output_speed_rpm = db.Column(db.Float, nullable=False)
    output_torque_nm = db.Column(db.Float, nullable=False)
    output_power_kw = db.Column(db.Float, nullable=False)
    stage_count = db.Column(db.Integer, nullable=False)
    data_json = db.Column(db.Text, nullable=False)  # resultado completo em JSON

    transmission_set = db.relationship("TransmissionSet", back_populates="snapshots")

    @property
    def data(self) -> dict:
        return json.loads(self.data_json)


class QuickCalculation(db.Model):
    """Funcionalidades 2 a 5 nas calculadoras rápidas: cada cálculo fica salvo."""

    __tablename__ = "gt_quick_calculation"

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, db.ForeignKey("core_organization.id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("core_user.id"), nullable=True)
    kind = db.Column(db.String(20), nullable=False)          # relacao | rotacao | torque | potencia
    inputs_json = db.Column(db.Text, nullable=False)
    result_json = db.Column(db.Text, nullable=False)
    summary = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    user = db.relationship("User")

    @property
    def result(self) -> dict:
        return json.loads(self.result_json)

    @property
    def inputs(self) -> dict:
        return json.loads(self.inputs_json)
