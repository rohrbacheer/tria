"""API do PUCHUB — portal de TI com assistente virtual de IA Generativa."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.staticfiles import StaticFiles

from app import db, ia
from app.schemas import (
    ChamadoEntrada,
    ChamadoSaida,
    IntegracaoEntrada,
    IntegracaoSaida,
    LoginEntrada,
    LoginSaida,
    PerguntaEntrada,
    RespostaSaida,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="PUCHUB",
    description="Portal de TI com assistente virtual: o usuário pergunta e a IA Generativa (Google Gemini) responde.",
    version="2.0.0",
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


@app.post("/chamados", response_model=ChamadoSaida, status_code=201, tags=["Chamados"])
def abrir_chamado(entrada: ChamadoEntrada, usuario: dict = Depends(usuario_atual)) -> dict:
    """Abre um chamado: a IA classifica categoria e prioridade e sugere a primeira orientação."""
    try:
        triagem = ia.triar_chamado(entrada.descricao)
    except Exception as erro:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível consultar a IA no momento. Tente novamente em instantes.",
        ) from erro
    return db.inserir_chamado(usuario["id"], entrada.descricao, triagem)


@app.get("/chamados", response_model=list[ChamadoSaida], tags=["Chamados"])
def listar_chamados(usuario: dict = Depends(usuario_atual)) -> list[dict]:
    """Lista os chamados: técnico e administrador veem a fila inteira, o usuário só os próprios."""
    return db.listar_chamados(usuario)


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
        raise HTTPException(
            status_code=502,
            detail="Não foi possível falar com o Gemini. Confira a chave e tente de novo.",
        ) from erro
    return {"ok": True}


# Serve a interface web (pasta /frontend) na raiz do site — mesmo domínio da API, sem CORS.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
