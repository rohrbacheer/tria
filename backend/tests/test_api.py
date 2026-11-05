"""Testes dos endpoints da API — a IA é sempre simulada (mock), nunca chamada de verdade."""

PERGUNTA_EXEMPLO = {"pergunta": "Minha internet está muito lenta, o que posso fazer?"}


def test_saude_retorna_ok(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_login_valido_abre_sessao(cliente):
    resposta = cliente.post("/login", json={"login": "ana.souza", "senha": "puc123"})
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["token"]
    assert corpo["nome"] == "Ana Souza"
    assert corpo["perfil"] == "COLABORADOR"


def test_login_com_senha_errada_retorna_401(cliente):
    resposta = cliente.post("/login", json={"login": "ana.souza", "senha": "errada"})
    assert resposta.status_code == 401


def test_perguntar_sem_login_retorna_401(cliente, ia_mockada):
    resposta = cliente.post("/perguntar", json=PERGUNTA_EXEMPLO)
    assert resposta.status_code == 401


def test_token_invalido_retorna_401(cliente):
    resposta = cliente.get("/historico", headers={"Authorization": "Bearer token-falso"})
    assert resposta.status_code == 401


def test_perguntar_devolve_resposta_da_ia(cliente, auth, ia_mockada):
    resposta = cliente.post("/perguntar", json=PERGUNTA_EXEMPLO, headers=auth)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["pergunta"] == PERGUNTA_EXEMPLO["pergunta"]
    assert corpo["resposta"] == ia_mockada["resposta"]
    assert corpo["categoria"] == ia_mockada["categoria"]
    assert corpo["criado_em"]


def test_historico_em_ordem_cronologica(cliente, auth, ia_mockada):
    cliente.post("/perguntar", json=PERGUNTA_EXEMPLO, headers=auth)
    cliente.post("/perguntar", json={"pergunta": "Como troco a minha senha de e-mail?"}, headers=auth)
    resposta = cliente.get("/historico", headers=auth)
    assert resposta.status_code == 200
    historico = resposta.json()
    assert len(historico) == 2
    assert historico[0]["pergunta"] == PERGUNTA_EXEMPLO["pergunta"]  # primeira pergunta primeiro
    assert historico[1]["pergunta"] == "Como troco a minha senha de e-mail?"


def test_historico_e_por_usuario(cliente, auth, auth_tecnico, ia_mockada):
    cliente.post("/perguntar", json=PERGUNTA_EXEMPLO, headers=auth)
    resposta = cliente.get("/historico", headers=auth_tecnico)
    assert resposta.status_code == 200
    assert resposta.json() == []  # a pergunta da Ana não aparece para o Carlos


def test_historico_comeca_vazio(cliente, auth):
    resposta = cliente.get("/historico", headers=auth)
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_pergunta_muito_curta_retorna_422(cliente, auth, ia_mockada):
    resposta = cliente.post("/perguntar", json={"pergunta": "oi"}, headers=auth)
    assert resposta.status_code == 422


def test_falha_na_ia_retorna_502(cliente, auth, monkeypatch):
    def ia_quebrada(pergunta):
        raise RuntimeError("API da IA fora do ar")

    monkeypatch.setattr("app.ia.responder_pergunta", ia_quebrada)
    resposta = cliente.post("/perguntar", json=PERGUNTA_EXEMPLO, headers=auth)
    assert resposta.status_code == 502
    assert "IA" in resposta.json()["detail"]
