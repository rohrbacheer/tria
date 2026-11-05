// Interface da Tria. Conversa com a API via fetch (mesma origem, sem CORS).
// A sessão (token, nome e perfil) vem do POST /login e vai no cabeçalho Authorization.

const telaLogin = document.getElementById("tela-login");
const appEl = document.getElementById("app");
const formLogin = document.getElementById("form-login");
const loginErro = document.getElementById("login-erro");

const conversa = document.getElementById("conversa");
const saudacao = document.getElementById("saudacao");
const formulario = document.getElementById("form-pergunta");
const campoPergunta = document.getElementById("pergunta");
const botaoEnviar = document.getElementById("botao-enviar");
const mensagemErro = document.getElementById("mensagem-erro");
const statusDot = document.getElementById("status-dot");
const statusTexto = document.getElementById("status-texto");

/* ---------- Sessão ---------- */

const SESSAO_CHAVE = "tria_sessao";
let sessao = null; // { token, nome, perfil }

const NOME_PERFIL = { USUARIO: "Usuário", TECNICO: "Técnico de TI", ADMIN: "Administrador" };

function veAFilaInteira() {
  return sessao.perfil === "TECNICO" || sessao.perfil === "ADMIN";
}

function iniciais(nome) {
  const partes = nome.trim().split(/\s+/);
  const primeira = partes[0] ? partes[0][0] : "";
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primeira + ultima).toUpperCase();
}

function carregarSessaoSalva() {
  try {
    sessao = JSON.parse(localStorage.getItem(SESSAO_CHAVE));
  } catch {
    sessao = null;
  }
}

function guardarSessao() {
  try {
    if (sessao) localStorage.setItem(SESSAO_CHAVE, JSON.stringify(sessao));
    else localStorage.removeItem(SESSAO_CHAVE);
  } catch {
    /* sem armazenamento local, a sessão vive só nesta aba */
  }
}

function mostrarLogin(mensagem) {
  sessao = null;
  guardarSessao();
  appEl.classList.add("escondido");
  telaLogin.classList.remove("escondido");
  if (mensagem) {
    loginErro.textContent = mensagem;
    loginErro.classList.remove("escondido");
  }
}

function entrarNoPortal() {
  telaLogin.classList.add("escondido");
  appEl.classList.remove("escondido");
  document.getElementById("usuario-avatar").textContent = iniciais(sessao.nome);
  document.getElementById("usuario-nome").textContent = sessao.nome;
  document.getElementById("usuario-perfil").textContent = NOME_PERFIL[sessao.perfil] || sessao.perfil;

  // Áreas administrativas aparecem só para o administrador.
  document
    .querySelectorAll(".somente-admin")
    .forEach((el) => el.classList.toggle("escondido", sessao.perfil !== "ADMIN"));

  // Sempre entra pela Assistente, para o novo perfil não cair numa tela que não é dele.
  document.querySelectorAll(".menu-item").forEach((b) => b.classList.remove("ativo"));
  document.querySelector('.menu-item[data-view="assistente"]').classList.add("ativo");
  document.querySelectorAll(".view").forEach((v) => v.classList.add("escondido"));
  document.getElementById("view-assistente").classList.remove("escondido");
  document.getElementById("titulo-pagina").textContent = TITULOS.assistente;

  // Zera a conversa (fica só a saudação) e carrega o histórico de quem entrou.
  conversa.querySelectorAll(".balao:not(#saudacao)").forEach((b) => b.remove());
  verificarSaude();
  carregarConversa();
  carregarOpcoes();
}

// Com o token inválido ou expirado, qualquer chamada volta 401: cai para a tela de login.
async function fetchAuth(url, opcoes = {}) {
  const tokenUsado = sessao.token;
  opcoes.headers = { ...(opcoes.headers || {}), Authorization: "Bearer " + tokenUsado };
  const resposta = await fetch(url, opcoes);
  if (resposta.status === 401) {
    // Só desloga se o token que falhou ainda é o da sessão atual. Sem isso, uma chamada
    // lenta feita com um token antigo poderia voltar depois de um novo login e derrubar
    // a sessão recém-aberta (corrida de token entre deploys que recriam o banco).
    if (sessao && sessao.token === tokenUsado) {
      mostrarLogin("Sua sessão expirou. Entre de novo.");
    }
    throw new Error("Sessão expirada");
  }
  return resposta;
}

