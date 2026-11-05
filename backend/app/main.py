"""API da Tria, assistente inteligente de classificação de solicitações."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from app import db, ia
from app.schemas import (
    IntegracaoEntrada,
    IntegracaoSaida,
    LoginEntrada,
    LoginSaida,
    PerguntaEntrada,
    RespostaSaida,
    SolicitacaoEntrada,
    SolicitacaoSaida,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="Tria",
    description="Assistente inteligente de classificação de solicitações: o usuário pergunta e a IA Generativa (Google Gemini) responde.",
    version="3.0.0",
    lifespan=lifespan,
)


def usuario_atual(authorization: str | None = Header(default=None)) -> dict:
    """Identifica o usuário pelo token Bearer da sessão; sem sessão válida, 401."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Faça login para continuar.")
    usuario = db.usuario_do_token(authorization.removeprefix("Bearer "))
    if usuario is None:
        raise HTTPException(status_code=401, detail="Sessão inválida. Faça login de novo.")
    return usuario


def admin_atual(usuario: dict = Depends(usuario_atual)) -> dict:
    """Área administrativa: somente o perfil administrador passa."""
    if usuario["perfil"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Somente o administrador acessa as integrações.")
    return usuario


@app.get("/saude", tags=["Monitoramento"])
def saude() -> dict:
    """Health check: confirma que a API está no ar."""
    return {"status": "ok"}


@app.post("/login", response_model=LoginSaida, tags=["Autenticação"])
def login(entrada: LoginEntrada) -> dict:
    """Valida as credenciais e abre uma sessão (token usado nas demais chamadas)."""
    sessao = db.autenticar(entrada.login, entrada.senha)
    if sessao is None:
        raise HTTPException(status_code=401, detail="Login ou senha incorretos.")
    return sessao


@app.post("/perguntar", response_model=RespostaSaida, status_code=201, tags=["Assistente"])
def perguntar(entrada: PerguntaEntrada, usuario: dict = Depends(usuario_atual)) -> dict:
    """Envia a pergunta à IA, grava no histórico do usuário e devolve a resposta."""
    try:
        resultado = ia.responder_pergunta(entrada.pergunta)
    except Exception as erro:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível consultar a IA no momento. Tente novamente em instantes.",
        ) from erro
    return db.inserir_pergunta(usuario["id"], entrada.pergunta, resultado)


@app.get("/historico", response_model=list[RespostaSaida], tags=["Assistente"])
def historico(usuario: dict = Depends(usuario_atual)) -> list[dict]:
    """Lista as perguntas do próprio usuário, em ordem cronológica (como uma conversa)."""
    return db.listar_historico(usuario["id"])


@app.get("/opcoes", tags=["Solicitações"])
def opcoes(_usuario: dict = Depends(usuario_atual)) -> dict:
    """Opções de classificação da solicitação manual (as mesmas listas que a IA conhece)."""
    return {"categorias": ia.CATEGORIAS, "prioridades": ia.PRIORIDADES}


@app.post("/solicitacoes", response_model=SolicitacaoSaida, status_code=201, tags=["Solicitações"])
def abrir_solicitacao(entrada: SolicitacaoEntrada, usuario: dict = Depends(usuario_atual)) -> dict:
    """Abre uma solicitação classificada pelo próprio usuário; a IA escreve a primeira orientação."""
    try:
        orientacao = ia.gerar_orientacao(
            entrada.titulo, entrada.descricao, entrada.categoria, entrada.prioridade
        )
    except Exception as erro:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível consultar a IA no momento. Tente novamente em instantes.",
        ) from erro
    return db.inserir_solicitacao(
        usuario["id"], entrada.titulo, entrada.descricao, entrada.categoria, entrada.prioridade, orientacao
    )


@app.get("/solicitacoes", response_model=list[SolicitacaoSaida], tags=["Solicitações"])
def listar_solicitacoes(usuario: dict = Depends(usuario_atual)) -> list[dict]:
    """Lista as solicitações: técnico e administrador veem a fila inteira, o usuário só as próprias."""
    return db.listar_solicitacoes(usuario)


@app.get("/integracoes", response_model=IntegracaoSaida, tags=["Integrações"])
def ver_integracao(_admin: dict = Depends(admin_atual)) -> dict:
    """Estado da integração com a IA: se há chave, de onde ela vem e o modelo em uso."""
    return ia.status_integracao()


@app.post("/integracoes", response_model=IntegracaoSaida, tags=["Integrações"])
def salvar_integracao(entrada: IntegracaoEntrada, _admin: dict = Depends(admin_atual)) -> dict:
    """Grava a chave (e o modelo) no banco — ela passa a valer sobre a variável de ambiente."""
    db.salvar_config("gemini_api_key", entrada.gemini_api_key)
    if entrada.modelo:
        db.salvar_config("gemini_modelo", entrada.modelo)
    return ia.status_integracao()


@app.post("/integracoes/testar", tags=["Integrações"])
def testar_integracao(_admin: dict = Depends(admin_atual)) -> dict:
    """Faz uma chamada mínima ao Gemini para validar a chave configurada."""
    try:
        ia.testar_conexao()
    except Exception as erro:
        # Tela do administrador: mostrar a causa real encurta o diagnóstico de chave/modelo.
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao falar com o Gemini ({type(erro).__name__}): {str(erro)[:300]}",
        ) from erro
    return {"ok": True}


# Serve a interface web (pasta /frontend) na raiz do site — mesmo domínio da API, sem CORS.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
