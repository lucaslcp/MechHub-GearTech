"""GearTech — cálculos de transmissões mecânicas.

Funções puras: recebem números e devolvem números. Não acessam o banco nem o
Flask, por isso são fáceis de testar e de explicar.

Unidades usadas em todo o módulo
    potência P ........ kW
    rotação n ......... rpm
    torque T .......... N·m
    diâmetros, módulo . mm
    forças ............ N
    velocidade v ...... m/s

Fórmulas principais (ver docs/FORMULAS.md)
    relação de transmissão   i = Z2 / Z1   ou   i = d2 / d1
    rotação de saída         n2 = n1 / i
    velocidade angular       ω = 2·π·n / 60            [rad/s]
    torque                   T = P·1000 / ω  (≈ 9549·P / n)
    potência de saída        P2 = P1 · η
    torque de saída          T2 = T1 · i · η
    estágios em série        i_total = Π i_k ,  η_total = Π η_k
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np


class TransmissionError(ValueError):
    """Dado de entrada inválido para os cálculos de transmissão."""


# --------------------------------------------------------------------------
# Tipos de estágio
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class StageType:
    key: str
    label: str
    element: str            # "dentes" (Z1/Z2) ou "diametro" (d1/d2 em mm)
    driver_label: str
    driven_label: str
    default_efficiency: float
    rotation: str           # "inverte", "mantem" ou "90graus"
    max_ratio: float        # relação máxima recomendada por estágio
    geometry: str | None    # "modulo", "passo" ou None


STAGE_TYPES: dict[str, StageType] = {
    "engrenagem_reta": StageType(
        "engrenagem_reta", "Engrenagens cilíndricas de dentes retos", "dentes",
        "Z1 – dentes do pinhão (motor)", "Z2 – dentes da coroa (movida)", 0.98, "inverte", 6.0, "modulo"),
    "engrenagem_helicoidal": StageType(
        "engrenagem_helicoidal", "Engrenagens cilíndricas helicoidais", "dentes",
        "Z1 – dentes do pinhão (motor)", "Z2 – dentes da coroa (movida)", 0.98, "inverte", 8.0, "modulo"),
    "polia_correia": StageType(
        "polia_correia", "Polias e correia", "diametro",
        "d1 – diâmetro da polia motora (mm)", "d2 – diâmetro da polia movida (mm)", 0.95, "mantem", 6.0, None),
    "corrente": StageType(
        "corrente", "Rodas dentadas e corrente", "dentes",
        "Z1 – dentes do pinhão (motor)", "Z2 – dentes da coroa (movida)", 0.97, "mantem", 7.0, "passo"),
    "sem_fim": StageType(
        "sem_fim", "Parafuso sem-fim e coroa", "dentes",
        "Z1 – nº de entradas do sem-fim", "Z2 – dentes da coroa", 0.70, "90graus", 100.0, None),
}

PRESSURE_ANGLE_DEG = 20.0   # ângulo de pressão normalizado
MAX_STAGES = 10


# --------------------------------------------------------------------------
# Validação
# --------------------------------------------------------------------------
def positive(value, name: str) -> float:
    """Converte para float e exige valor finito e > 0."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise TransmissionError(f"{name}: informe um número.") from None
    if not math.isfinite(number) or number <= 0:
        raise TransmissionError(f"{name}: o valor deve ser maior que zero.")
    return number


def check_efficiency(eta, name: str = "Rendimento η") -> float:
    eta = positive(eta, name)
    if eta > 1:
        raise TransmissionError(f"{name}: use um valor entre 0 e 1 (ex.: 0,98 para 98 %).")
    return eta


# --------------------------------------------------------------------------
# Funcionalidades 2 a 5: fórmulas básicas
# --------------------------------------------------------------------------
def transmission_ratio(driver: float, driven: float) -> float:
    """Relação de transmissão de um par: i = Z2/Z1 (ou d2/d1).

    i > 1 → redução (saída mais lenta e com mais torque)
    i < 1 → multiplicação (saída mais rápida)
    """
    return positive(driven, "Elemento movido") / positive(driver, "Elemento motor")


def total_ratio(ratios) -> float:
    """Estágios em série: i_total = i1 · i2 · ... · ik."""
    values = np.asarray(list(ratios), dtype=float)
    if values.size == 0:
        raise TransmissionError("Informe pelo menos uma relação.")
    if np.any(values <= 0) or not np.all(np.isfinite(values)):
        raise TransmissionError("Todas as relações devem ser maiores que zero.")
    return float(np.prod(values))


def output_speed(input_speed_rpm: float, ratio: float) -> float:
    """n2 = n1 / i."""
    return positive(input_speed_rpm, "Rotação de entrada") / positive(ratio, "Relação de transmissão")


