"""Fixtures compartilhadas: banco temporário e mock da IA (nenhum teste chama o Gemini real)."""

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


@pytest.fixture()
def ia_mockada(monkeypatch):
    """Substitui a chamada ao Gemini por uma resposta fixa (mock)."""
    monkeypatch.setattr("app.ia.responder_pergunta", lambda pergunta: dict(RESPOSTA_FALSA))
    return RESPOSTA_FALSA
