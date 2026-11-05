"""Testes dos endpoints da API — a IA é sempre simulada (mock), nunca chamada de verdade."""

PERGUNTA_EXEMPLO = {"pergunta": "Minha internet está muito lenta, o que posso fazer?"}


def test_saude_retorna_ok(cliente):
    resposta = cliente.get("/saude")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_perguntar_devolve_resposta_da_ia(cliente, ia_mockada):
    resposta = cliente.post("/perguntar", json=PERGUNTA_EXEMPLO)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["id"] == 1
    assert corpo["pergunta"] == PERGUNTA_EXEMPLO["pergunta"]
    assert corpo["resposta"] == ia_mockada["resposta"]
    assert corpo["categoria"] == ia_mockada["categoria"]
    assert corpo["criado_em"]


def test_historico_em_ordem_cronologica(cliente, ia_mockada):
    cliente.post("/perguntar", json=PERGUNTA_EXEMPLO)
    cliente.post("/perguntar", json={"pergunta": "Como troco a minha senha de e-mail?"})
    resposta = cliente.get("/historico")
    assert resposta.status_code == 200
    historico = resposta.json()
    assert len(historico) == 2
    assert historico[0]["pergunta"] == PERGUNTA_EXEMPLO["pergunta"]  # primeira pergunta primeiro
    assert historico[1]["pergunta"] == "Como troco a minha senha de e-mail?"


def test_historico_comeca_vazio(cliente):
    resposta = cliente.get("/historico")
    assert resposta.status_code == 200
    assert resposta.json() == []


def test_pergunta_muito_curta_retorna_422(cliente, ia_mockada):
    resposta = cliente.post("/perguntar", json={"pergunta": "oi"})
    assert resposta.status_code == 422


def test_falha_na_ia_retorna_502(cliente, monkeypatch):
    def ia_quebrada(pergunta):
        raise RuntimeError("API da IA fora do ar")

    monkeypatch.setattr("app.ia.responder_pergunta", ia_quebrada)
    resposta = cliente.post("/perguntar", json=PERGUNTA_EXEMPLO)
    assert resposta.status_code == 502
    assert "IA" in resposta.json()["detail"]
