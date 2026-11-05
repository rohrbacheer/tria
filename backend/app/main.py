"""API do PUCHUB — portal de TI com assistente virtual de IA Generativa."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from app import db, ia
from app.schemas import PerguntaEntrada, RespostaSaida


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="PUCHUB",
    description="Assistente virtual de TI: o usuário pergunta e a IA Generativa (Google Gemini) responde.",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/saude", tags=["Monitoramento"])
def saude() -> dict:
    """Health check: confirma que a API está no ar."""
    return {"status": "ok"}


@app.post("/perguntar", response_model=RespostaSaida, status_code=201, tags=["Assistente"])
def perguntar(entrada: PerguntaEntrada) -> dict:
    """Envia a pergunta à IA, grava no histórico e devolve a resposta com a categoria."""
    try:
        resultado = ia.responder_pergunta(entrada.pergunta)
    except Exception as erro:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível consultar a IA no momento. Tente novamente em instantes.",
        ) from erro
    return db.inserir_pergunta(entrada.pergunta, resultado)


@app.get("/historico", response_model=list[RespostaSaida], tags=["Assistente"])
def historico() -> list[dict]:
    """Lista todas as perguntas já respondidas, em ordem cronológica (como uma conversa)."""
    return db.listar_historico()


# Serve a interface web (pasta /frontend) na raiz do site — mesmo domínio da API, sem CORS.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
