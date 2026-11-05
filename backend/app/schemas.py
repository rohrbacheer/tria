"""Modelos de entrada e saída da API (validação automática do FastAPI/Pydantic)."""

from pydantic import BaseModel, Field, field_validator

from app.ia import CATEGORIAS, PRIORIDADES


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


class IntegracaoEntrada(BaseModel):
    """Configuração da IA enviada pela tela de Integrações (só o perfil técnico)."""

    gemini_api_key: str = Field(min_length=10, max_length=200)
    modelo: str | None = Field(default=None, max_length=100, examples=["gemini-2.5-flash"])


class IntegracaoSaida(BaseModel):
    """Estado da integração: a chave em si nunca volta para o navegador."""

    gemini_configurada: bool
    origem: str | None  # "banco", "ambiente" ou None
    modelo: str


class ChamadoEntrada(BaseModel):
    """Chamado aberto manualmente: o próprio usuário classifica antes de enviar."""

    titulo: str = Field(min_length=5, max_length=100, examples=["Impressora não imprime"])
    descricao: str = Field(
        min_length=10,
        max_length=2000,
        examples=["Minha impressora parou de imprimir e aparece um erro de driver na tela."],
    )
    categoria: str = Field(examples=["Hardware"])
    prioridade: str = Field(examples=["Média"])

    @field_validator("categoria")
    @classmethod
    def _categoria_do_catalogo(cls, valor: str) -> str:
        if valor not in CATEGORIAS:
            raise ValueError(f"deve ser uma destas: {', '.join(CATEGORIAS)}")
        return valor

    @field_validator("prioridade")
    @classmethod
    def _prioridade_valida(cls, valor: str) -> str:
        if valor not in PRIORIDADES:
            raise ValueError(f"deve ser uma destas: {', '.join(PRIORIDADES)}")
        return valor


class ChamadoSaida(BaseModel):
    """Chamado completo, com a orientação inicial escrita pela IA."""

    id: int
    solicitante: str
    titulo: str
    descricao: str
    categoria: str
    prioridade: str
    orientacao: str
    status: str
    criado_em: str
