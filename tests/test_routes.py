"""Telas, autenticação e tratamento de erros."""
from werkzeug.datastructures import MultiDict

from mechhub.core.seed import DEMO_SETS, demo_form


def test_paginas_exigem_login(client):
    for url in ("/", "/geartech/", "/geartech/conjuntos/1", "/mechcalc/"):
        resp = client.get(url)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


def test_login_com_senha_errada(client):
    resp = client.post("/login", data={"email": "demo@mechhub.local", "password": "x"})
    assert resp.status_code == 200
    assert "incorretos" in resp.get_data(as_text=True)


def test_login_nao_redireciona_para_fora(client):
    resp = client.post("/login?next=https://site-malicioso.com",
                       data={"email": "demo@mechhub.local", "password": "mechhub123"})
    assert resp.headers["Location"] == "/"


def test_cadastro_cria_organizacao(client):
    resp = client.post("/cadastro", data={"name": "Ana", "email": "ana@teste.com", "password": "123456",
                                          "organization": "Oficina da Ana"}, follow_redirects=True)
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Oficina da Ana" in html
    # organização nova começa sem conjuntos de outras empresas
    assert "Redutor de esteira" not in client.get("/geartech/").get_data(as_text=True)


def test_cadastro_invalido(client):
    resp = client.post("/cadastro", data={"name": "A", "email": "naoemail", "password": "1", "organization": ""})
    assert resp.status_code == 400


def test_paginas_principais(logged):
    for url in ("/", "/geartech/", "/geartech/conjuntos/1", "/geartech/conjuntos/novo",
                "/geartech/conjuntos/1/editar", "/geartech/conjuntos/1/simular", "/geartech/calculadoras",
                "/geartech/comparar", "/geartech/comparar?ids=1&ids=2", "/mechcalc/", "/modulo/vibrasense"):
        assert logged.get(url).status_code == 200, url


def test_criar_conjunto_pela_tela(logged):
    form = demo_form(DEMO_SETS[2] | {"name": "Criado pela tela"})
    resp = logged.post("/geartech/conjuntos/novo", data=form, follow_redirects=True)
    assert resp.status_code == 200
    assert "Criado pela tela" in resp.get_data(as_text=True)


def test_previa_nao_salva(logged):
    form = demo_form(DEMO_SETS[2] | {"name": "Só prévia"})
    form["action"] = "preview"
    resp = logged.post("/geartech/conjuntos/novo", data=form)
    assert resp.status_code == 200
    assert "Pré-visualização" in resp.get_data(as_text=True)
    assert "Só prévia" not in logged.get("/geartech/").get_data(as_text=True)


def test_formulario_com_erro_mostra_mensagem(logged):
    form = MultiDict({"name": "Erro", "input_power_kw": "-1", "input_speed_rpm": "1000",
                      "stage_type": "engrenagem_reta", "driver": "20", "driven": "40"})
    resp = logged.post("/geartech/conjuntos/novo", data=form)
    assert resp.status_code == 400
    assert "maior que zero" in resp.get_data(as_text=True)


def test_erro_aparece_ao_lado_do_campo(logged):
    """Princípio da proximidade: o erro fica no campo/estágio que precisa ser corrigido."""
    form = MultiDict([("name", "Conjunto com erro"), ("input_power_kw", "abc"), ("input_speed_rpm", "1000"),
                      ("stage_type", "engrenagem_reta"), ("driver", "20"), ("driven", "40"),
                      ("stage_type", "corrente"), ("driver", ""), ("driven", "38")])
    resp = logged.post("/geartech/conjuntos/novo", data=form)
    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert "corrija 2 campo(s) destacado(s)" in html
    assert "&#39;abc&#39; não é um número válido" in html          # junto da potência
    assert 'id="estagio-form-2"' in html and "stage-row is-invalid" in html
    assert html.count('class="invalid-feedback"') == 2


def test_alerta_fica_no_estagio(logged):
    """O alerta de interferência aparece na linha do estágio, com o atalho para corrigir."""
    html = logged.get("/geartech/conjuntos/4").get_data(as_text=True)  # sem-fim + par 14/28
    assert "stage-alert-row" in html
    assert "Corrigir este estágio" in html and "/editar#estagio-form-2" in html


def test_excluir_pela_tela(logged):
    resp = logged.post("/geartech/conjuntos/4/excluir", follow_redirects=True)
    assert resp.status_code == 200
    assert logged.get("/geartech/conjuntos/4").status_code == 404


def test_conjunto_inexistente_404(logged):
    assert logged.get("/geartech/conjuntos/999").status_code == 404
    assert logged.post("/geartech/conjuntos/999/excluir").status_code == 404


def test_downloads(logged):
    pdf = logged.get("/geartech/conjuntos/1/relatorio.pdf")
    assert pdf.mimetype == "application/pdf" and pdf.data.startswith(b"%PDF")
    csv = logged.get("/geartech/conjuntos/1/resultados.csv")
    assert csv.mimetype == "text/csv"
    cmp_pdf = logged.get("/geartech/comparar/relatorio.pdf?ids=1&ids=2")
    assert cmp_pdf.data.startswith(b"%PDF")


def test_calculadora_pela_tela(logged):
    resp = logged.post("/geartech/calculadoras?kind=rotacao", data={"speed": "1750", "ratio": "4"})
    assert "437,50 rpm" in resp.get_data(as_text=True)


def test_simulacao_com_parametros_invalidos(logged):
    resp = logged.get("/geartech/conjuntos/1/simular?start=2000&stop=100")
    assert resp.status_code == 200
    assert "maior que o inicial" in resp.get_data(as_text=True)


def test_publicar_e_verificar_no_mechcalc(logged):
    resp = logged.post("/geartech/conjuntos/2/publicar", follow_redirects=True)
    assert "enviados ao MechCalc" in resp.get_data(as_text=True)
    page = logged.get("/mechcalc/").get_data(as_text=True)
    assert "Betoneira" in page
