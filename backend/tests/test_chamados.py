"""Testes dos chamados — a triagem da IA é sempre simulada (mock)."""

CHAMADO_EXEMPLO = {"descricao": "Minha impressora parou de imprimir e aparece um erro de driver."}


def test_abrir_chamado_devolve_triagem_da_ia(cliente, auth, triagem_mockada):
    resposta = cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["solicitante"] == "Ana Souza"
    assert corpo["categoria"] == triagem_mockada["categoria"]
    assert corpo["prioridade"] == triagem_mockada["prioridade"]
    assert corpo["resposta_sugerida"] == triagem_mockada["resposta_sugerida"]
    assert corpo["status"] == "Aberto"


def test_abrir_chamado_sem_login_retorna_401(cliente, triagem_mockada):
    resposta = cliente.post("/chamados", json=CHAMADO_EXEMPLO)
    assert resposta.status_code == 401


def test_colaborador_ve_somente_os_proprios_chamados(cliente, auth, auth_tecnico, triagem_mockada):
    cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    cliente.post("/chamados", json={"descricao": "Preciso de acesso ao sistema acadêmico."}, headers=auth_tecnico)

    resposta = cliente.get("/chamados", headers=auth)
    chamados = resposta.json()
    assert len(chamados) == 1
    assert chamados[0]["solicitante"] == "Ana Souza"


def test_tecnico_ve_a_fila_inteira(cliente, auth, auth_tecnico, triagem_mockada):
    cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    cliente.post("/chamados", json={"descricao": "Preciso de acesso ao sistema acadêmico."}, headers=auth_tecnico)

    resposta = cliente.get("/chamados", headers=auth_tecnico)
    chamados = resposta.json()
    assert len(chamados) == 2
    assert chamados[0]["solicitante"] == "Carlos Lima"  # mais recente primeiro
    assert chamados[1]["solicitante"] == "Ana Souza"


def test_admin_tambem_ve_a_fila_inteira(cliente, auth, auth_admin, triagem_mockada):
    cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    resposta = cliente.get("/chamados", headers=auth_admin)
    chamados = resposta.json()
    assert len(chamados) == 1
    assert chamados[0]["solicitante"] == "Ana Souza"


def test_descricao_muito_curta_retorna_422(cliente, auth, triagem_mockada):
    resposta = cliente.post("/chamados", json={"descricao": "curta"}, headers=auth)
    assert resposta.status_code == 422


def test_falha_na_ia_retorna_502(cliente, auth, monkeypatch):
    def ia_quebrada(descricao):
        raise RuntimeError("API da IA fora do ar")

    monkeypatch.setattr("app.ia.triar_chamado", ia_quebrada)
    resposta = cliente.post("/chamados", json=CHAMADO_EXEMPLO, headers=auth)
    assert resposta.status_code == 502
