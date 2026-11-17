"""Serviços de integração entre módulos.

Integração obrigatória implementada aqui: GearTech → MechCalc
("compartilhar esforços e parâmetros de transmissão para análises mecânicas").

- O GearTech chama `publish_transmission_loads(...)`.
- O MechCalc chama `list_transmission_loads(...)` / `get_transmission_load(...)`.

Nenhum dos dois acessa as tabelas privadas do outro: ambos só conhecem o
contrato `TransmissionLoad` e estas funções.
"""
import math

from ..extensions import db
from .contracts import TransmissionLoad
from .models import TransmissionLoadRecord


class IntegrationError(ValueError):
    """Dados inválidos enviados para a integração."""


def _check(load: TransmissionLoad) -> None:
    for name in ("speed_rpm", "torque_nm", "power_kw"):
        value = getattr(load, name)
        if value is None or not math.isfinite(value) or value <= 0:
            raise IntegrationError(f"{name} precisa ser um número positivo (eixo {load.shaft_label}).")


def _to_contract(rec: TransmissionLoadRecord) -> TransmissionLoad:
    return TransmissionLoad(
        id=rec.id,
        source_ref=rec.source_ref,
        set_name=rec.set_name,
        shaft_index=rec.shaft_index,
        shaft_label=rec.shaft_label,
        speed_rpm=rec.speed_rpm,
        torque_nm=rec.torque_nm,
        power_kw=rec.power_kw,
        tangential_force_n=rec.tangential_force_n,
        radial_force_n=rec.radial_force_n,
        axial_force_n=rec.axial_force_n,
        published_at=rec.published_at,
    )


def publish_transmission_loads(organization_id: int, user_id: int | None,
                               loads: list[TransmissionLoad]) -> int:
    """Publica (ou substitui) os esforços de um conjunto. Retorna quantos eixos foram gravados."""
    if not loads:
        raise IntegrationError("Nenhum eixo para publicar.")
    refs = {load.source_ref for load in loads}
    if len(refs) != 1:
        raise IntegrationError("Publique um conjunto de transmissão por vez.")
    for load in loads:
        _check(load)

    source_ref = refs.pop()
    TransmissionLoadRecord.query.filter_by(organization_id=organization_id, source_ref=source_ref).delete()
    for load in loads:
        db.session.add(TransmissionLoadRecord(
            organization_id=organization_id,
            source_module="geartech",
            source_ref=load.source_ref,
            set_name=load.set_name,
            shaft_index=load.shaft_index,
            shaft_label=load.shaft_label,
            speed_rpm=load.speed_rpm,
            torque_nm=load.torque_nm,
            power_kw=load.power_kw,
            tangential_force_n=load.tangential_force_n,
            radial_force_n=load.radial_force_n,
            axial_force_n=load.axial_force_n,
            published_by=user_id,
        ))
    db.session.commit()
    return len(loads)


def withdraw_transmission_loads(organization_id: int, source_ref: str) -> int:
    """Remove os esforços publicados de um conjunto (ex.: quando ele é excluído)."""
    count = TransmissionLoadRecord.query.filter_by(organization_id=organization_id, source_ref=source_ref).delete()
    db.session.commit()
    return count


def list_transmission_loads(organization_id: int) -> list[TransmissionLoad]:
    records = (TransmissionLoadRecord.query
               .filter_by(organization_id=organization_id)
               .order_by(TransmissionLoadRecord.set_name, TransmissionLoadRecord.shaft_index)
               .all())
    return [_to_contract(r) for r in records]


def get_transmission_load(organization_id: int, load_id: int) -> TransmissionLoad | None:
    rec = db.session.get(TransmissionLoadRecord, load_id)
    if rec is None or rec.organization_id != organization_id:
        return None
    return _to_contract(rec)


def is_published(organization_id: int, source_ref: str) -> bool:
    return db.session.query(
        TransmissionLoadRecord.query.filter_by(organization_id=organization_id, source_ref=source_ref).exists()
    ).scalar()