def angular_speed(speed_rpm: float) -> float:
    """ω = 2·π·n / 60  [rad/s]."""
    return 2 * math.pi * positive(speed_rpm, "Rotação") / 60


def torque_from_power(power_kw: float, speed_rpm: float) -> float:
    """T = P / ω  →  T[N·m] = P[kW]·1000 / ω[rad/s]."""
    return positive(power_kw, "Potência") * 1000 / angular_speed(speed_rpm)


def power_from_torque(torque_nm: float, speed_rpm: float) -> float:
    """P = T · ω  →  P[kW] = T[N·m] · ω[rad/s] / 1000."""
    return positive(torque_nm, "Torque") * angular_speed(speed_rpm) / 1000


def output_power(input_power_kw: float, efficiency: float) -> float:
    """P2 = P1 · η  (a diferença P1 − P2 vira calor/atrito)."""
    return positive(input_power_kw, "Potência de entrada") * check_efficiency(efficiency)


def output_torque(input_torque_nm: float, ratio: float, efficiency: float = 1.0) -> float:
    """T2 = T1 · i · η."""
    return (positive(input_torque_nm, "Torque de entrada") * positive(ratio, "Relação de transmissão")
            * check_efficiency(efficiency))


# --------------------------------------------------------------------------
# Geometria e esforços (usados na integração com o MechCalc)
# --------------------------------------------------------------------------
def pitch_diameter(module_mm: float, teeth: float, helix_angle_deg: float = 0.0) -> float:
    """Diâmetro primitivo d = m·Z / cos β  [mm] (β = 0 para dentes retos)."""
    m = positive(module_mm, "Módulo")
    z = positive(teeth, "Número de dentes")
    beta = math.radians(helix_angle_deg)
    return m * z / math.cos(beta)


def sprocket_pitch_diameter(pitch_mm: float, teeth: float) -> float:
    """Roda de corrente: d = p / sen(180°/Z)  [mm]."""
    p = positive(pitch_mm, "Passo da corrente")
    z = positive(teeth, "Número de dentes")
    return p / math.sin(math.pi / z)


def tangential_force(torque_nm: float, diameter_mm: float) -> float:
    """Ft = 2·T / d   (T em N·m, d em mm → ×1000)  [N]."""
    return 2000 * positive(torque_nm, "Torque") / positive(diameter_mm, "Diâmetro")


def radial_force(ft_n: float, pressure_angle_deg: float = PRESSURE_ANGLE_DEG, helix_angle_deg: float = 0.0) -> float:
    """Fr = Ft · tan(α) / cos(β)  [N]."""
    return ft_n * math.tan(math.radians(pressure_angle_deg)) / math.cos(math.radians(helix_angle_deg))


def axial_force(ft_n: float, helix_angle_deg: float) -> float:
    """Fa = Ft · tan(β)  [N]  (zero para dentes retos)."""
    return ft_n * math.tan(math.radians(helix_angle_deg))


def peripheral_speed(diameter_mm: float, speed_rpm: float) -> float:
    """v = π · d · n / 60000  [m/s]."""
    return math.pi * positive(diameter_mm, "Diâmetro") * positive(speed_rpm, "Rotação") / 60000


def minimum_teeth_no_undercut(pressure_angle_deg: float = PRESSURE_ANGLE_DEG, helix_angle_deg: float = 0.0) -> float:
    """Zmin = 2 / sen²(α) (≈ 17 para α = 20°), corrigido por cos³β nas helicoidais."""
    zmin = 2 / math.sin(math.radians(pressure_angle_deg)) ** 2
    return zmin * math.cos(math.radians(helix_angle_deg)) ** 3


# --------------------------------------------------------------------------
# Funcionalidade 6: simulação de transmissões com múltiplos estágios
# --------------------------------------------------------------------------
@dataclass
class StageInput:
    stage_type: str
    driver: float               # Z1 ou d1
    driven: float               # Z2 ou d2
    efficiency: float | None = None
    module_mm: float | None = None        # engrenagens
    pitch_mm: float | None = None         # corrente
    helix_angle_deg: float = 0.0          # helicoidais
    label: str = ""


@dataclass
class ShaftState:
    index: int
    label: str
    speed_rpm: float
    torque_nm: float
    power_kw: float
    direction: str


