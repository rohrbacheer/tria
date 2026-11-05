"""API do PUCHUB — portal de TI com assistente virtual de IA Generativa."""

from fastapi import FastAPI

app = FastAPI(
    title="PUCHUB",
    description="Assistente virtual de TI: o usuário pergunta e a IA Generativa (Google Gemini) responde.",
    version="1.0.0",
)


@app.get("/saude", tags=["Monitoramento"])
def saude() -> dict:
    """Health check: confirma que a API está no ar."""
    return {"status": "ok"}
