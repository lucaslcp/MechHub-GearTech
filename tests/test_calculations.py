"""Testes das fórmulas do GearTech (funcionalidades 2 a 6)."""
import math

import pytest

from mechhub.modules.m03_geartech import calculations as c
from mechhub.modules.m03_geartech.calculations import StageInput, TransmissionError

approx = pytest.approx


# ---- Funcionalidade 2: relação de transmissão --------------------------------
def test_relacao_de_um_par():
    assert c.transmission_ratio(20, 60) == 3
    assert c.transmission_ratio(100, 250) == 2.5


def test_relacao_multiplicadora_menor_que_um():
    assert c.transmission_ratio(60, 20) == approx(1 / 3)


def test_relacao_total_e_o_produto():
    assert c.total_ratio([4, 4]) == 16
    assert c.total_ratio([2.5, 5]) == 12.5


@pytest.mark.parametrize("driver,driven", [(0, 10), (10, 0), (-5, 10), ("abc", 10), (None, 10)])
def test_relacao_rejeita_valores_invalidos(driver, driven):
    with pytest.raises(TransmissionError):
        c.transmission_ratio(driver, driven)


def test_relacao_total_vazia():
    with pytest.raises(TransmissionError):
        c.total_ratio([])


# ---- Funcionalidade 3: rotação -----------------------------------------------
def test_rotacao_de_saida():
    assert c.output_speed(1750, 4) == 437.5


def test_velocidade_angular():
    assert c.angular_speed(60) == approx(2 * math.pi)


# ---- Funcionalidade 4: torque ------------------------------------------------
def test_torque_pela_potencia():
    # T = 9549,3·P/n  →  7,5 kW a 1750 rpm ≈ 40,93 N·m
    assert c.torque_from_power(7.5, 1750) == approx(40.9256, rel=1e-4)


def test_torque_de_saida_com_rendimento():
    assert c.output_torque(100, 3, 0.95) == approx(285)


# ---- Funcionalidade 5: potência ----------------------------------------------
def test_potencia_de_saida():
    assert c.output_power(10, 0.9) == approx(9)


def test_potencia_pelo_torque_e_inverso_do_torque():
    t = c.torque_from_power(5, 1200)
    assert c.power_from_torque(t, 1200) == approx(5)


@pytest.mark.parametrize("eta", [0, -0.1, 1.2])
def test_rendimento_fora_da_faixa(eta):
    with pytest.raises(TransmissionError):
        c.output_power(10, eta)


# ---- Geometria e esforços ----------------------------------------------------
def test_diametro_primitivo_reto_e_helicoidal():
    assert c.pitch_diameter(2, 20) == 40
    assert c.pitch_diameter(3, 19, 15) == approx(3 * 19 / math.cos(math.radians(15)))


def test_forcas_no_dente():
    ft = c.tangential_force(50, 40)  # 2·50/0,040
    assert ft == approx(2500)
    assert c.radial_force(ft) == approx(2500 * math.tan(math.radians(20)))
    assert c.axial_force(ft, 0) == 0


def test_diametro_roda_de_corrente():
    assert c.sprocket_pitch_diameter(15.875, 12) == approx(61.34, rel=1e-3)


def test_numero_minimo_de_dentes():
    assert c.minimum_teeth_no_undercut() == approx(17.1, rel=1e-2)


# ---- Funcionalidade 6: múltiplos estágios ------------------------------------
def two_stage():
    return [StageInput("engrenagem_helicoidal", 19, 76, 0.98, 3, None, 15),
            StageInput("engrenagem_helicoidal", 21, 84, 0.98, 4, None, 15)]


def test_simulacao_dois_estagios():
    r = c.simulate_transmission(7.5, 1750, two_stage())
    assert r.total_ratio == approx(16)
    assert r.output_speed_rpm == approx(109.375)
    assert r.total_efficiency == approx(0.98 ** 2)
    assert r.output_power_kw == approx(7.5 * 0.98 ** 2)
    assert r.output_torque_nm == approx(c.torque_from_power(7.5, 1750) * 16 * 0.98 ** 2)
    assert r.kind == "redutor"
    assert len(r.shafts) == 3


def test_conservacao_de_energia_em_cada_eixo():
    r = c.simulate_transmission(7.5, 1750, two_stage())
    for shaft in r.shafts:
        assert c.power_from_torque(shaft.torque_nm, shaft.speed_rpm) == approx(shaft.power_kw)
    assert r.total_power_loss_kw == approx(sum(s.power_loss_kw for s in r.stages))


def test_sentido_de_rotacao():
    r = c.simulate_transmission(1, 1000, [StageInput("engrenagem_reta", 20, 40),
                                          StageInput("polia_correia", 100, 200),
                                          StageInput("engrenagem_reta", 20, 40)])
    assert [s.direction for s in r.shafts] == ["horário", "anti-horário", "anti-horário", "horário"]


def test_rendimento_padrao_quando_vazio():
    r = c.simulate_transmission(1, 1000, [StageInput("polia_correia", 100, 200)])
    assert r.stages[0].efficiency == 0.95


def test_alerta_de_interferencia():
    r = c.simulate_transmission(1, 1000, [StageInput("engrenagem_reta", 12, 48, module_mm=2)])
    assert any("interferência" in w for w in r.warnings)


def test_alerta_relacao_alta():
    r = c.simulate_transmission(1, 1000, [StageInput("engrenagem_reta", 17, 170, module_mm=2)])
    assert any("acima da recomendada" in w for w in r.warnings)


def test_simulacao_sem_estagios():
    with pytest.raises(TransmissionError):
        c.simulate_transmission(1, 1000, [])


def test_tipo_desconhecido():
    with pytest.raises(TransmissionError, match="desconhecido"):
        c.simulate_transmission(1, 1000, [StageInput("magica", 1, 2)])


def test_dentes_fracionarios():
    with pytest.raises(TransmissionError, match="inteiro"):
        c.simulate_transmission(1, 1000, [StageInput("engrenagem_reta", 20.5, 40)])


def test_varredura_de_rotacao():
    sweep = c.operating_sweep(7.5, 1750, two_stage(), "rotacao", 500, 2000, 4)
    assert sweep["x"] == approx([500, 1000, 1500, 2000])
    assert sweep["output_speed_rpm"][0] == approx(500 / 16)
    # potência constante: torque cai com a rotação
    assert sweep["output_torque_nm"][0] > sweep["output_torque_nm"][-1]


def test_varredura_intervalo_invalido():
    with pytest.raises(TransmissionError):
        c.operating_sweep(7.5, 1750, two_stage(), "rotacao", 2000, 500)