@dataclass
class StageResult:
    index: int
    label: str
    type_key: str
    type_label: str
    driver: float
    driven: float
    ratio: float
    efficiency: float
    input_speed_rpm: float
    output_speed_rpm: float
    input_torque_nm: float
    output_torque_nm: float
    input_power_kw: float
    output_power_kw: float
    power_loss_kw: float
    driver_diameter_mm: float | None = None
    driven_diameter_mm: float | None = None
    peripheral_speed_ms: float | None = None
    tangential_force_n: float | None = None
    radial_force_n: float | None = None
    axial_force_n: float | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class TransmissionResult:
    input_power_kw: float
    input_speed_rpm: float
    input_torque_nm: float
    output_power_kw: float
    output_speed_rpm: float
    output_torque_nm: float
    total_ratio: float
    total_efficiency: float
    total_power_loss_kw: float
    kind: str                       # "redutor", "multiplicador" ou "direta"
    shafts: list[ShaftState]
    stages: list[StageResult]

    @property
    def warnings(self) -> list[str]:
        return [f"Estágio {s.index}: {w}" for s in self.stages for w in s.warnings]

    @property
    def torque_multiplication(self) -> float:
        return self.output_torque_nm / self.input_torque_nm

    def to_dict(self) -> dict:
        data = asdict(self)
        data["warnings"] = self.warnings
        return data


def _br(value: float, decimals: int = 1) -> str:
    """Número com vírgula decimal para as mensagens de alerta."""
    return f"{value:.{decimals}f}".replace(".", ",")


def _flip(direction: str) -> str:
    return {"horário": "anti-horário", "anti-horário": "horário"}.get(direction, direction)


def _check_stage(k: int, st: StageInput) -> tuple[StageType, float, float, float]:
    stype = STAGE_TYPES.get(st.stage_type)
    if stype is None:
        raise TransmissionError(f"Estágio {k}: tipo de transmissão desconhecido ({st.stage_type!r}).")
    z1 = positive(st.driver, f"Estágio {k} – {stype.driver_label}")
    z2 = positive(st.driven, f"Estágio {k} – {stype.driven_label}")
    if stype.element == "dentes" and (z1 != int(z1) or z2 != int(z2)):
        raise TransmissionError(f"Estágio {k}: número de dentes/entradas deve ser inteiro.")
    eta = stype.default_efficiency if st.efficiency in (None, "") else st.efficiency
    eta = check_efficiency(eta, f"Estágio {k} – rendimento η")
    if not 0 <= float(st.helix_angle_deg or 0) <= 45:
        raise TransmissionError(f"Estágio {k}: ângulo de hélice deve estar entre 0° e 45°.")
    return stype, z1, z2, eta


def simulate_transmission(input_power_kw: float, input_speed_rpm: float,
                          stages: list[StageInput]) -> TransmissionResult:
    """Calcula, estágio por estágio, rotação, torque, potência e esforços em cada eixo.

    O eixo k é a saída do estágio k e a entrada do estágio k+1.
    """
    p = positive(input_power_kw, "Potência de entrada")
    n = positive(input_speed_rpm, "Rotação de entrada")
    if not stages:
        raise TransmissionError("Inclua pelo menos um estágio de transmissão.")
    if len(stages) > MAX_STAGES:
        raise TransmissionError(f"No máximo {MAX_STAGES} estágios por conjunto.")

    t = torque_from_power(p, n)
    direction = "horário"
    shafts = [ShaftState(0, "Eixo de entrada (motor)", n, t, p, direction)]
    results: list[StageResult] = []

    for k, st in enumerate(stages, start=1):
        stype, z1, z2, eta = _check_stage(k, st)
        i = z2 / z1
        n_out = n / i
        p_out = p * eta
        t_out = t * i * eta          # igual a torque_from_power(p_out, n_out)
        beta = float(st.helix_angle_deg or 0) if stype.key == "engrenagem_helicoidal" else 0.0

        res = StageResult(
            index=k, label=st.label or f"Estágio {k}", type_key=stype.key, type_label=stype.label,
            driver=z1, driven=z2, ratio=i, efficiency=eta,
            input_speed_rpm=n, output_speed_rpm=n_out, input_torque_nm=t, output_torque_nm=t_out,
            input_power_kw=p, output_power_kw=p_out, power_loss_kw=p - p_out,
        )

        # Diâmetros (quando a geometria foi informada) e esforços no engrenamento
        d1 = d2 = None
        if stype.geometry == "modulo" and st.module_mm:
            d1 = pitch_diameter(st.module_mm, z1, beta)
            d2 = pitch_diameter(st.module_mm, z2, beta)
        elif stype.geometry == "passo" and st.pitch_mm:
            d1 = sprocket_pitch_diameter(st.pitch_mm, z1)
            d2 = sprocket_pitch_diameter(st.pitch_mm, z2)
        elif stype.element == "diametro":
            d1, d2 = z1, z2

        if d1:
            res.driver_diameter_mm, res.driven_diameter_mm = d1, d2
            res.peripheral_speed_ms = peripheral_speed(d1, n)
            res.tangential_force_n = tangential_force(t, d1)
            if stype.geometry == "modulo":
                res.radial_force_n = radial_force(res.tangential_force_n, PRESSURE_ANGLE_DEG, beta)
                res.axial_force_n = axial_force(res.tangential_force_n, beta)

        # Alertas de projeto
        if stype.geometry == "modulo":
            zmin = minimum_teeth_no_undercut(PRESSURE_ANGLE_DEG, beta)
            if z1 < zmin:
                res.warnings.append(f"Z1 = {z1:.0f} < {_br(zmin)}: risco de interferência (adelgaçamento do pé do dente).")
            if not st.module_mm:
                res.warnings.append("Módulo não informado: diâmetros e forças no dente não foram calculados.")
        if stype.key == "corrente" and z1 < 17:
            res.warnings.append("Pinhão de corrente com menos de 17 dentes: efeito poligonal e desgaste maiores.")
        if i > stype.max_ratio:
            res.warnings.append(f"Relação {_br(i, 2)} acima da recomendada (até {_br(stype.max_ratio, 0)}) para este tipo; "
                                "considere dividir em mais estágios.")
        if res.peripheral_speed_ms:
            if stype.key == "polia_correia" and res.peripheral_speed_ms > 30:
                res.warnings.append(f"Velocidade da correia {_br(res.peripheral_speed_ms)} m/s acima de 30 m/s.")
            if stype.geometry == "modulo" and res.peripheral_speed_ms > 20:
                res.warnings.append(f"Velocidade periférica {_br(res.peripheral_speed_ms)} m/s: exige alta precisão "
                                    "e lubrificação forçada.")
        if eta < 0.5:
            res.warnings.append("Rendimento menor que 50 %: a maior parte da potência vira calor.")
        if stype.key == "sem_fim" and eta < 0.5:
            res.warnings.append("Sem-fim com η < 0,5 tende a ser autotravante (não gira de trás para frente).")

        if stype.rotation == "inverte":
            direction = _flip(direction)
        elif stype.rotation == "90graus":
            direction = "eixo a 90° (depende da hélice)"

        results.append(res)
        label = "Eixo de saída" if k == len(stages) else f"Eixo intermediário {k}"
        shafts.append(ShaftState(k, label, n_out, t_out, p_out, direction))
        n, t, p = n_out, t_out, p_out

    i_total = total_ratio(r.ratio for r in results)
    eta_total = float(np.prod([r.efficiency for r in results]))
    kind = "redutor" if i_total > 1.0001 else "multiplicador" if i_total < 0.9999 else "direta"
    return TransmissionResult(
        input_power_kw=shafts[0].power_kw, input_speed_rpm=shafts[0].speed_rpm,
        input_torque_nm=shafts[0].torque_nm, output_power_kw=p, output_speed_rpm=n, output_torque_nm=t,
        total_ratio=i_total, total_efficiency=eta_total, total_power_loss_kw=shafts[0].power_kw - p,
        kind=kind, shafts=shafts, stages=results,
    )


