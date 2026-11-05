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


class ChamadoEntrada(BaseModel):
    """Descrição do problema enviada ao abrir um chamado manualmente."""

    descricao: str = Field(
        min_length=10,
        max_length=2000,
        examples=["Minha impressora parou de imprimir e aparece um erro de driver na tela."],
    )


class ChamadoSaida(BaseModel):
    """Chamado completo, já com a triagem feita pela IA."""

    id: int
    solicitante: str
    descricao: str
    categoria: str
    prioridade: str
    resposta_sugerida: str
    status: str
    criado_em: str
