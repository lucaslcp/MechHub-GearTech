"""Torção em eixos maciços (usado com os esforços vindos do GearTech).

    τ = 16·T / (π·d³)                  tensão de cisalhamento máxima
    d_min = (16·T / (π·τ_adm))^(1/3)    diâmetro mínimo
    FS = τ_adm / τ                      fator de segurança

T em N·m é convertido para N·mm (×1000); com d em mm, τ sai em MPa.
"""
import math


class ShaftCalcError(ValueError):
    pass


def _positive(value, name):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ShaftCalcError(f"{name}: informe um número.") from None
    if not math.isfinite(v) or v <= 0:
        raise ShaftCalcError(f"{name}: o valor deve ser maior que zero.")
    return v


def torsion_stress_mpa(torque_nm: float, diameter_mm: float) -> float:
    t = _positive(torque_nm, "Torque") * 1000
    d = _positive(diameter_mm, "Diâmetro")
    return 16 * t / (math.pi * d ** 3)


def minimum_diameter_mm(torque_nm: float, allowable_mpa: float) -> float:
    t = _positive(torque_nm, "Torque") * 1000
    tau = _positive(allowable_mpa, "Tensão admissível")
    return (16 * t / (math.pi * tau)) ** (1 / 3)


def check_shaft(torque_nm: float, diameter_mm: float, allowable_mpa: float) -> dict:
    tau = torsion_stress_mpa(torque_nm, diameter_mm)
    allow = _positive(allowable_mpa, "Tensão admissível")
    return {
        "tau_mpa": tau,
        "d_min_mm": minimum_diameter_mm(torque_nm, allow),
        "safety_factor": allow / tau,
        "approved": tau <= allow,
    }
