# Tria — Assistente inteligente de classificação de solicitações

[![CI](https://github.com/rohrbacheer/tria/actions/workflows/ci.yml/badge.svg)](https://github.com/rohrbacheer/tria/actions/workflows/ci.yml)

Portal de TI com IA Generativa e três perfis de acesso. Depois do login, o usuário descreve o
problema para a **Tria** (o Google Gemini responde na tela, orienta e classifica a categoria).
Se a orientação não resolver, a Tria **abre um chamado automaticamente**, já classificado
(categoria e prioridade) e **roteado para a equipe responsável** por aquela categoria. Também dá
para abrir uma solicitação manual, em que o usuário classifica e a IA escreve a primeira
orientação. O usuário vê as próprias solicitações; **técnico** e **administrador** veem a fila
inteira; só o administrador configura a integração com a IA pela tela. A ideia nasceu do
**CotraHub**, portal interno de TI que desenvolvo no trabalho, aqui recriada do zero como uma
mini-aplicação pública para o **Desafio da Trilha de DevOps e IA Generativa (PUCPR)**.

**Equipes de atendimento:** Hardware → Suporte Técnico; Software e E-mail → Sistemas; Rede →
Infraestrutura; Acesso e senhas → Segurança e Acessos; Outro → Suporte Técnico.

🌐 **Aplicação em produção:** https://tria-bqc2.onrender.com

## Como funciona

```
frontend (HTML/CSS/JS puro)  →  backend (FastAPI/Python)  →  Google Gemini (gemini-3.8-flash)
                                        ↓
                                 SQLite (usuários, sessões, perguntas e solicitações)
```

- **`/backend`** — API em FastAPI. A pergunta vai ao Gemini com um prompt de sistema que define
  o papel da Tria e exige **saída estruturada em JSON** (`resposta` + `categoria`). Na
  solicitação manual é o contrário: a pessoa classifica e o Gemini escreve a orientação inicial.
- **`/frontend`** — portal em HTML, CSS e JavaScript puros (sem frameworks), servido pelo próprio
  FastAPI (mesma origem, sem CORS): tela de login, assistente em chat, nova solicitação com
  classificação, fila, histórico e integrações, com tema claro e escuro automático.

## Endpoints da API

| Método | Rota            | O que faz                                                               |
| ------ | --------------- | ----------------------------------------------------------------------- |
| `GET`  | `/saude`        | Health check, confirma que a API está no ar                              |
| `POST` | `/login`        | Valida as credenciais e abre a sessão (token Bearer)                     |
| `POST` | `/perguntar`    | Envia a pergunta à IA e devolve resposta + categoria (grava tudo)        |
| `GET`  | `/historico`    | Perguntas já respondidas do usuário logado, em ordem cronológica         |
| `GET`  | `/opcoes`       | Categorias e prioridades aceitas na solicitação manual                   |
| `POST` | `/solicitacoes` | Abre uma solicitação classificada pelo usuário; a IA escreve a orientação |
| `POST` | `/solicitacoes/auto` | A Tria classifica o relato e abre o chamado roteado para a equipe   |
| `GET`  | `/solicitacoes` | Solicitações do usuário; técnico e administrador veem a fila inteira     |
| `GET`  | `/integracoes`  | Estado da integração com a IA (só administrador; a chave nunca volta)    |
| `POST` | `/integracoes`  | Salva a chave/modelo do Gemini pela tela, vence a variável de ambiente   |
| `POST` | `/integracoes/testar` | Chamada mínima ao Gemini para validar a chave configurada         |

Documentação interativa (Swagger) em `/docs`.

## Contas de demonstração

Criadas automaticamente no primeiro boot (senha `puc123` para todas):

| Login         | Perfil        | O que vê                                                    |
| ------------- | ------------- | ------------------------------------------------------------ |
| `ana.souza`   | Usuária       | Assistente, as próprias solicitações e o histórico            |
| `carlos.lima` | Técnico de TI | O mesmo, mas com a fila inteira de solicitações               |
| `julia.alves` | Administradora | Tudo isso e a tela de Integrações (configuração da IA)       |

## Rodando localmente

Pré-requisitos: Python 3.12 e uma chave do [Google AI Studio](https://aistudio.google.com/apikey).

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows (no Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt

# configure a chave por variável de ambiente, ou depois pela tela de Integrações:
set GEMINI_API_KEY=sua_chave   # Windows (no Linux/Mac: export GEMINI_API_KEY=...)

uvicorn app.main:app --reload
```

Abra <http://localhost:8000>: o frontend e a API sobem juntos.

## Testes e cobertura

```bash
cd backend
pytest
```

- A chamada à IA é **sempre simulada (mock)** nos testes, nenhum teste depende da API do Gemini.
- O `pytest` falha se a cobertura ficar abaixo de **70%** (cobertura atual: **96%**).

## CI/CD

- **CI:** GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)) roda os testes
  com o limite de cobertura a cada push, status no badge acima.
- **CD:** deploy automático no [Render](https://render.com) via [render.yaml](render.yaml) a
  cada push na `main`.

## Segurança da chave

A chave do Gemini nunca aparece no código nem no histórico de commits. Ela entra por um de dois
caminhos: a variável de ambiente `GEMINI_API_KEY` (arquivo `.env` local, ignorado pelo git, ou o
painel do Render em produção) **ou** a tela de Integrações do portal (só o administrador), que
grava no banco e tem prioridade, o mesmo padrão de precedência de sistemas corporativos. A chave
salva nunca volta para o navegador; a tela mostra só o estado. Veja o [.env.example](.env.example).

## Decisões e aprendizados

Estão no [DECISOES.md](DECISOES.md).