formLogin.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  loginErro.classList.add("escondido");

  try {
    const resposta = await fetch("/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        login: document.getElementById("campo-login").value.trim(),
        senha: document.getElementById("campo-senha").value,
      }),
    });

    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      throw new Error(corpo.detail || "Não foi possível entrar. Tente novamente.");
    }

    sessao = await resposta.json();
    guardarSessao();
    formLogin.reset();
    entrarNoPortal();
  } catch (erro) {
    loginErro.textContent = erro.message;
    loginErro.classList.remove("escondido");
  }
});

document.getElementById("botao-sair").addEventListener("click", () => mostrarLogin());

/* ---------- Navegação entre as telas ---------- */

const TITULOS = {
  assistente: "Assistente",
  abrir: "Nova solicitação",
  solicitacoes: "Solicitações",
  historico: "Histórico de perguntas",
  integracoes: "Integrações",
  sobre: "Sobre o projeto",
};

function tituloDaView(view) {
  if (view === "solicitacoes") {
    return veAFilaInteira() ? "Solicitações" : "Minhas solicitações";
  }
  return TITULOS[view];
}

document.querySelectorAll(".menu-item").forEach((botao) => {
  botao.addEventListener("click", () => {
    document.querySelectorAll(".menu-item").forEach((b) => b.classList.remove("ativo"));
    botao.classList.add("ativo");

    const view = botao.dataset.view;
    document.querySelectorAll(".view").forEach((v) => v.classList.add("escondido"));
    document.getElementById("view-" + view).classList.remove("escondido");
    document.getElementById("titulo-pagina").textContent = tituloDaView(view);

    if (view === "historico") carregarTabelaHistorico();
    if (view === "solicitacoes") carregarSolicitacoes();
    if (view === "integracoes") carregarIntegracoes();
  });
});

/* ---------- Nova solicitação ---------- */

let prioridadeEscolhida = "Média";

// As opções de classificação vêm da API (as mesmas listas que a IA conhece).
async function carregarOpcoes() {
  const resposta = await fetchAuth("/opcoes");
  if (!resposta.ok) return;
  const opcoes = await resposta.json();

  const selectCategoria = document.getElementById("categoria");
  selectCategoria.innerHTML = "";
  for (const categoria of opcoes.categorias) {
    selectCategoria.add(new Option(categoria, categoria));
  }

  const grupo = document.getElementById("prioridades");
  grupo.innerHTML = "";
  for (const prioridade of opcoes.prioridades) {
    const botao = document.createElement("button");
    botao.type = "button";
    botao.className = "segmento" + (prioridade === prioridadeEscolhida ? " ativo" : "");
    botao.textContent = prioridade;
    botao.addEventListener("click", () => {
      prioridadeEscolhida = prioridade;
      grupo.querySelectorAll(".segmento").forEach((b) => b.classList.remove("ativo"));
      botao.classList.add("ativo");
    });
    grupo.appendChild(botao);
  }
}

const formSolicitacao = document.getElementById("form-solicitacao");
const botaoAbrir = document.getElementById("botao-abrir");
const solicitacaoErro = document.getElementById("solicitacao-erro");
const solicitacaoResultado = document.getElementById("solicitacao-resultado");

function classeDePrioridade(prioridade) {
  return "pill pill-" + prioridade.toLowerCase().replace("é", "e");
}

formSolicitacao.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  solicitacaoErro.classList.add("escondido");
  solicitacaoResultado.classList.add("escondido");
  botaoAbrir.disabled = true;
  botaoAbrir.textContent = "A Tria está escrevendo a orientação…";

  try {
    const resposta = await fetchAuth("/solicitacoes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        titulo: document.getElementById("titulo").value.trim(),
        descricao: document.getElementById("descricao").value.trim(),
        categoria: document.getElementById("categoria").value,
        prioridade: prioridadeEscolhida,
      }),
    });

    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      throw new Error(corpo.detail || "Não foi possível abrir a solicitação. Tente novamente.");
    }

    const solicitacao = await resposta.json();
    document.getElementById("resultado-protocolo").textContent =
      "Solicitação #" + solicitacao.id + " aberta: " + solicitacao.titulo;
    document.getElementById("resultado-categoria").textContent = solicitacao.categoria;
    const pillPrioridade = document.getElementById("resultado-prioridade");
    pillPrioridade.textContent = "Prioridade " + solicitacao.prioridade;
    pillPrioridade.className = classeDePrioridade(solicitacao.prioridade);
    document.getElementById("resultado-orientacao").textContent = solicitacao.orientacao;
    solicitacaoResultado.classList.remove("escondido");
    formSolicitacao.reset();
  } catch (erro) {
    solicitacaoErro.textContent = erro.message;
    solicitacaoErro.classList.remove("escondido");
  } finally {
    botaoAbrir.disabled = false;
    botaoAbrir.textContent = "Abrir solicitação";
  }
});

