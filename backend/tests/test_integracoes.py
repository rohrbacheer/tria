"""Testes da tela de Integrações — área exclusiva do administrador; a chave gravada
no banco vence a variável de ambiente."""

import pytest

from app import db, ia

CONFIG_EXEMPLO = {"gemini_api_key": "chave-de-teste-123", "modelo": "gemini-2.5-pro"}


def test_usuario_nao_acessa_integracoes(cliente, auth):
    resposta = cliente.get("/integracoes", headers=auth)
    assert resposta.status_code == 403


def test_tecnico_tambem_nao_acessa_integracoes(cliente, auth_tecnico):
    resposta = cliente.get("/integracoes", headers=auth_tecnico)
    assert resposta.status_code == 403


def test_sem_chave_nenhuma_aparece_nao_configurada(cliente, auth_admin, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    resposta = cliente.get("/integracoes", headers=auth_admin)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["gemini_configurada"] is False
    assert corpo["origem"] is None


def test_variavel_de_ambiente_conta_como_configurada(cliente, auth_admin, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-do-ambiente")
    resposta = cliente.get("/integracoes", headers=auth_admin)
    assert resposta.json()["origem"] == "ambiente"


def test_salvar_chave_e_modelo_pela_tela(cliente, auth_admin, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    resposta = cliente.post("/integracoes", json=CONFIG_EXEMPLO, headers=auth_admin)
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["gemini_configurada"] is True
    assert corpo["origem"] == "banco"
    assert corpo["modelo"] == "gemini-2.5-pro"
    # A chave em si nunca volta na resposta.
    assert "chave-de-teste-123" not in resposta.text


def test_chave_do_banco_vence_a_variavel_de_ambiente(cliente, auth_admin, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "chave-do-ambiente")
    cliente.post("/integracoes", json=CONFIG_EXEMPLO, headers=auth_admin)
    assert ia._chave_api() == "chave-de-teste-123"
    assert ia.status_integracao()["origem"] == "banco"


def test_sem_chave_nenhuma_levanta_erro(cliente, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        ia._chave_api()


def test_modelo_padrao_quando_nada_configurado(cliente, monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    assert ia._modelo() == "gemini-flash-lite-latest"


def test_testar_conexao_ok(cliente, auth_admin, monkeypatch):
    monkeypatch.setattr("app.ia.testar_conexao", lambda: None)
    resposta = cliente.post("/integracoes/testar", headers=auth_admin)
    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}


def test_testar_conexao_com_falha_retorna_502(cliente, auth_admin, monkeypatch):
    def quebrada():
        raise RuntimeError("chave inválida")

    monkeypatch.setattr("app.ia.testar_conexao", quebrada)
    resposta = cliente.post("/integracoes/testar", headers=auth_admin)
    assert resposta.status_code == 502
