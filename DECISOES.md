# Decisões do projeto

## Por que essa stack

Trabalho com TI no dia a dia e mantenho um portal interno de serviços (o CotraHub) que tem um
assistente virtual de abertura de chamados. A Tria nasceu dessa experiência: eu queria recriar,
do zero e em versão pública, a parte que mais gera valor, uma assistente que responde dúvidas
de TI em linguagem simples e classifica solicitações.

Escolhi **FastAPI (Python 3.12)** no backend porque é um framework enxuto, com validação
automática via Pydantic e documentação Swagger pronta, o que deixa os dois endpoints exigidos
muito claros de demonstrar. Para a IA usei o **Google Gemini (gemini-2.5-flash)** com **saída
estruturada em JSON**: em vez de interpretar texto livre, a API recebe sempre `resposta` e
`categoria` validadas por um schema, com valor seguro quando o modelo foge das categorias. O
histórico, os usuários de demonstração (perfis de usuário, técnico e administrador) e as
solicitações ficam em **SQLite**, que dispensa servidor de banco e basta para o escopo. A IA
entra em dois pontos: na assistente ela responde e classifica a pergunta com saída estruturada;
na solicitação manual é o contrário, a pessoa classifica (título, categoria e prioridade) e a IA
escreve a primeira orientação. O frontend é
**HTML, CSS e JavaScript puros**, servido pelo próprio FastAPI — mesma origem, sem CORS, um
único serviço no deploy. Testes com **pytest** e a chamada à IA **mockada** (nenhum teste depende
da API externa), cobertura mínima de 70% travada no próprio pytest — atingi 95%. O **GitHub
Actions** roda os testes a cada push e o **Render** faz o deploy automático da `main` via
blueprint (`render.yaml`).

## Maior dificuldade

Garantir que a resposta da IA fosse previsível. Texto livre quebrava o contrato da API; a
solução foi exigir saída estruturada com `response_schema` e validar as categorias no backend,
com fallback para "Outro". Também precisei isolar a função que fala com o Gemini em um módulo
único para conseguir mockar nos testes sem gambiarras.

## O que aprendi e o que faria diferente

Aprendi na prática como DevOps e IA se encaixam: segredo fora do código (`.env` +
`.gitignore` + variáveis no Render), pipeline que bloqueia regressão de cobertura e deploy
contínuo de verdade. Usei IA como assistente de código durante o desenvolvimento, revisando e
entendendo cada parte antes de commitar. Se tivesse mais tempo, adicionaria conversa com
contexto (a IA lembrar das mensagens anteriores), limite de requisições por usuário e um banco
gerenciado em vez de SQLite, que no plano gratuito do Render não persiste entre deploys.