/* ---------- Solicitações (tabela) ---------- */

async function carregarSolicitacoes() {
  // A coluna Solicitante só faz sentido para quem vê a fila inteira (técnico e admin).
  document
    .getElementById("tabela-solicitacoes")
    .classList.toggle("sem-solicitante", !veAFilaInteira());

  const resposta = await fetchAuth("/solicitacoes");
  if (!resposta.ok) return;
  const solicitacoes = await resposta.json();

  const corpo = document.getElementById("solicitacoes-linhas");
  const vazio = document.getElementById("solicitacoes-vazio");
  corpo.innerHTML = "";
  vazio.classList.toggle("escondido", solicitacoes.length > 0);

  for (const solicitacao of solicitacoes) {
    const linha = document.createElement("tr");

    const colunaId = document.createElement("td");
    colunaId.textContent = "#" + solicitacao.id;

    const colunaSolicitante = document.createElement("td");
    colunaSolicitante.className = "col-solicitante";
    colunaSolicitante.textContent = solicitacao.solicitante;

    const colunaTitulo = document.createElement("td");
    colunaTitulo.className = "col-pergunta";
    colunaTitulo.textContent = solicitacao.titulo;
    colunaTitulo.title = solicitacao.descricao; // a descrição completa aparece ao passar o mouse

    const colunaCategoria = document.createElement("td");
    const pillCategoria = document.createElement("span");
    pillCategoria.className = "pill";
    pillCategoria.textContent = solicitacao.categoria;
    colunaCategoria.appendChild(pillCategoria);

    const colunaPrioridade = document.createElement("td");
    const pillPrioridade = document.createElement("span");
    pillPrioridade.className = classeDePrioridade(solicitacao.prioridade);
    pillPrioridade.textContent = solicitacao.prioridade;
    colunaPrioridade.appendChild(pillPrioridade);

    const colunaStatus = document.createElement("td");
    colunaStatus.textContent = solicitacao.status;

    const colunaData = document.createElement("td");
    colunaData.className = "col-data";
    colunaData.textContent = new Date(solicitacao.criado_em).toLocaleString("pt-BR");

    linha.append(
      colunaId,
      colunaSolicitante,
      colunaTitulo,
      colunaCategoria,
      colunaPrioridade,
      colunaStatus,
      colunaData
    );
    corpo.appendChild(linha);
  }
}

/* ---------- Histórico (tabela) ---------- */

async function carregarTabelaHistorico() {
  const resposta = await fetchAuth("/historico");
  if (!resposta.ok) return;
  const itens = await resposta.json();

  const corpo = document.getElementById("historico-linhas");
  const vazio = document.getElementById("historico-vazio");
  corpo.innerHTML = "";
  vazio.classList.toggle("escondido", itens.length > 0);

  for (const item of itens.slice().reverse()) {
    const linha = document.createElement("tr");

    const colunaId = document.createElement("td");
    colunaId.textContent = "#" + item.id;

    const colunaPergunta = document.createElement("td");
    colunaPergunta.className = "col-pergunta";
    colunaPergunta.textContent = item.pergunta;

    const colunaCategoria = document.createElement("td");
    const pill = document.createElement("span");
    pill.className = "pill";
    pill.textContent = item.categoria;
    colunaCategoria.appendChild(pill);

    const colunaData = document.createElement("td");
    colunaData.className = "col-data";
    colunaData.textContent = new Date(item.criado_em).toLocaleString("pt-BR");

    linha.append(colunaId, colunaPergunta, colunaCategoria, colunaData);
    corpo.appendChild(linha);
  }
}

/* ---------- Integrações (área do administrador) ---------- */

const formIntegracao = document.getElementById("form-integracao");
const integracaoErro = document.getElementById("integracao-erro");
const integracaoOk = document.getElementById("integracao-ok");

function mostrarStatusIntegracao(estado) {
  const alvo = document.getElementById("integracao-status");
  if (!estado.gemini_configurada) {
    alvo.textContent = "Gemini ainda não configurado. A assistente e a classificação ficam indisponíveis.";
    alvo.className = "status-integracao pendente";
    return;
  }
  const origem = estado.origem === "banco" ? "chave salva pela tela" : "variável de ambiente";
  alvo.textContent = "Conectado (" + origem + "), modelo " + estado.modelo + ".";
  alvo.className = "status-integracao ok";
}

