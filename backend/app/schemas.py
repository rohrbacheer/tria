"""Modelos de entrada e saída da API (validação automática do FastAPI/Pydantic)."""

from pydantic import BaseModel, Field, field_validator

from app.ia import CATEGORIAS, PRIORIDADES  # noqa: F401 (reexportados para os validadores)


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
    """Pergunta que o usuário envia para a Tria."""

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
    """Configuração da IA enviada pela tela de Integrações (só o administrador)."""

    gemini_api_key: str = Field(min_length=10, max_length=200)
    modelo: str | None = Field(default=None, max_length=100, examples=["gemini-flash-lite-latest"])


class IntegracaoSaida(BaseModel):
    """Estado da integração: a chave em si nunca volta para o navegador."""

    gemini_configurada: bool
    origem: str | None  # "banco", "ambiente" ou None
    modelo: str


class SolicitacaoEntrada(BaseModel):
    """Solicitação aberta manualmente: o próprio usuário classifica antes de enviar."""

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


class SolicitacaoAutoEntrada(BaseModel):
    """Relato livre que a Tria classifica e vira um chamado (quando a orientação não resolveu)."""

    descricao: str = Field(
        min_length=5,
        max_length=2000,
        examples=["Meu computador não liga, já tentei trocar a tomada e nada."],
    )


class SolicitacaoSaida(BaseModel):
    """Solicitação completa, com a orientação da IA e a equipe de destino."""

    id: int
    solicitante: str
    titulo: str
    descricao: str
    categoria: str
    prioridade: str
    equipe: str
    orientacao: str
    origem: str
    status: str
    criado_em: str
