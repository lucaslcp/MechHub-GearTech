"""Módulo 3 — GearTech: análise de transmissões mecânicas.

Funcionalidades
 1. Cadastrar conjuntos de transmissão ............ routes.create / edit / delete
 2. Calcular relações de transmissão ............... calculations.transmission_ratio / total_ratio
 3. Calcular rotações .............................. calculations.output_speed
 4. Calcular torque ................................ calculations.torque_from_power / output_torque
 5. Calcular potência .............................. calculations.output_power / power_from_torque
 6. Simular transmissões com múltiplos estágios .... calculations.simulate_transmission / operating_sweep
 7. Comparar configurações ......................... services.compare
 8. Gerar gráficos e relatórios .................... services.set_charts / set_report_pdf / set_csv
 +  Integração GearTech → MechCalc ................. services.publish_to_mechcalc
"""
from flask import Blueprint

bp = Blueprint("geartech", __name__, url_prefix="/geartech", template_folder="templates")

from . import routes  # noqa: E402,F401