async function carregarIntegracoes() {
  const resposta = await fetchAuth("/integracoes");
  if (!resposta.ok) return;
  mostrarStatusIntegracao(await resposta.json());
}

formIntegracao.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  integracaoErro.classList.add("escondido");
  integracaoOk.classList.add("escondido");

  const modelo = document.getElementById("campo-modelo").value.trim();
  try {
    const resposta = await fetchAuth("/integracoes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        gemini_api_key: document.getElementById("campo-chave").value.trim(),
        ...(modelo ? { modelo } : {}),
      }),
    });

    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      throw new Error(corpo.detail || "Não foi possível salvar. Tente novamente.");
    }

    mostrarStatusIntegracao(await resposta.json());
    formIntegracao.reset();
    integracaoOk.textContent = "Configuração salva. Use o botão ao lado para testar a conexão.";
    integracaoOk.classList.remove("escondido");
  } catch (erro) {
    integracaoErro.textContent = erro.message;
    integracaoErro.classList.remove("escondido");
  }
});

document.getElementById("botao-testar").addEventListener("click", async () => {
  const botao = document.getElementById("botao-testar");
  integracaoErro.classList.add("escondido");
  integracaoOk.classList.add("escondido");
  botao.disabled = true;
  botao.textContent = "Testando…";

  try {
    const resposta = await fetchAuth("/integracoes/testar", { method: "POST" });
    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      throw new Error(corpo.detail || "Falha no teste de conexão.");
    }
    integracaoOk.textContent = "Conexão com o Gemini funcionando.";
    integracaoOk.classList.remove("escondido");
  } catch (erro) {
    integracaoErro.textContent = erro.message;
    integracaoErro.classList.remove("escondido");
  } finally {
    botao.disabled = false;
    botao.textContent = "Testar conexão";
  }
});

/* ---------- Status da API na barra lateral ---------- */

async function verificarSaude() {
  try {
    const resposta = await fetch("/saude");
    if (!resposta.ok) throw new Error();
    statusDot.className = "dot ok";
    statusTexto.textContent = "API no ar";
  } catch {
    statusDot.className = "dot erro";
    statusTexto.textContent = "API fora do ar";
  }
}

/* ---------- Assistente (chat) ---------- */

function adicionarBalao(texto, tipo, categoria) {
  const balao = document.createElement("div");
  balao.className = "balao " + tipo;

  const paragrafo = document.createElement("p");
  paragrafo.textContent = texto;
  balao.appendChild(paragrafo);

  if (categoria) {
    const etiqueta = document.createElement("span");
    etiqueta.className = "categoria";
    etiqueta.textContent = categoria;
    balao.appendChild(etiqueta);
  }

  conversa.appendChild(balao);
  conversa.scrollTop = conversa.scrollHeight;
  return balao;
}

// Carrega o histórico salvo no servidor, para a conversa continuar de onde parou.
async function carregarConversa() {
  const resposta = await fetchAuth("/historico");
  if (!resposta.ok) return;
  const itens = await resposta.json();
  for (const item of itens) {
    adicionarBalao(item.pergunta, "usuario");
    adicionarBalao(item.resposta, "assistente", item.categoria);
  }
}

formulario.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  const pergunta = campoPergunta.value.trim();
  if (!pergunta) return;

  mensagemErro.classList.add("escondido");
  botaoEnviar.disabled = true;
  campoPergunta.value = "";

  adicionarBalao(pergunta, "usuario");
  const digitando = adicionarBalao("A Tria está pensando…", "assistente digitando");

  try {
    const resposta = await fetchAuth("/perguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta }),
    });

    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      throw new Error(corpo.detail || "Não foi possível obter a resposta. Tente novamente.");
    }

    const item = await resposta.json();
    digitando.remove();
    adicionarBalao(item.resposta, "assistente", item.categoria);
  } catch (erro) {
    digitando.remove();
    mensagemErro.textContent = erro.message;
    mensagemErro.classList.remove("escondido");
    campoPergunta.value = pergunta; // devolve a pergunta para a pessoa tentar de novo
  } finally {
    botaoEnviar.disabled = false;
    campoPergunta.focus();
  }
});

/* ---------- Início ---------- */

carregarSessaoSalva();
if (sessao && sessao.token) {
  entrarNoPortal();
} else {
  mostrarLogin();
}
