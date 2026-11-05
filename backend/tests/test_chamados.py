"""Testes dos chamados — o usuário classifica; a orientação da IA é sempre simulada (mock)."""

CHAMADO_EXEMPLO = {
    "titulo": "Impressora não imprime",
    "descricao": "Minha impressora parou de imprimir e aparece um erro de driver.",
    "categoria": "Hardware",
    "prioridade": "Média",
}


def test_opcoes_de_classificacao(cliente, auth):
    resposta = cliente.get("/opcoes", headers=auth)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert "Hardware" in corpo["categorias"]
    assert corpo["prioridades"] == ["Baixa", "Média", "Alta"]


def test_abrir_chamado_guarda_classificacao_e_orientacao_da_ia(cliente, auth, orientacao_mockada):
    resposta = cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["solicitante"] == "Ana Souza"
    assert corpo["titulo"] == CHAMADO_EXEMPLO["titulo"]
    assert corpo["categoria"] == CHAMADO_EXEMPLO["categoria"]
    assert corpo["prioridade"] == CHAMADO_EXEMPLO["prioridade"]
    assert corpo["orientacao"] == orientacao_mockada
    assert corpo["status"] == "Aberto"


def test_abrir_chamado_sem_login_retorna_401(cliente, orientacao_mockada):
    resposta = cliente.post("/chamados", json=CHAMADO_EXEMPLO)
    assert resposta.status_code == 401


def test_usuario_ve_somente_os_proprios_chamados(cliente, auth, auth_tecnico, orientacao_mockada):
    cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    cliente.post(
        "/chamados",
        json={**CHAMADO_EXEMPLO, "titulo": "Acesso ao sistema acadêmico", "categoria": "Acesso e Senhas"},
        headers=auth_tecnico,
    )

    resposta = cliente.get("/chamados", headers=auth)
    chamados = resposta.json()
    assert len(chamados) == 1
    assert chamados[0]["solicitante"] == "Ana Souza"


def test_tecnico_ve_a_fila_inteira(cliente, auth, auth_tecnico, orientacao_mockada):
    cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    cliente.post(
        "/chamados",
        json={**CHAMADO_EXEMPLO, "titulo": "Acesso ao sistema acadêmico", "categoria": "Acesso e Senhas"},
        headers=auth_tecnico,
    )

    resposta = cliente.get("/chamados", headers=auth_tecnico)
    chamados = resposta.json()
    assert len(chamados) == 2
    assert chamados[0]["solicitante"] == "Carlos Lima"  # mais recente primeiro
    assert chamados[1]["solicitante"] == "Ana Souza"


def test_admin_tambem_ve_a_fila_inteira(cliente, auth, auth_admin, orientacao_mockada):
    cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    resposta = cliente.get("/chamados", headers=auth_admin)
    chamados = resposta.json()
    assert len(chamados) == 1
    assert chamados[0]["solicitante"] == "Ana Souza"


def test_titulo_muito_curto_retorna_422(cliente, auth, orientacao_mockada):
    resposta = cliente.post("/chamados", json={**CHAMADO_EXEMPLO, "titulo": "oi"}, headers=auth)
    assert resposta.status_code == 422


def test_categoria_fora_do_catalogo_retorna_422(cliente, auth, orientacao_mockada):
    resposta = cliente.post("/chamados", json={**CHAMADO_EXEMPLO, "categoria": "Jardinagem"}, headers=auth)
    assert resposta.status_code == 422


def test_prioridade_invalida_retorna_422(cliente, auth, orientacao_mockada):
    resposta = cliente.post(
        "/chamados", json={**CHAMADO_EXEMPLO, "prioridade": "Urgentíssima"}, headers=auth
    )
    assert resposta.status_code == 422


def test_falha_na_ia_retorna_502(cliente, auth, monkeypatch):
    def ia_quebrada(*dados):
        raise RuntimeError("API da IA fora do ar")

    monkeypatch.setattr("app.ia.gerar_orientacao", ia_quebrada)
    resposta = cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    assert resposta.status_code == 502
