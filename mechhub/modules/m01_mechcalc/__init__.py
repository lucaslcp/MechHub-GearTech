"""Módulo 1 — MechCalc (versão de demonstração da integração).

O MechCalc completo é responsabilidade de outra dupla. Esta versão mínima existe
apenas para mostrar o lado "consumidor" da integração GearTech → MechCalc:
ela lê os esforços publicados pelo GearTech, exclusivamente pelo serviço
`shared.integration`, e verifica eixos à torção.
"""
from flask import Blueprint

bp = Blueprint("mechcalc", __name__, url_prefix="/mechcalc", template_folder="templates")

from . import routes  # noqa: E402,F401
