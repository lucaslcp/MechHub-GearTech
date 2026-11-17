"""Persistência, comparação e relatórios (funcionalidades 1, 7 e 8)."""
import pytest
from werkzeug.datastructures import MultiDict

from mechhub.core.models import Organization, User
from mechhub.core.seed import DEMO_SETS, demo_form
from mechhub.extensions import db
from mechhub.modules.m03_geartech import services as svc
from mechhub.modules.m03_geartech.models import QuickCalculation, ResultSnapshot, Stage, TransmissionSet


def demo_org():
    return Organization.query.filter_by(name="MechHub Demo").one()


def test_parse_number_formatos_brasileiros():
    assert svc.parse_number("1,5", "x") == 1.5
    assert svc.parse_number("1.234,5", "x") == 1234.5
    assert svc.parse_number("2.5", "x") == 2.5
    assert svc.parse_number("", "x", required=False) is None
    with pytest.raises(svc.GearTechValidationError):
        svc.parse_number("dez", "x")
    with pytest.raises(svc.GearTechValidationError):
        svc.parse_number("", "x")


def test_cadastro_grava_conjunto_estagios_e_resultado(ctx):
    org = demo_org()
    data = svc.parse_set_form(demo_form(DEMO_SETS[0] | {"name": "Novo redutor"}))
    ts = svc.create_set(org.id, None, data)
    saved = db.session.get(TransmissionSet, ts.id)
    assert saved.name == "Novo redutor"
    assert [s.position for s in saved.stages] == [1, 2]
    assert saved.snapshots[0].total_ratio == pytest.approx(16)


def test_edicao_substitui_estagios_e_cria_novo_snapshot(ctx):
    org = demo_org()
    ts = svc.list_sets(org.id)[-1]
    snaps_before = len(ts.snapshots)
    form = demo_form(DEMO_SETS[1] | {"name": "Editado"})
    svc.update_set(ts, None, svc.parse_set_form(form))
    assert ts.name == "Editado"
    assert len(ts.stages) == 2
    assert len(ts.snapshots) == snaps_before + 1
    assert Stage.query.filter_by(set_id=ts.id).count() == 2


def test_exclusao_remove_estagios_e_snapshots(ctx):
    org = demo_org()
    ts = svc.list_sets(org.id)[0]
    set_id = ts.id
    svc.delete_set(ts, None)
    assert db.session.get(TransmissionSet, set_id) is None
    assert Stage.query.filter_by(set_id=set_id).count() == 0
    assert ResultSnapshot.query.filter_by(set_id=set_id).count() == 0


def test_formulario_invalido_lista_todos_os_erros(ctx):
    form = MultiDict({"name": "x", "input_power_kw": "abc", "input_speed_rpm": ""})
    form.add("stage_type", "engrenagem_reta")
    form.add("driver", "")
    form.add("driven", "40")
    with pytest.raises(svc.GearTechValidationError) as exc:
        svc.parse_set_form(form)
    assert len(exc.value.messages) >= 4


def test_rendimento_digitado_em_porcentagem(ctx):
    form = demo_form({"name": "Teste %", "input_power_kw": "1", "input_speed_rpm": "1000",
                      "stages": [("polia_correia", "100", "200", "95", "", "", "", "")]})
    data = svc.parse_set_form(form)
    assert data.stages[0].efficiency == pytest.approx(0.95)


def test_isolamento_entre_organizacoes(ctx):
    other = Organization(name="Outra empresa")
    db.session.add(other)
    db.session.commit()
    ts = svc.list_sets(demo_org().id)[0]
    assert svc.get_set(other.id, ts.id) is None
    assert svc.list_sets(other.id) == []


def test_calculadora_rapida_salva_no_banco(ctx):
    org = demo_org()
    form = MultiDict({"power": "7,5", "speed": "1750", "ratio": "16", "efficiency": "0,9604"})
    rec = svc.run_quick_calc("torque", form, org.id, None)
    assert rec.result["T1_Nm"] == pytest.approx(40.9256, rel=1e-4)
    assert QuickCalculation.query.count() == 1


def test_calculadora_relacao_com_varios_pares(ctx):
    form = MultiDict([("driver", "19"), ("driven", "76"), ("driver", "21"), ("driven", "84"),
                      ("driver", ""), ("driven", "")])
    rec = svc.run_quick_calc("relacao", form, demo_org().id, None)
    assert rec.result["relacao_total"] == pytest.approx(16)


def test_calculadora_com_erro(ctx):
    with pytest.raises(svc.GearTechValidationError):
        svc.run_quick_calc("rotacao", MultiDict({"speed": "1000", "ratio": "0"}), demo_org().id, None)


def test_comparacao_indica_melhores(ctx):
    items = [(ts, svc.analyze(ts)) for ts in svc.list_sets(demo_org().id)]
    cmp = svc.compare(items)
    assert len(cmp["names"]) == 4
    assert cmp["best"]["Menor perda de potência"] in cmp["names"]
    assert cmp["df"]["total_efficiency"].max() <= 1
    assert len(cmp["charts"]) == 4


def test_comparacao_precisa_de_dois(ctx):
    ts = svc.list_sets(demo_org().id)[0]
    with pytest.raises(svc.GearTechValidationError):
        svc.compare([(ts, svc.analyze(ts))])


def test_relatorio_pdf_e_csv(ctx):
    ts = svc.list_sets(demo_org().id)[0]
    result = svc.analyze(ts)
    pdf = svc.set_report_pdf(ts, result, "Teste")
    assert pdf.startswith(b"%PDF")
    csv = svc.set_csv(ts, result).decode("utf-8-sig")
    assert "Relação i" in csv and ";" in csv


def test_usuario_demo_existe(ctx):
    user = User.query.filter_by(email="demo@mechhub.local").one()
    assert user.check_password("mechhub123")
    assert not user.check_password("errada")
