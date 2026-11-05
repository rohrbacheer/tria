# PUCHUB — Assistente Virtual de TI com IA Generativa

[![CI](https://github.com/rohrbacheer/puchub/actions/workflows/ci.yml/badge.svg)](https://github.com/rohrbacheer/puchub/actions/workflows/ci.yml)

Sistema de perguntas e respostas com IA Generativa: o usuário digita uma dúvida de TI
(impressora, rede, e-mail, senhas…) e a assistente virtual responde na tela, classificando
também a categoria da dúvida. A ideia nasceu do **CotraHub**, portal interno de TI que
desenvolvo no trabalho — aqui recriada do zero como uma mini-aplicação pública para o
**Desafio da Trilha de DevOps e IA Generativa (PUCPR)**.

🌐 **Aplicação em produção:** `<URL_DO_RENDER_AQUI>`

## Como funciona

```
frontend (HTML/CSS/JS puro)  →  backend (FastAPI/Python)  →  Google Gemini (gemini-2.5-flash)
                                        ↓
                                 SQLite (histórico)
```

- **`/backend`** — API em FastAPI. A pergunta vai ao Gemini com um prompt de sistema que
  define o papel de assistente de TI e exige **saída estruturada em JSON** (`resposta` +
  `categoria`). Cada resposta é gravada em SQLite.
- **`/frontend`** — portal em HTML, CSS e JavaScript puros (sem frameworks), servido pelo próprio
  FastAPI (mesma origem, sem CORS): shell com barra lateral e três telas — Assistente Virtual
  (chat), Histórico (tabela) e Sobre, com tema claro/escuro automático.

## Endpoints da API

| Método | Rota         | O que faz                                                        |
| ------ | ------------ | ---------------------------------------------------------------- |
| `GET`  | `/saude`     | Health check — confirma que a API está no ar                      |
| `POST` | `/perguntar` | Envia a pergunta à IA e devolve resposta + categoria (grava tudo) |
| `GET`  | `/historico` | Lista as perguntas já respondidas, em ordem cronológica           |

Documentação interativa (Swagger) em `/docs`.

## Rodando localmente

Pré-requisitos: Python 3.12 e uma chave do [Google AI Studio](https://aistudio.google.com/apikey).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows (no Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# configure a chave (copie o .env.example da raiz e preencha, ou exporte direto):
set GEMINI_API_KEY=sua_chave   # Windows (no Linux/Mac: export GEMINI_API_KEY=...)

uvicorn app.main:app --reload
```

Abra <http://localhost:8000> — o frontend e a API sobem juntos.

## Testes e cobertura

```bash
cd backend
pytest
```

- A chamada à IA é **sempre simulada (mock)** nos testes — nenhum teste depende da API do Gemini.
- O `pytest` falha se a cobertura ficar abaixo de **70%** (cobertura atual: **95%**).

## CI/CD

- **CI:** GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) roda os testes
  com o limite de cobertura a cada push — status no badge acima.
- **CD:** deploy automático no [Render](https://render.com) via [render.yaml](render.yaml) a
  cada push na `main`.

## Segurança da chave

A chave do Gemini vive **somente** na variável de ambiente `GEMINI_API_KEY` (arquivo `.env`
local, ignorado pelo git, e painel do Render em produção). Nenhuma chave aparece no código nem
no histórico de commits — veja o [.env.example](.env.example).

## Decisões e aprendizados

Estão no [DECISOES.md](DECISOES.md).
