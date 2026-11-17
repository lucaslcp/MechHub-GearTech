"""GearTech — regras de negócio.

Camada entre as telas (routes.py) e os cálculos (calculations.py):
lê formulários, valida, grava no banco, monta tabelas (Pandas), gráficos,
relatórios e publica os esforços para o MechCalc.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

import pandas as pd

from ...extensions import db
from ...shared import charts, integration
from ...shared.contracts import TransmissionLoad
from ...shared.formatting import fmt_num
from ...shared.history import log_event
from ...shared.reports import PdfReport
from . import calculations as calc
from .calculations import STAGE_TYPES, StageInput, TransmissionError, TransmissionResult
from .models import QuickCalculation, ResultSnapshot, Stage, TransmissionSet

MODULE = "geartech"


class GearTechValidationError(ValueError):
    """Erros de preenchimento de formulário (uma ou mais mensagens)."""

    def __init__(self, messages):
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        super().__init__("; ".join(self.messages))


# --------------------------------------------------------------------------
# Leitura de formulários
# --------------------------------------------------------------------------
def parse_number(raw, name: str, required: bool = True) -> float | None:
    """Aceita '1,5', '1.5' e '1.234,5'. Devolve None se vazio e não obrigatório."""
    text = "" if raw is None else str(raw).strip().replace(" ", "")
    if text == "":
        if required:
            raise GearTechValidationError(f"{name}: campo obrigatório.")
        return None
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        raise GearTechValidationError(f"{name}: '{raw}' não é um número válido.") from None


@dataclass
class SetData:
    name: str
    application: str
    description: str
    input_power_kw: float
    input_speed_rpm: float
    stages: list[StageInput] = field(default_factory=list)


def parse_set_form(form) -> SetData:
    """Lê o formulário de conjunto (campos de estágio vêm em listas: stage_type[], driver[] ...)."""
    errors: list[str] = []

    def number(raw, name, required=True):
        try:
            return parse_number(raw, name, required)
        except GearTechValidationError as exc:
            errors.extend(exc.messages)
            return None

    name = (form.get("name") or "").strip()
    if len(name) < 3:
        errors.append("Nome do conjunto: use pelo menos 3 caracteres.")
    power = number(form.get("input_power_kw"), "Potência de entrada")
    speed = number(form.get("input_speed_rpm"), "Rotação de entrada")

    types = form.getlist("stage_type")
    drivers = form.getlist("driver")
    drivens = form.getlist("driven")
    etas = form.getlist("efficiency")
    modules = form.getlist("module_mm")
    pitches = form.getlist("pitch_mm")
    helix = form.getlist("helix_angle_deg")
    labels = form.getlist("stage_label")

    def at(values, k):
        return values[k] if k < len(values) else ""

    stages = []
    for k, stype in enumerate(types):
        n = k + 1
        if stype not in STAGE_TYPES:
            errors.append(f"Estágio {n}: escolha o tipo de transmissão.")
            continue
        info = STAGE_TYPES[stype]
        eta = number(at(etas, k), f"Estágio {n} – rendimento", required=False)
        if eta is not None and eta > 1:
            eta = eta / 100  # o usuário digitou em %, ex.: 98
        stages.append(StageInput(
            stage_type=stype,
            driver=number(at(drivers, k), f"Estágio {n} – {info.driver_label}"),
            driven=number(at(drivens, k), f"Estágio {n} – {info.driven_label}"),
            efficiency=eta,
            module_mm=number(at(modules, k), f"Estágio {n} – módulo", required=False)
            if info.geometry == "modulo" else None,
            pitch_mm=number(at(pitches, k), f"Estágio {n} – passo", required=False)
            if info.geometry == "passo" else None,
            helix_angle_deg=(number(at(helix, k), f"Estágio {n} – ângulo de hélice", required=False) or 0.0)
            if stype == "engrenagem_helicoidal" else 0.0,
            label=(at(labels, k) or "").strip()[:80],
        ))
    if not types:
        errors.append("Inclua pelo menos um estágio de transmissão.")

    if errors:
        raise GearTechValidationError(errors)

    data = SetData(name=name[:120], application=(form.get("application") or "").strip()[:120],
                   description=(form.get("description") or "").strip()[:2000],
                   input_power_kw=power, input_speed_rpm=speed, stages=stages)
    simulate(data)  # validação física completa (lança erro se algo for inválido)
    return data


def simulate(data: SetData) -> TransmissionResult:
    try:
        return calc.simulate_transmission(data.input_power_kw, data.input_speed_rpm, data.stages)
    except TransmissionError as exc:
        raise GearTechValidationError(str(exc)) from None


# --------------------------------------------------------------------------
# Funcionalidade 1: cadastro de conjuntos (CRUD)
# --------------------------------------------------------------------------
def list_sets(organization_id: int) -> list[TransmissionSet]:
    return (TransmissionSet.query.filter_by(organization_id=organization_id)
            .order_by(TransmissionSet.updated_at.desc()).all())


def get_set(organization_id: int, set_id: int) -> TransmissionSet | None:
    ts = db.session.get(TransmissionSet, set_id)
    if ts is None or ts.organization_id != organization_id:
        return None  # conjunto de outra organização é tratado como inexistente
    return ts


def _apply(ts: TransmissionSet, data: SetData) -> None:
    ts.name = data.name
    ts.application = data.application or None
    ts.description = data.description or None
    ts.input_power_kw = data.input_power_kw
    ts.input_speed_rpm = data.input_speed_rpm
    ts.stages.clear()
    db.session.flush()
    for pos, st in enumerate(data.stages, start=1):
        ts.stages.append(Stage(
            position=pos, label=st.label or None, stage_type=st.stage_type, driver=st.driver, driven=st.driven,
            efficiency=st.efficiency if st.efficiency is not None else STAGE_TYPES[st.stage_type].default_efficiency,
            module_mm=st.module_mm, pitch_mm=st.pitch_mm, helix_angle_deg=st.helix_angle_deg or 0.0,
        ))


def _snapshot(ts: TransmissionSet, result: TransmissionResult) -> ResultSnapshot:
    snap = ResultSnapshot(
        total_ratio=result.total_ratio, total_efficiency=result.total_efficiency,
        output_speed_rpm=result.output_speed_rpm, output_torque_nm=result.output_torque_nm,
        output_power_kw=result.output_power_kw, stage_count=len(result.stages),
        data_json=json.dumps(result.to_dict(), ensure_ascii=False),
    )
    ts.snapshots.append(snap)
    return snap


def create_set(organization_id: int, user_id: int | None, data: SetData) -> TransmissionSet:
    result = simulate(data)
    ts = TransmissionSet(organization_id=organization_id, created_by=user_id)
    db.session.add(ts)
    _apply(ts, data)
    _snapshot(ts, result)
    db.session.commit()
    log_event(organization_id, user_id, MODULE, "cadastro",
              f"Conjunto '{ts.name}' cadastrado (i = {fmt_num(result.total_ratio, 2)}).")
    return ts


def update_set(ts: TransmissionSet, user_id: int | None, data: SetData) -> TransmissionSet:
    result = simulate(data)
    _apply(ts, data)
    _snapshot(ts, result)
    db.session.commit()
    if integration.is_published(ts.organization_id, ts.source_ref):
        # Mantém o MechCalc sincronizado com a versão nova.
        integration.publish_transmission_loads(ts.organization_id, user_id, transmission_loads(ts, result))
    log_event(ts.organization_id, user_id, MODULE, "edição", f"Conjunto '{ts.name}' atualizado.")
    return ts


def delete_set(ts: TransmissionSet, user_id: int | None) -> None:
    org_id, name, ref = ts.organization_id, ts.name, ts.source_ref
    db.session.delete(ts)
    db.session.commit()
    integration.withdraw_transmission_loads(org_id, ref)
    log_event(org_id, user_id, MODULE, "exclusão", f"Conjunto '{name}' excluído.")


def stage_inputs(ts: TransmissionSet) -> list[StageInput]:
    return [StageInput(stage_type=s.stage_type, driver=s.driver, driven=s.driven, efficiency=s.efficiency,
                       module_mm=s.module_mm, pitch_mm=s.pitch_mm, helix_angle_deg=s.helix_angle_deg,
                       label=s.label or "") for s in ts.stages]


def analyze(ts: TransmissionSet) -> TransmissionResult:
    return calc.simulate_transmission(ts.input_power_kw, ts.input_speed_rpm, stage_inputs(ts))


def set_to_form(ts: TransmissionSet) -> dict:
    return {
        "name": ts.name, "application": ts.application or "", "description": ts.description or "",
        "input_power_kw": ts.input_power_kw, "input_speed_rpm": ts.input_speed_rpm,
        "stages": [{"stage_type": s.stage_type, "driver": s.driver, "driven": s.driven,
                    "efficiency": s.efficiency, "module_mm": s.module_mm, "pitch_mm": s.pitch_mm,
                    "helix_angle_deg": s.helix_angle_deg, "label": s.label or ""} for s in ts.stages],
    }


def form_to_dict(form) -> dict:
    """Devolve o que o usuário digitou, para reexibir o formulário após um erro."""
    keys = ("stage_type", "driver", "driven", "efficiency", "module_mm", "pitch_mm", "helix_angle_deg", "stage_label")
    lists = {k: form.getlist(k) for k in keys}
    stages = []
    for k in range(len(lists["stage_type"])):
        row = {key: (lists[key][k] if k < len(lists[key]) else "") for key in keys}
        row["label"] = row.pop("stage_label")
        stages.append(row)
    return {"name": form.get("name", ""), "application": form.get("application", ""),
            "description": form.get("description", ""), "input_power_kw": form.get("input_power_kw", ""),
            "input_speed_rpm": form.get("input_speed_rpm", ""), "stages": stages}


# --------------------------------------------------------------------------
# Funcionalidades 2 a 5: calculadoras rápidas (resultado salvo no banco)
# --------------------------------------------------------------------------
QUICK_CALCS = {
    "relacao": "Relação de transmissão",
    "rotacao": "Rotação de saída",
    "torque": "Torque",
    "potencia": "Potência",
}


def run_quick_calc(kind: str, form, organization_id: int, user_id: int | None) -> QuickCalculation:
    if kind not in QUICK_CALCS:
        raise GearTechValidationError("Calculadora desconhecida.")
    try:
        if kind == "relacao":
            pairs = []
            for k, (a, b) in enumerate(zip(form.getlist("driver"), form.getlist("driven")), start=1):
                if not str(a).strip() and not str(b).strip():
                    continue
                pairs.append((parse_number(a, f"Par {k} – motor"), parse_number(b, f"Par {k} – movido")))
            if not pairs:
                raise GearTechValidationError("Informe pelo menos um par motor/movido.")
            ratios = [calc.transmission_ratio(a, b) for a, b in pairs]
            i_total = calc.total_ratio(ratios)
            inputs = {"pares": pairs}
            result = {"relacoes": ratios, "relacao_total": i_total,
                      "tipo": "redução" if i_total > 1 else "multiplicação" if i_total < 1 else "direta"}
            summary = f"{len(pairs)} par(es): i_total = {fmt_num(i_total, 4)}"
        elif kind == "rotacao":
            n1 = parse_number(form.get("speed"), "Rotação de entrada")
            i = parse_number(form.get("ratio"), "Relação de transmissão")
            n2 = calc.output_speed(n1, i)
            inputs = {"n1_rpm": n1, "i": i}
            result = {"n2_rpm": n2, "omega1_rad_s": calc.angular_speed(n1), "omega2_rad_s": calc.angular_speed(n2)}
            summary = f"n1 = {fmt_num(n1, 1)} rpm, i = {fmt_num(i, 3)} → n2 = {fmt_num(n2, 2)} rpm"
        elif kind == "torque":
            p = parse_number(form.get("power"), "Potência")
            n = parse_number(form.get("speed"), "Rotação")
            i = parse_number(form.get("ratio"), "Relação de transmissão", required=False) or 1.0
            eta = parse_number(form.get("efficiency"), "Rendimento", required=False) or 1.0
            if eta > 1:
                eta /= 100
            t1 = calc.torque_from_power(p, n)
            t2 = calc.output_torque(t1, i, eta)
            inputs = {"P_kW": p, "n_rpm": n, "i": i, "eta": eta}
            result = {"T1_Nm": t1, "T2_Nm": t2, "omega_rad_s": calc.angular_speed(n)}
            summary = (f"P = {fmt_num(p, 3)} kW, n = {fmt_num(n, 1)} rpm → T = {fmt_num(t1, 2)} N·m "
                       f"(saída {fmt_num(t2, 2)} N·m)")
        else:  # potencia
            mode = form.get("mode", "torque")
            eta = parse_number(form.get("efficiency"), "Rendimento", required=False) or 1.0
            if eta > 1:
                eta /= 100
            if mode == "torque":
                t = parse_number(form.get("torque"), "Torque")
                n = parse_number(form.get("speed"), "Rotação")
                p1 = calc.power_from_torque(t, n)
                inputs = {"T_Nm": t, "n_rpm": n, "eta": eta}
            else:
                p1 = parse_number(form.get("power"), "Potência de entrada")
                inputs = {"P1_kW": p1, "eta": eta}
            p2 = calc.output_power(p1, eta)
            result = {"P1_kW": p1, "P2_kW": p2, "perda_kW": p1 - p2, "P1_cv": p1 / 0.7355}
            summary = f"P1 = {fmt_num(p1, 3)} kW, η = {fmt_num(eta, 3)} → P2 = {fmt_num(p2, 3)} kW"
    except TransmissionError as exc:
        raise GearTechValidationError(str(exc)) from None

    record = QuickCalculation(organization_id=organization_id, user_id=user_id, kind=kind,
                              inputs_json=json.dumps(inputs), result_json=json.dumps(result), summary=summary)
    db.session.add(record)
    db.session.commit()
    return record


def recent_quick_calcs(organization_id: int, limit: int = 15) -> list[QuickCalculation]:
    return (QuickCalculation.query.filter_by(organization_id=organization_id)
            .order_by(QuickCalculation.created_at.desc(), QuickCalculation.id.desc()).limit(limit).all())


# --------------------------------------------------------------------------
# Tabelas (Pandas) e exportação CSV
# --------------------------------------------------------------------------
def shafts_dataframe(result: TransmissionResult) -> pd.DataFrame:
    return pd.DataFrame([{
        "Eixo": s.index, "Descrição": s.label, "Rotação (rpm)": round(s.speed_rpm, 3),
        "Torque (N·m)": round(s.torque_nm, 3), "Potência (kW)": round(s.power_kw, 4), "Sentido": s.direction,
    } for s in result.shafts])


def stages_dataframe(result: TransmissionResult) -> pd.DataFrame:
    return pd.DataFrame([{
        "Estágio": s.index, "Descrição": s.label, "Tipo": s.type_label, "Motor (Z1/d1)": s.driver,
        "Movido (Z2/d2)": s.driven, "Relação i": round(s.ratio, 4), "Rendimento η": s.efficiency,
        "n entrada (rpm)": round(s.input_speed_rpm, 3), "n saída (rpm)": round(s.output_speed_rpm, 3),
        "T entrada (N·m)": round(s.input_torque_nm, 3), "T saída (N·m)": round(s.output_torque_nm, 3),
        "P saída (kW)": round(s.output_power_kw, 4), "Perda (kW)": round(s.power_loss_kw, 4),
        "d1 (mm)": None if s.driver_diameter_mm is None else round(s.driver_diameter_mm, 2),
        "d2 (mm)": None if s.driven_diameter_mm is None else round(s.driven_diameter_mm, 2),
        "v (m/s)": None if s.peripheral_speed_ms is None else round(s.peripheral_speed_ms, 3),
        "Ft (N)": None if s.tangential_force_n is None else round(s.tangential_force_n, 1),
        "Fr (N)": None if s.radial_force_n is None else round(s.radial_force_n, 1),
        "Fa (N)": None if s.axial_force_n is None else round(s.axial_force_n, 1),
    } for s in result.stages])


def to_csv(df: pd.DataFrame) -> bytes:
    """CSV no padrão brasileiro (abre direto no Excel)."""
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def set_csv(ts: TransmissionSet, result: TransmissionResult) -> bytes:
    header = pd.DataFrame([{"Conjunto": ts.name, "Potência (kW)": ts.input_power_kw,
                            "Rotação (rpm)": ts.input_speed_rpm, "i total": round(result.total_ratio, 4),
                            "η total": round(result.total_efficiency, 4)}])
    parts = [to_csv(header), b"\r\n", to_csv(stages_dataframe(result)).removeprefix("﻿".encode()),
             b"\r\n", to_csv(shafts_dataframe(result)).removeprefix("﻿".encode())]
    return b"".join(parts)


# --------------------------------------------------------------------------
# Funcionalidade 7: comparação de configurações
# --------------------------------------------------------------------------
COMPARISON_METRICS = [
    ("total_ratio", "Relação total i", 4),
    ("output_speed_rpm", "Rotação de saída (rpm)", 2),
    ("output_torque_nm", "Torque de saída (N·m)", 2),
    ("output_power_kw", "Potência de saída (kW)", 3),
    ("total_efficiency", "Rendimento total η", 4),
    ("total_power_loss_kw", "Perda de potência (kW)", 3),
    ("torque_multiplication", "Multiplicação de torque", 3),
    ("stage_count", "Nº de estágios", 0),
    ("warning_count", "Nº de alertas", 0),
]


def compare(items: list[tuple[TransmissionSet, TransmissionResult]]) -> dict:
    if len(items) < 2:
        raise GearTechValidationError("Selecione pelo menos dois conjuntos para comparar.")
    rows = []
    for ts, r in items:
        rows.append({"Conjunto": ts.name, "total_ratio": r.total_ratio, "output_speed_rpm": r.output_speed_rpm,
                     "output_torque_nm": r.output_torque_nm, "output_power_kw": r.output_power_kw,
                     "total_efficiency": r.total_efficiency, "total_power_loss_kw": r.total_power_loss_kw,
                     "torque_multiplication": r.torque_multiplication, "stage_count": len(r.stages),
                     "warning_count": len(r.warnings)})
    df = pd.DataFrame(rows).set_index("Conjunto")
    best = {
        "Maior rendimento": df["total_efficiency"].idxmax(),
        "Menor perda de potência": df["total_power_loss_kw"].idxmin(),
        "Maior torque de saída": df["output_torque_nm"].idxmax(),
        "Menos estágios": df["stage_count"].idxmin(),
    }
    names = list(df.index)
    chart_list = [
        charts.bar_chart(names, df["total_efficiency"] * 100, "Rendimento total", "η (%)", color=charts.PALETTE[2]),
        charts.bar_chart(names, df["output_torque_nm"], "Torque de saída", "N·m", color=charts.PALETTE[0]),
        charts.bar_chart(names, df["output_speed_rpm"], "Rotação de saída", "rpm", color=charts.PALETTE[1]),
        charts.bar_chart(names, df["total_power_loss_kw"], "Perda de potência", "kW",
                         color=charts.PALETTE[4], text_format=".3f"),
    ]
    table = df.rename(columns={key: label for key, label, _ in COMPARISON_METRICS}).T
    return {"df": df, "table": table, "best": best, "charts": chart_list, "names": names}


def comparison_csv(comparison: dict) -> bytes:
    return to_csv(comparison["table"].reset_index(names="Indicador"))


# --------------------------------------------------------------------------
# Funcionalidade 8: gráficos e relatórios
# --------------------------------------------------------------------------
def set_charts(result: TransmissionResult) -> list[str]:
    labels = [f"Eixo {s.index}" for s in result.shafts]
    loss_labels = ["Entrada"] + [f"Perda est. {s.index}" for s in result.stages] + ["Saída"]
    loss_values = [result.input_power_kw] + [-s.power_loss_kw for s in result.stages] + [result.output_power_kw]
    return [
        charts.dual_axis_chart(labels, ("Rotação", [s.speed_rpm for s in result.shafts], "Rotação (rpm)"),
                               ("Torque", [s.torque_nm for s in result.shafts], "Torque (N·m)"),
                               "Rotação e torque em cada eixo"),
        charts.waterfall_chart(loss_labels, loss_values, "Fluxo de potência e perdas por estágio", "kW"),
    ]


def sweep_charts(sweep: dict) -> list[str]:
    if sweep["variable"] == "rotacao":
        x, x_title = sweep["input_speed_rpm"], "Rotação do motor (rpm)"
    else:
        x, x_title = sweep["input_power_kw"], "Potência do motor (kW)"
    return [
        charts.line_chart(x, {"Torque de entrada": sweep["input_torque_nm"],
                              "Torque de saída": sweep["output_torque_nm"]},
                          "Torque × condição de operação", x_title, "Torque (N·m)", markers=False),
        charts.line_chart(x, {"Rotação de entrada": sweep["input_speed_rpm"],
                              "Rotação de saída": sweep["output_speed_rpm"]},
                          "Rotação × condição de operação", x_title, "Rotação (rpm)", markers=False),
    ]


def _fmt(v, d=2):
    return fmt_num(v, d, empty="-")


def set_report_pdf(ts: TransmissionSet, result: TransmissionResult, author: str = "") -> bytes:
    rep = PdfReport(f"Relatório de transmissão — {ts.name}", "GearTech · Módulo 3", author)
    if ts.application or ts.description:
        rep.paragraph(" · ".join(x for x in (ts.application, ts.description) if x))
    rep.heading("Resumo")
    rep.table([
        ["Grandeza", "Entrada", "Saída"],
        ["Potência (kW)", _fmt(result.input_power_kw, 3), _fmt(result.output_power_kw, 3)],
        ["Rotação (rpm)", _fmt(result.input_speed_rpm), _fmt(result.output_speed_rpm)],
        ["Torque (N·m)", _fmt(result.input_torque_nm), _fmt(result.output_torque_nm)],
    ], [6, 5, 5])
    rep.spacer()
    rep.paragraph(f"Relação total i = {_fmt(result.total_ratio, 4)} ({result.kind}); rendimento total "
                  f"η = {_fmt(result.total_efficiency * 100, 2)} %; perda total = "
                  f"{_fmt(result.total_power_loss_kw, 3)} kW; torque multiplicado "
                  f"{_fmt(result.torque_multiplication, 2)} vezes.")
    rep.heading("Estágios")
    rows = [["#", "Tipo", "Z1/d1", "Z2/d2", "i", "η", "n saída (rpm)", "T saída (N·m)", "Ft (N)"]]
    for s in result.stages:
        rows.append([s.index, s.type_label, _fmt(s.driver, 1), _fmt(s.driven, 1), _fmt(s.ratio, 3),
                     _fmt(s.efficiency, 3), _fmt(s.output_speed_rpm), _fmt(s.output_torque_nm),
                     _fmt(s.tangential_force_n, 0)])
    rep.table(rows, [0.7, 4.6, 1.4, 1.4, 1.3, 1.2, 2.2, 2.2, 1.6])
    rep.heading("Eixos")
    rows = [["Eixo", "Descrição", "Rotação (rpm)", "Torque (N·m)", "Potência (kW)", "Sentido"]]
    for s in result.shafts:
        rows.append([s.index, s.label, _fmt(s.speed_rpm), _fmt(s.torque_nm), _fmt(s.power_kw, 3), s.direction])
    rep.table(rows, [1.1, 4.4, 2.6, 2.6, 2.4, 3.5])
    rep.spacer()
    labels = [f"Eixo {s.index}" for s in result.shafts]
    rep.bar_chart(labels, {"Rotação (rpm)": [s.speed_rpm for s in result.shafts]}, "Rotação por eixo", "rpm")
    rep.bar_chart(labels, {"Torque (N·m)": [s.torque_nm for s in result.shafts]}, "Torque por eixo", "N·m")
    if result.warnings:
        rep.heading("Alertas de projeto")
        for w in result.warnings:
            rep.paragraph(f"! {w}", "warn")
    rep.heading("Fórmulas utilizadas")
    rep.paragraph("i = Z2/Z1 (ou d2/d1); n2 = n1/i; T = P·1000/ω com ω = 2·pi·n/60; P2 = P1·eta; "
                  "T2 = T1·i·eta; i_total = produto dos i; eta_total = produto dos eta; d = m·Z/cos(beta); "
                  "Ft = 2T/d; Fr = Ft·tan(20°)/cos(beta); Fa = Ft·tan(beta).", "small")
    return rep.build()


def comparison_report_pdf(comparison: dict, author: str = "") -> bytes:
    rep = PdfReport("Comparação de configurações de transmissão", "GearTech · Módulo 3", author)
    df = comparison["df"]
    names = comparison["names"]
    rows = [["Indicador"] + names]
    for key, label, dec in COMPARISON_METRICS:
        pct = key == "total_efficiency"
        values = df[key] * (100 if pct else 1)
        rows.append([label + (" (%)" if pct else "")] + [_fmt(v, 2 if pct else dec) for v in values])
    width = min(3.2, 12.5 / len(names))
    rep.table(rows, [4.5] + [width] * len(names))
    rep.heading("Destaques")
    for criterion, name in comparison["best"].items():
        rep.paragraph(f"{criterion}: {name}")
    rep.spacer()
    rep.bar_chart(names, {"Rendimento (%)": list(df["total_efficiency"] * 100)}, "Rendimento total", "%")
    rep.bar_chart(names, {"Torque de saída (N·m)": list(df["output_torque_nm"])}, "Torque de saída", "N·m")
    rep.bar_chart(names, {"Perda (kW)": list(df["total_power_loss_kw"])}, "Perda de potência", "kW")
    return rep.build()


# --------------------------------------------------------------------------
# Integração GearTech → MechCalc
# --------------------------------------------------------------------------
def transmission_loads(ts: TransmissionSet, result: TransmissionResult) -> list[TransmissionLoad]:
    """Converte o resultado em esforços por eixo (contrato compartilhado).

    O eixo k recebe o estágio k (elemento movido) e aciona o estágio k+1
    (elemento motor). Publica-se o maior esforço entre esses engrenamentos.
    """
    loads = []
    for shaft in result.shafts:
        touching = [s for s in result.stages if s.index in (shaft.index, shaft.index + 1)
                    and s.tangential_force_n is not None]
        worst = max(touching, key=lambda s: s.tangential_force_n, default=None)
        loads.append(TransmissionLoad(
            source_ref=ts.source_ref, set_name=ts.name, shaft_index=shaft.index, shaft_label=shaft.label,
            speed_rpm=shaft.speed_rpm, torque_nm=shaft.torque_nm, power_kw=shaft.power_kw,
            tangential_force_n=worst.tangential_force_n if worst else None,
            radial_force_n=worst.radial_force_n if worst else None,
            axial_force_n=worst.axial_force_n if worst else None,
        ))
    return loads


def publish_to_mechcalc(ts: TransmissionSet, user_id: int | None) -> int:
    count = integration.publish_transmission_loads(ts.organization_id, user_id, transmission_loads(ts, analyze(ts)))
    log_event(ts.organization_id, user_id, MODULE, "integração",
              f"Esforços de {count} eixos de '{ts.name}' enviados ao MechCalc.")
    return count


# --------------------------------------------------------------------------
# Painel
# --------------------------------------------------------------------------
def organization_summary(organization_id: int) -> dict:
    sets = list_sets(organization_id)
    published = {load.source_ref for load in integration.list_transmission_loads(organization_id)}
    return {
        "set_count": len(sets),
        "stage_count": sum(len(s.stages) for s in sets),
        "published_count": len(published),
        "quick_count": QuickCalculation.query.filter_by(organization_id=organization_id).count(),
        "latest": sets[:3],
    }
