"""Integração GearTech → MechCalc pelo serviço compartilhado."""
import pytest

from mechhub.core.models import Organization
from mechhub.extensions import db
from mechhub.modules.m01_mechcalc.calculations import ShaftCalcError, check_shaft, torsion_stress_mpa
from mechhub.modules.m03_geartech import services as svc
from mechhub.shared import integration
from mechhub.shared.contracts import TransmissionLoad


def demo_org():
    return Organization.query.filter_by(name="MechHub Demo").one()


def test_publicacao_gera_um_registro_por_eixo(ctx):
    org = demo_org()
    ts = next(s for s in svc.list_sets(org.id) if s.name.startswith("Betoneira"))
    count = svc.publish_to_mechcalc(ts, None)
    assert count == len(ts.stages) + 1
    loads = [load for load in integration.list_transmission_loads(org.id) if load.source_ref == ts.source_ref]
    assert len(loads) == count
    assert all(isinstance(load, TransmissionLoad) for load in loads)


def test_esforcos_batem_com_o_resultado(ctx):
    org = demo_org()
    ts = svc.list_sets(org.id)[0]
    result = svc.analyze(ts)
    loads = svc.transmission_loads(ts, result)
    assert loads[-1].torque_nm == pytest.approx(result.output_torque_nm)
    assert loads[0].speed_rpm == pytest.approx(ts.input_speed_rpm)


def test_republicar_substitui_e_nao_duplica(ctx):
    org = demo_org()
    ts = svc.list_sets(org.id)[0]
    svc.publish_to_mechcalc(ts, None)
    svc.publish_to_mechcalc(ts, None)
    loads = [load for load in integration.list_transmission_loads(org.id) if load.source_ref == ts.source_ref]
    assert len(loads) == len(ts.stages) + 1


def test_excluir_conjunto_retira_do_mechcalc(ctx):
    org = demo_org()
    ts = svc.list_sets(org.id)[0]
    ref = ts.source_ref
    svc.publish_to_mechcalc(ts, None)
    svc.delete_set(ts, None)
    assert not integration.is_published(org.id, ref)


def test_outra_organizacao_nao_ve_os_esforcos(ctx):
    other = Organization(name="Concorrente")
    db.session.add(other)
    db.session.commit()
    assert integration.list_transmission_loads(other.id) == []
    some_load = integration.list_transmission_loads(demo_org().id)[0]
    assert integration.get_transmission_load(other.id, some_load.id) is None


def test_integracao_rejeita_dados_invalidos(ctx):
    bad = TransmissionLoad(source_ref="x", set_name="x", shaft_index=0, shaft_label="x",
                           speed_rpm=0, torque_nm=10, power_kw=1)
    with pytest.raises(integration.IntegrationError):
        integration.publish_transmission_loads(demo_org().id, None, [bad])
    with pytest.raises(integration.IntegrationError):
        integration.publish_transmission_loads(demo_org().id, None, [])


def test_mechcalc_verifica_eixo_com_torque_do_geartech(ctx):
    load = integration.list_transmission_loads(demo_org().id)[-1]
    res = check_shaft(load.torque_nm, 50, 40)
    assert res["tau_mpa"] == pytest.approx(torsion_stress_mpa(load.torque_nm, 50))
    assert res["d_min_mm"] > 0
    assert res["approved"] == (res["tau_mpa"] <= 40)


def test_formula_de_torcao():
    # T = 100 N·m, d = 20 mm → τ = 16·100000/(π·8000) ≈ 63,66 MPa
    assert torsion_stress_mpa(100, 20) == pytest.approx(63.662, rel=1e-4)
    with pytest.raises(ShaftCalcError):
        torsion_stress_mpa(100, 0)
