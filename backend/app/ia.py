"""Integração com a IA Generativa (Google Gemini) — a assistente virtual do PUCHUB."""

import json
import os

from google import genai
from google.genai import types
from pydantic import BaseModel

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


def _criar_cliente() -> genai.Client:
    """Cria o cliente do Gemini lendo a chave da variável de ambiente (nunca do código)."""
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def responder_pergunta(pergunta: str) -> dict:
    """Envia a pergunta do usuário ao Gemini e devolve a resposta estruturada como dicionário.

    Esta é a única função que fala com a IA — nos testes automatizados ela é
    substituída por um mock, para que nenhum teste dependa da API externa.
    """
    cliente = _criar_cliente()
    resposta = cliente.models.generate_content(
        model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
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
