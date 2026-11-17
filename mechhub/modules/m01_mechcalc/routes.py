from flask import flash, render_template, request
from flask_login import current_user, login_required

from ...shared import integration
from . import bp
from .calculations import ShaftCalcError, check_shaft


@bp.route("/", methods=["GET", "POST"])
@login_required
def index():
    org = current_user.organization_id
    loads = integration.list_transmission_loads(org)  # só o serviço compartilhado
    selected = None
    check = None
    values = {"load_id": request.values.get("load_id", ""), "diameter": request.form.get("diameter", ""),
              "allowable": request.form.get("allowable", "40")}
    if values["load_id"]:
        try:
            selected = integration.get_transmission_load(org, int(values["load_id"]))
        except ValueError:
            selected = None
    if request.method == "POST":
        if selected is None:
            flash("Escolha um eixo publicado pelo GearTech.", "danger")
        else:
            try:
                check = check_shaft(selected.torque_nm, values["diameter"].replace(",", "."),
                                    values["allowable"].replace(",", "."))
            except ShaftCalcError as exc:
                flash(str(exc), "danger")
    return render_template("mechcalc/index.html", loads=loads, selected=selected, check=check, values=values)
