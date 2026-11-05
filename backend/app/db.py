"""Persistência em SQLite (biblioteca padrão): usuários, sessões e o histórico do assistente."""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Contas de demonstração criadas no primeiro boot (senha padrão: puc123).
# Didático: SHA-256 simples para a senha — num sistema real, bcrypt/argon2 com salt por usuário.
USUARIOS_DEMO = [
    ("ana.souza", "Ana Souza", "puc123", "COLABORADOR"),
    ("carlos.lima", "Carlos Lima", "puc123", "TECNICO"),
]


def _caminho_banco() -> str:
    """Caminho do arquivo do banco; configurável via DB_PATH (útil nos testes)."""
    return os.environ.get("DB_PATH", str(Path(__file__).resolve().parents[1] / "puchub.db"))


def _conectar() -> sqlite3.Connection:
    conexao = sqlite3.connect(_caminho_banco())
    conexao.row_factory = sqlite3.Row
    return conexao


def _hash_senha(senha: str) -> str:
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    """Cria as tabelas caso ainda não existam e semeia os usuários de demonstração."""
    with _conectar() as conexao:
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL
            )
            """
        )
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS sessoes (
                token TEXT PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                criado_em TEXT NOT NULL
            )
            """
        )
        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS perguntas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                pergunta TEXT NOT NULL,
                resposta TEXT NOT NULL,
                categoria TEXT NOT NULL,
                criado_em TEXT NOT NULL
            )
            """
        )
        ja_tem_usuarios = conexao.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
        if ja_tem_usuarios == 0:
            for login, nome, senha, perfil in USUARIOS_DEMO:
                conexao.execute(
                    "INSERT INTO usuarios (login, nome, senha_hash, perfil) VALUES (?, ?, ?, ?)",
                    (login, nome, _hash_senha(senha), perfil),
                )


def autenticar(login: str, senha: str) -> dict | None:
    """Confere as credenciais e abre uma sessão; devolve None quando não batem."""
    with _conectar() as conexao:
        linha = conexao.execute(
            "SELECT * FROM usuarios WHERE login = ? AND senha_hash = ?",
            (login, _hash_senha(senha)),
        ).fetchone()
        if linha is None:
            return None
        token = secrets.token_hex(16)
        conexao.execute(
            "INSERT INTO sessoes (token, usuario_id, criado_em) VALUES (?, ?, ?)",
            (token, linha["id"], _agora()),
        )
    return {"token": token, "nome": linha["nome"], "perfil": linha["perfil"]}


def usuario_do_token(token: str) -> dict | None:
    """Devolve o usuário dono da sessão, ou None se o token não existir."""
    with _conectar() as conexao:
        linha = conexao.execute(
            """
            SELECT u.id, u.login, u.nome, u.perfil
            FROM sessoes s JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
    return dict(linha) if linha else None


def inserir_pergunta(usuario_id: int, pergunta: str, resultado_ia: dict) -> dict:
    """Grava uma pergunta respondida pela IA e devolve o registro completo."""
    criado_em = _agora()
    with _conectar() as conexao:
        cursor = conexao.execute(
            """
            INSERT INTO perguntas (usuario_id, pergunta, resposta, categoria, criado_em)
            VALUES (?, ?, ?, ?, ?)
            """,
            (usuario_id, pergunta, resultado_ia["resposta"], resultado_ia["categoria"], criado_em),
        )
        novo_id = cursor.lastrowid
    return {
        "id": novo_id,
        "pergunta": pergunta,
        "resposta": resultado_ia["resposta"],
        "categoria": resultado_ia["categoria"],
        "criado_em": criado_em,
    }


def listar_historico(usuario_id: int) -> list[dict]:
    """Devolve o histórico do próprio usuário em ordem cronológica (como uma conversa)."""
    with _conectar() as conexao:
        linhas = conexao.execute(
            "SELECT id, pergunta, resposta, categoria, criado_em FROM perguntas WHERE usuario_id = ? ORDER BY id ASC",
            (usuario_id,),
        ).fetchall()
    return [dict(linha) for linha in linhas]
