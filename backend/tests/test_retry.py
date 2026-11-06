"""Testes da repetição automática quando o Gemini responde erro transitório (503/high demand)."""

import pytest

from app import ia


class _ClienteFalso:
    """Simula o cliente do Gemini: falha com 503 nas primeiras vezes, depois responde."""

    def __init__(self, falhas: int, erro_final: Exception | None = None):
        self.falhas = falhas
        self.erro_final = erro_final
        self.chamadas = 0
        self.models = self

    def generate_content(self, **kwargs):
        self.chamadas += 1
        if self.chamadas <= self.falhas:
            raise RuntimeError("503 UNAVAILABLE: high demand")
        if self.erro_final:
            raise self.erro_final
        return "ok"


@pytest.fixture(autouse=True)
def _sem_espera(monkeypatch):
    # Não esperar de verdade entre as tentativas durante o teste.
    monkeypatch.setattr(ia.time, "sleep", lambda _s: None)


def test_repete_e_tem_sucesso_apos_picos(monkeypatch):
    cliente = _ClienteFalso(falhas=2)  # falha 2x, sucesso na 3a
    assert ia._gerar(cliente, model="x", contents="oi") == "ok"
    assert cliente.chamadas == 3


def test_desiste_apos_o_limite_de_tentativas():
    cliente = _ClienteFalso(falhas=99)  # sempre 503
    with pytest.raises(RuntimeError):
        ia._gerar(cliente, model="x", contents="oi")
    assert cliente.chamadas == ia._TENTATIVAS  # tentou o máximo e parou


def test_erro_nao_transitorio_nao_repete():
    cliente = _ClienteFalso(falhas=0, erro_final=ValueError("400 chave invalida"))
    with pytest.raises(ValueError):
        ia._gerar(cliente, model="x", contents="oi")
    assert cliente.chamadas == 1  # erro definitivo: não repete


def test_classificador_de_transitorio():
    assert ia._e_transitorio(RuntimeError("503 UNAVAILABLE"))
    assert ia._e_transitorio(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert not ia._e_transitorio(RuntimeError("404 NOT_FOUND"))
