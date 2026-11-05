"""Persistência do histórico de perguntas e respostas em SQLite (biblioteca padrão do Python)."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def _caminho_banco() -> str:
    """Caminho do arquivo do banco; configurável via DB_PATH (útil nos testes)."""
    return os.environ.get("DB_PATH", str(Path(__file__).resolve().parents[1] / "puchub.db"))


def _conectar() -> sqlite3.Connection:
    conexao = sqlite3.connect(_caminho_banco())
    conexao.row_factory = sqlite3.Row
    return conexao


def init_db() -> None:
    """Cria a tabela do histórico caso ainda não exista."""
    with _conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS perguntas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pergunta TEXT NOT NULL,
                resposta TEXT NOT NULL,
                categoria TEXT NOT NULL,
                criado_em TEXT NOT NULL
            )
            """
        )


def inserir_pergunta(pergunta: str, resultado_ia: dict) -> dict:
    """Grava uma pergunta respondida pela IA e devolve o registro completo."""
    criado_em = datetime.now(timezone.utc).isoformat()
    with _conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO perguntas (pergunta, resposta, categoria, criado_em)
            VALUES (?, ?, ?, ?)
            """,
            (pergunta, resultado_ia["resposta"], resultado_ia["categoria"], criado_em),
        )
        novo_id = cursor.lastrowid
    return {
        "id": novo_id,
        "pergunta": pergunta,
        "resposta": resultado_ia["resposta"],
        "categoria": resultado_ia["categoria"],
        "criado_em": criado_em,
    }


def listar_historico() -> list[dict]:
    """Devolve todo o histórico em ordem cronológica (como uma conversa)."""
    with _conectar() as conexao:
        linhas = conexao.execute("SELECT * FROM perguntas ORDER BY id ASC").fetchall()
    return [dict(linha) for linha in linhas]
