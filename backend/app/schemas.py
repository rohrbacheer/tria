"""Modelos de entrada e saída da API (validação automática do FastAPI/Pydantic)."""

from pydantic import BaseModel, Field


class LoginEntrada(BaseModel):
    """Credenciais enviadas na tela de login."""

    login: str = Field(min_length=3, max_length=60, examples=["ana.souza"])
    senha: str = Field(min_length=3, max_length=60, examples=["puc123"])


class LoginSaida(BaseModel):
    """Sessão aberta: o token vai no cabeçalho Authorization das próximas chamadas."""

    token: str
    nome: str
    perfil: str


class PerguntaEntrada(BaseModel):
    """Pergunta que o usuário envia para a assistente virtual."""

    pergunta: str = Field(
        min_length=5,
        max_length=1000,
        examples=["Como configuro a impressora de rede no meu computador?"],
    )


class RespostaSaida(BaseModel):
    """Pergunta completa, já com a resposta e a categoria dadas pela IA."""

    id: int
    pergunta: str
    resposta: str
    categoria: str
    criado_em: str
