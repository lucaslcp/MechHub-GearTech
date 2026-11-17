"""GearTech — rotas (telas) do módulo."""
import re

from flask import Response, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ...shared import integration
from ...shared.history import recent_events
from . import bp
from . import calculations as calc
from . import services as svc
from .calculations import STAGE_TYPES

EXAMPLE_FORM = {
    "name": "", "application": "", "description": "", "input_power_kw": "", "input_speed_rpm": "",
    "stages": [{"stage_type": "engrenagem_reta", "driver": "", "driven": "", "efficiency": "",
                "module_mm": "", "pitch_mm": "", "helix_angle_deg": "", "label": ""}],
}


def _org() -> int:
    return current_user.organization_id


def _get_or_404(set_id: int):
    ts = svc.get_set(_org(), set_id)
    if ts is None:
        abort(404)
    return ts


def _file(data: bytes, filename: str, mimetype: str) -> Response:
    return Response(data, mimetype=mimetype,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


def _slug(text: str) -> str:
    import re
    import unicodedata

    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower() or "conjunto"


@bp.route("/")
@login_required
def index():
    sets = svc.list_sets(_org())
    rows = []
    for ts in sets:
        try:
            rows.append((ts, svc.analyze(ts)))
        except calc.TransmissionError:
            rows.append((ts, None))
    published = {load.source_ref for load in integration.list_transmission_loads(_org())}
    return render_template("geartech/index.html", rows=rows, published=published,
                           events=recent_events(_org(), module=svc.MODULE, limit=10))


def _render_form(form_data, ts=None, preview=None, status=200, field_errors=None, stage_errors=None):
    return render_template("geartech/form.html", form=form_data, ts=ts, stage_types=STAGE_TYPES,
                           preview=preview, charts=svc.set_charts(preview) if preview else [],
                           field_errors=field_errors or {}, stage_errors=stage_errors or {}), status


def _place_errors(exc):
    """Separa os erros: ao lado do campo, no bloco do estágio ou no topo da página.

    Princípio da proximidade: a orientação aparece perto de onde se corrige.
    """
    field_errors = {}
    for key, msg in exc.fields.items():
        text = msg.split(": ", 1)[-1]
        field_errors[key] = text[:1].upper() + text[1:]
    stage_errors: dict[int, list[str]] = {}
    general = []
    for msg in exc.messages:
        if msg in exc.fields.values():
            continue
        match = re.match(r"Estágio (\d+)", msg)
        if match:
            stage_errors.setdefault(int(match.group(1)), []).append(msg)
        else:
            general.append(msg)
    placed = len(field_errors) + sum(len(v) for v in stage_errors.values())
    if placed:
        flash(f"Não foi possível continuar: corrija {placed} campo(s) destacado(s) em vermelho.", "danger")
    for msg in general:
        flash(msg, "danger")
    return field_errors, stage_errors


def _handle_form(ts=None):
    action = request.form.get("action", "save")
    try:
        data = svc.parse_set_form(request.form)
    except svc.GearTechValidationError as exc:
        field_errors, stage_errors = _place_errors(exc)
        return _render_form(svc.form_to_dict(request.form), ts, status=400,
                            field_errors=field_errors, stage_errors=stage_errors)
    if action == "preview":
        # Funcionalidade 6: simula sem gravar.
        return _render_form(svc.form_to_dict(request.form), ts, preview=svc.simulate(data))
    if ts is None:
        ts = svc.create_set(_org(), current_user.id, data)
        flash(f"Conjunto '{ts.name}' cadastrado.", "success")
    else:
        svc.update_set(ts, current_user.id, data)
        flash("Alterações salvas e resultados recalculados.", "success")
    return redirect(url_for("geartech.detail", set_id=ts.id))


@bp.route("/conjuntos/novo", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        return _handle_form()
    return _render_form(EXAMPLE_FORM)


@bp.route("/conjuntos/<int:set_id>/editar", methods=["GET", "POST"])
@login_required
def edit(set_id: int):
    ts = _get_or_404(set_id)
    if request.method == "POST":
        return _handle_form(ts)
    return _render_form(svc.set_to_form(ts), ts)


@bp.route("/conjuntos/<int:set_id>/excluir", methods=["POST"])
@login_required
def delete(set_id: int):
    ts = _get_or_404(set_id)
    name = ts.name
    svc.delete_set(ts, current_user.id)
    flash(f"Conjunto '{name}' excluído.", "info")
    return redirect(url_for("geartech.index"))


@bp.route("/conjuntos/<int:set_id>")
@login_required
def detail(set_id: int):
    ts = _get_or_404(set_id)
    result = svc.analyze(ts)
    return render_template("geartech/detail.html", ts=ts, result=result, charts=svc.set_charts(result),
                           loads=svc.transmission_loads(ts, result),
                           published=integration.is_published(_org(), ts.source_ref))


@bp.route("/conjuntos/<int:set_id>/simular", methods=["GET", "POST"])
@login_required
def simulate(set_id: int):
    ts = _get_or_404(set_id)
    result = svc.analyze(ts)
    params = {"variable": request.values.get("variable", "rotacao"), "start": request.values.get("start", ""),
              "stop": request.values.get("stop", ""), "points": request.values.get("points", "25")}
    sweep, sweep_charts = None, []
    try:
        start = svc.parse_number(params["start"], "Valor inicial", required=False)
        stop = svc.parse_number(params["stop"], "Valor final", required=False)
        points = int(svc.parse_number(params["points"], "Pontos") or 25)
        sweep = calc.operating_sweep(ts.input_power_kw, ts.input_speed_rpm, svc.stage_inputs(ts),
                                     params["variable"], start, stop, points)
        sweep_charts = svc.sweep_charts(sweep)
    except (svc.GearTechValidationError, calc.TransmissionError) as exc:
        flash(str(exc), "danger")
    return render_template("geartech/simulate.html", ts=ts, result=result, params=params, sweep=sweep,
                           charts=sweep_charts)


@bp.route("/calculadoras", methods=["GET", "POST"])
@login_required
def calculators():
    active = request.values.get("kind", "relacao")
    record = None
    if request.method == "POST":
        try:
            record = svc.run_quick_calc(active, request.form, _org(), current_user.id)
            flash("Cálculo realizado e salvo no histórico.", "success")
        except svc.GearTechValidationError as exc:
            for msg in exc.messages:
                flash(msg, "danger")
    return render_template("geartech/calculators.html", active=active, record=record, calcs=svc.QUICK_CALCS,
                           history=svc.recent_quick_calcs(_org()), values=request.form)


def _comparison_items():
    ids = request.values.getlist("ids", type=int)
    items = []
    for set_id in dict.fromkeys(ids):
        ts = svc.get_set(_org(), set_id)
        if ts is not None:
            items.append((ts, svc.analyze(ts)))
    return ids, items


@bp.route("/comparar")
@login_required
def compare():
    ids, items = _comparison_items()
    comparison = None
    if ids:
        try:
            comparison = svc.compare(items)
        except svc.GearTechValidationError as exc:
            flash(str(exc), "warning")
    return render_template("geartech/compare.html", sets=svc.list_sets(_org()), selected=set(ids), ids=ids,
                           comparison=comparison, metrics=svc.COMPARISON_METRICS)


@bp.route("/comparar/relatorio.<fmt>")
@login_required
def compare_export(fmt: str):
    _ids, items = _comparison_items()
    try:
        comparison = svc.compare(items)
    except svc.GearTechValidationError as exc:
        flash(str(exc), "warning")
        return redirect(url_for("geartech.compare"))
    if fmt == "pdf":
        return _file(svc.comparison_report_pdf(comparison, current_user.name), "comparacao-geartech.pdf",
                     "application/pdf")
    if fmt == "csv":
        return _file(svc.comparison_csv(comparison), "comparacao-geartech.csv", "text/csv")
    abort(404)


@bp.route("/conjuntos/<int:set_id>/relatorio.pdf")
@login_required
def report_pdf(set_id: int):
    ts = _get_or_404(set_id)
    pdf = svc.set_report_pdf(ts, svc.analyze(ts), current_user.name)
    return _file(pdf, f"geartech-{_slug(ts.name)}.pdf", "application/pdf")


@bp.route("/conjuntos/<int:set_id>/resultados.csv")
@login_required
def report_csv(set_id: int):
    ts = _get_or_404(set_id)
    return _file(svc.set_csv(ts, svc.analyze(ts)), f"geartech-{_slug(ts.name)}.csv", "text/csv")


@bp.route("/conjuntos/<int:set_id>/publicar", methods=["POST"])
@login_required
def publish(set_id: int):
    ts = _get_or_404(set_id)
    try:
        count = svc.publish_to_mechcalc(ts, current_user.id)
        flash(f"Esforços de {count} eixos enviados ao MechCalc.", "success")
    except integration.IntegrationError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("geartech.detail", set_id=ts.id))
