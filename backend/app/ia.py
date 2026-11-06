"""Integração com a IA Generativa (Google Gemini). A Tria fala com o Gemini por aqui."""

import json
import os
import time

from google import genai
from google.genai import types
from pydantic import BaseModel

from app import db

# O Gemini às vezes responde 503/UNAVAILABLE ("high demand") em picos passageiros. Em vez de
# falhar na cara do usuário, repetimos a chamada algumas vezes com uma espera curta.
_TENTATIVAS = 3
_ESPERA_SEGUNDOS = (1.5, 3.0)


def _e_transitorio(erro: Exception) -> bool:
    texto = str(erro).upper()
    return "503" in texto or "UNAVAILABLE" in texto or "OVERLOADED" in texto or "429" in texto


def _gerar(cliente: "genai.Client", **kwargs):
    """Chama generate_content repetindo quando o erro é transitório (sobrecarga do Gemini)."""
    for tentativa in range(_TENTATIVAS):
        try:
            return cliente.models.generate_content(**kwargs)
        except Exception as erro:
            if tentativa < _TENTATIVAS - 1 and _e_transitorio(erro):
                time.sleep(_ESPERA_SEGUNDOS[tentativa])
                continue
            raise

CATEGORIAS = ["Hardware", "Software", "Rede", "Acesso e senhas", "E-mail", "Outro"]

PROMPT_SISTEMA = f"""Você é a Tria, assistente virtual de TI de uma empresa fictícia. Sua função é
responder dúvidas de tecnologia do dia a dia de trabalho: computador, impressora, rede, internet,
sistemas, e-mail, senhas e acessos.

Como responder:
- Seja cordial, objetiva e responda sempre em português brasileiro. Trate a pessoa por você.
- Fale como uma colega de equipe: frases curtas e diretas, sem jargão e sem travessões.
- "resposta" deve ter de 2 a 6 frases, com passos práticos que a pessoa consegue seguir sozinha.
  Se o problema normalmente exige um técnico, dê os primeiros passos e oriente a abrir uma
  solicitação para a equipe.
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
    return db.ler_config("gemini_modelo") or os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


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
    _gerar(cliente, model=_modelo(), contents="Responda apenas: ok")


def _criar_cliente() -> genai.Client:
    """Cria o cliente do Gemini com a chave configurada (banco ou ambiente)."""
    return genai.Client(api_key=_chave_api())


def responder_pergunta(pergunta: str) -> dict:
    """Envia a pergunta do usuário ao Gemini e devolve a resposta estruturada como dicionário.

    Esta é a única função que fala com a IA no assistente. Nos testes automatizados ela é
    substituída por um mock, para que nenhum teste dependa da API externa.
    """
    cliente = _criar_cliente()
    resposta = _gerar(
        cliente,
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


# ---------- Orientação inicial da solicitação manual ----------

PRIORIDADES = ["Baixa", "Média", "Alta"]

PROMPT_ORIENTACAO = """Você é a Tria, assistente de TI. Uma pessoa abriu uma solicitação de
suporte e ela mesma classificou título, categoria e prioridade. Escreva a primeira orientação:
2 a 4 frases, em português, educadas e práticas, com os primeiros passos que ela pode tentar
sozinha enquanto aguarda o atendimento. Fale como uma colega de equipe, sem jargão e sem
travessões. Não invente detalhes que não estão na solicitação. Responda somente com o texto da
orientação, sem saudação e sem assinatura."""


def gerar_orientacao(titulo: str, descricao: str, categoria: str, prioridade: str) -> str:
    """Pede ao Gemini a primeira orientação para uma solicitação já classificada pelo usuário.

    Assim como responder_pergunta, é substituída por um mock nos testes.
    """
    solicitacao = (
        f"Título: {titulo}\n"
        f"Categoria: {categoria}\n"
        f"Prioridade: {prioridade}\n"
        f"Descrição: {descricao}"
    )
    cliente = _criar_cliente()
    resposta = _gerar(
        cliente,
        model=_modelo(),
        contents=solicitacao,
        config=types.GenerateContentConfig(
            system_instruction=PROMPT_ORIENTACAO,
            temperature=0.3,
        ),
    )
    return resposta.text.strip()