def operating_sweep(input_power_kw: float, input_speed_rpm: float, stages: list[StageInput],
                    variable: str = "rotacao", start: float | None = None, stop: float | None = None,
                    points: int = 25) -> dict:
    """Varre uma condição de operação e devolve as curvas de saída (NumPy vetorizado).

    variable = "rotacao": varia a rotação do motor com potência constante.
    variable = "potencia": varia a potência com rotação constante.
    """
    base = simulate_transmission(input_power_kw, input_speed_rpm, stages)
    if not 2 <= int(points) <= 200:
        raise TransmissionError("Número de pontos deve estar entre 2 e 200.")
    nominal = base.input_speed_rpm if variable == "rotacao" else base.input_power_kw
    lo = positive(start if start not in (None, "") else nominal * 0.25, "Valor inicial")
    hi = positive(stop if stop not in (None, "") else nominal * 1.5, "Valor final")
    if hi <= lo:
        raise TransmissionError("O valor final deve ser maior que o inicial.")

    x = np.linspace(lo, hi, int(points))
    if variable == "rotacao":
        n_in = x
        p_in = np.full_like(x, base.input_power_kw)
    elif variable == "potencia":
        n_in = np.full_like(x, base.input_speed_rpm)
        p_in = x
    else:
        raise TransmissionError("Variável de simulação deve ser 'rotacao' ou 'potencia'.")

    t_in = p_in * 1000 / (2 * np.pi * n_in / 60)
    n_out = n_in / base.total_ratio
    p_out = p_in * base.total_efficiency
    t_out = t_in * base.total_ratio * base.total_efficiency
    return {
        "variable": variable,
        "x": x.round(4).tolist(),
        "input_speed_rpm": n_in.round(4).tolist(),
        "input_power_kw": p_in.round(4).tolist(),
        "input_torque_nm": t_in.round(4).tolist(),
        "output_speed_rpm": n_out.round(4).tolist(),
        "output_power_kw": p_out.round(4).tolist(),
        "output_torque_nm": t_out.round(4).tolist(),
        "total_ratio": base.total_ratio,
        "total_efficiency": base.total_efficiency,
    }
