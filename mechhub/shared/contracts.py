"""Contratos de integração: os formatos de dados que os módulos trocam.

Definidos pela "equipe de infraestrutura" para que cada equipe trabalhe sem
depender do código interno das outras.
"""
from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True)
class TransmissionLoad:
    """Esforços em um eixo de transmissão (GearTech → MechCalc).

    Unidades: rpm, N·m, kW e N.
    """

    source_ref: str
    set_name: str
    shaft_index: int
    shaft_label: str
    speed_rpm: float
    torque_nm: float
    power_kw: float
    tangential_force_n: float | None = None
    radial_force_n: float | None = None
    axial_force_n: float | None = None
    id: int | None = None
    published_at: datetime | None = None

    def to_dict(self) -> dict:
        return asdict(self)
