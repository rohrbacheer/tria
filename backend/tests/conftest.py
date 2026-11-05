"""Fixtures compartilhadas: banco temporário, sessões de login e mock da IA
(nenhum teste chama o Gemini real)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

RESPOSTA_FALSA = {
    "resposta": "Verifique se o cabo de rede está conectado e reinicie o roteador. Se não resolver, acione o suporte.",
    "categoria": "Rede",
}


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    """Cliente de teste da API usando um banco SQLite temporário e isolado."""
    monkeypatch.setenv("DB_PATH", str(tmp_path / "teste.db"))
    with TestClient(app) as cliente_teste:
        yield cliente_teste


def _login(cliente, login: str) -> dict:
    resposta = cliente.post("/login", json={"login": login, "senha": "puc123"})
    assert resposta.status_code == 200
    return {"Authorization": "Bearer " + resposta.json()["token"]}


@pytest.fixture()
def auth(cliente):
    """Cabeçalho de sessão da colaboradora de demonstração (ana.souza)."""
    return _login(cliente, "ana.souza")


@pytest.fixture()
def auth_tecnico(cliente):
    """Cabeçalho de sessão do técnico de demonstração (carlos.lima)."""
    return _login(cliente, "carlos.lima")


@pytest.fixture()
def ia_mockada(monkeypatch):
    """Substitui a chamada ao Gemini por uma resposta fixa (mock)."""
    monkeypatch.setattr("app.ia.responder_pergunta", lambda pergunta: dict(RESPOSTA_FALSA))
    return RESPOSTA_FALSA
