"""Testes do tratamento da resposta da IA (parse e validação do JSON)."""

import json

import pytest

from app import ia


def test_parse_resposta_valida():
    texto = json.dumps({"resposta": "Reinicie o roteador e teste de novo.", "categoria": "Rede"})
    resultado = ia._parse_resposta(texto)
    assert resultado == {"resposta": "Reinicie o roteador e teste de novo.", "categoria": "Rede"}


def test_categoria_desconhecida_vira_outro():
    texto = json.dumps({"resposta": "Ok.", "categoria": "Culinária"})
    assert ia._parse_resposta(texto)["categoria"] == "Outro"


def test_json_invalido_levanta_erro():
    with pytest.raises(json.JSONDecodeError):
        ia._parse_resposta("isto não é um JSON")


def test_prompt_do_sistema_cita_todas_as_categorias():
    for categoria in ia.CATEGORIAS:
        assert categoria in ia.PROMPT_SISTEMA


def test_listas_de_classificacao_do_chamado_manual():
    # As mesmas listas alimentam o GET /opcoes e a validação do POST /chamados.
    assert ia.PRIORIDADES == ["Baixa", "Média", "Alta"]
    assert "Outro" in ia.CATEGORIAS
