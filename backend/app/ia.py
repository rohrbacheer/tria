"""Integração com a IA Generativa (Google Gemini) — a assistente virtual do PUCHUB."""

import json
import os

from google import genai
from google.genai import types
from pydantic import BaseModel

from app import db

CATEGORIAS = ["Hardware", "Software", "Rede", "Acesso e Senhas", "E-mail", "Outro"]

PROMPT_SISTEMA = f"""Você é a assistente virtual de TI do PUCHUB, o portal de serviços de TI de uma
empresa fictícia. Sua função é responder dúvidas de tecnologia do dia a dia de trabalho:
computador, impressora, rede, internet, sistemas, e-mail, senhas e acessos.

Como responder:
- Seja cordial, objetiva e responda sempre em português brasileiro. Trate o colaborador por você.
- "resposta" deve ter de 2 a 6 frases, com passos práticos que o colaborador consegue seguir
  sozinho. Se o problema normalmente exige um técnico, dê os primeiros passos e oriente a
  procurar a equipe de suporte.
- Nunca invente detalhes sobre sistemas específicos da empresa; na dúvida, dê orientações gerais.
- Se a pergunta não for sobre TI, explique em uma frase que você só responde dúvidas de
  tecnologia e classifique como "Outro".
- "categoria" deve ser exatamente uma destas: {", ".join(CATEGORIAS)}.
Responda somente com o JSON pedido."""


class RespostaIA(BaseModel):
    """Formato de saída estruturada exigido do Gemini."""

    resposta: str
    categoria: str


def _chave_api() -> str:
    """Chave do Gemini: a gravada na tela de Integrações (banco) tem prioridade sobre a
    variável de ambiente GEMINI_API_KEY. Nunca fica no código."""
    chave = db.ler_config("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
    if not chave:
        raise RuntimeError("Chave do Gemini não configurada (tela de Integrações ou GEMINI_API_KEY).")
    return chave


def _modelo() -> str:
    """Modelo do Gemini, com a mesma precedência da chave (banco > ambiente > padrão)."""
    return db.ler_config("gemini_modelo") or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")


def status_integracao() -> dict:
    """O que a tela de Integrações mostra: se há chave, de onde ela vem e o modelo em uso."""
    if db.ler_config("gemini_api_key"):
        origem = "banco"
    elif os.environ.get("GEMINI_API_KEY"):
        origem = "ambiente"
    else:
        origem = None
    return {"gemini_configurada": origem is not None, "origem": origem, "modelo": _modelo()}


def testar_conexao() -> None:
    """Chamada mínima ao Gemini só para validar a chave (botão Testar da tela de Integrações)."""
    cliente = _criar_cliente()
    cliente.models.generate_content(model=_modelo(), contents="Responda apenas: ok")


def _criar_cliente() -> genai.Client:
    """Cria o cliente do Gemini com a chave configurada (banco ou ambiente)."""
    return genai.Client(api_key=_chave_api())


def responder_pergunta(pergunta: str) -> dict:
    """Envia a pergunta do usuário ao Gemini e devolve a resposta estruturada como dicionário.

    Esta é a única função que fala com a IA — nos testes automatizados ela é
    substituída por um mock, para que nenhum teste dependa da API externa.
    """
    cliente = _criar_cliente()
    resposta = cliente.models.generate_content(
        model=_modelo(),
        contents=pergunta,
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_SISTEMA,
            response_mime_type="application/json",
            response_schema=RespostaIA,
            temperature=0.3,
        ),
    )
    return _parse_resposta(resposta.text)


def _parse_resposta(texto: str) -> dict:
    """Valida o JSON devolvido pela IA, com valor seguro caso ela fuja das categorias."""
    dados = json.loads(texto)
    resposta = RespostaIA(**dados)
    if resposta.categoria not in CATEGORIAS:
        resposta.categoria = "Outro"
    return resposta.model_dump()


# ---------- Orientação inicial do chamado manual ----------

PRIORIDADES = ["Baixa", "Média", "Alta"]

PROMPT_ORIENTACAO = """Você é o analista de suporte de TI do PUCHUB. Um colaborador abriu um
chamado e ele mesmo classificou título, categoria e prioridade. Escreva a primeira orientação:
2 a 4 frases, em português, educadas e práticas, com os primeiros passos que ele pode tentar
sozinho enquanto aguarda o atendimento. Não invente detalhes que não estão no chamado.
Responda somente com o texto da orientação, sem saudação e sem assinatura."""


def gerar_orientacao(titulo: str, descricao: str, categoria: str, prioridade: str) -> str:
    """Pede ao Gemini a primeira orientação para um chamado já classificado pelo usuário.

    Assim como responder_pergunta, é substituída por um mock nos testes.
    """
    chamado = (
        f"Título: {titulo}\n"
        f"Categoria: {categoria}\n"
        f"Prioridade: {prioridade}\n"
        f"Descrição: {descricao}"
    )
    cliente = _criar_cliente()
    resposta = cliente.models.generate_content(
        model=_modelo(),
        contents=chamado,
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_ORIENTACAO,
            temperature=0.3,
        ),
    )
    return resposta.text.strip()
