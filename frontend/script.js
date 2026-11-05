// Interface do PUCHUB — conversa com a API via fetch (mesma origem, sem CORS).
// A sessão (token + nome + perfil) vem do POST /login e vai no cabeçalho Authorization.

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

const SESSAO_CHAVE = "puchub_sessao";
let sessao = null; // { token, nome, perfil }

const NOME_PERFIL = { USUARIO: "Usuária(o)", TECNICO: "Técnico de TI", ADMIN: "Administradora(or)" };

// Perfis que enxergam a fila inteira de chamados (e a coluna Solicitante).
function veAFilaInteira() {
  return sessao.perfil === "TECNICO" || sessao.perfil === "ADMIN";
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
  document.getElementById("usuario-nome").textContent = sessao.nome;
  document.getElementById("usuario-perfil").textContent = NOME_PERFIL[sessao.perfil] || sessao.perfil;

  // Áreas administrativas aparecem só para o administrador.
  document
    .querySelectorAll(".somente-admin")
    .forEach((el) => el.classList.toggle("escondido", sessao.perfil !== "ADMIN"));

  // Sempre entra pelo Assistente — evita o novo perfil cair numa tela que não é dele.
  document.querySelectorAll(".menu-item").forEach((b) => b.classList.remove("ativo"));
  document.querySelector('.menu-item[data-view="assistente"]').classList.add("ativo");
  document.querySelectorAll(".view").forEach((v) => v.classList.add("escondido"));
  document.getElementById("view-assistente").classList.remove("escondido");
  document.getElementById("titulo-pagina").textContent = TITULOS.assistente;

  // Zera a conversa (fica só a saudação) e carrega o histórico do usuário logado.
  conversa.querySelectorAll(".balao:not(#saudacao)").forEach((b) => b.remove());
  verificarSaude();
  carregarConversa();
  carregarOpcoes();
}

// Com o token inválido ou expirado, qualquer chamada volta 401: cai para a tela de login.
async function fetchAuth(url, opcoes = {}) {
  opcoes.headers = { ...(opcoes.headers || {}), Authorization: "Bearer " + sessao.token };
  const resposta = await fetch(url, opcoes);
  if (resposta.status === 401) {
    mostrarLogin("Sua sessão expirou. Entre de novo.");
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
  assistente: "Assistente Virtual",
  abrir: "Abrir chamado",
  chamados: "Chamados",
  historico: "Histórico de perguntas",
  integracoes: "Integrações",
  sobre: "Sobre o projeto",
};

function tituloDaView(view) {
  if (view === "chamados") {
    return veAFilaInteira() ? "Fila de chamados" : "Meus chamados";
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
    if (view === "chamados") carregarChamados();
    if (view === "integracoes") carregarIntegracoes();
  });
});

/* ---------- Integrações (área do técnico) ---------- */

const formIntegracao = document.getElementById("form-integracao");
const integracaoErro = document.getElementById("integracao-erro");
const integracaoOk = document.getElementById("integracao-ok");

function mostrarStatusIntegracao(estado) {
  const alvo = document.getElementById("integracao-status");
  if (!estado.gemini_configurada) {
    alvo.textContent = "⚠ Gemini ainda não configurado — o assistente e a triagem ficam indisponíveis.";
    alvo.className = "status-integracao pendente";
    return;
  }
  const origem = estado.origem === "banco" ? "chave salva pela tela" : "variável de ambiente";
  alvo.textContent = `✓ Gemini configurado (${origem}) · modelo ${estado.modelo}`;
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
    integracaoOk.textContent = "Conexão com o Gemini funcionando. ✔";
    integracaoOk.classList.remove("escondido");
  } catch (erro) {
    integracaoErro.textContent = erro.message;
    integracaoErro.classList.remove("escondido");
  } finally {
    botao.disabled = false;
    botao.textContent = "Testar conexão";
  }
});

/* ---------- Abrir chamado ---------- */

// As opções de classificação vêm da API (as mesmas listas que a IA conhece).
async function carregarOpcoes() {
  const resposta = await fetchAuth("/opcoes");
  if (!resposta.ok) return;
  const opcoes = await resposta.json();

  const selectCategoria = document.getElementById("categoria");
  const selectPrioridade = document.getElementById("prioridade");
  selectCategoria.innerHTML = "";
  selectPrioridade.innerHTML = "";

  for (const categoria of opcoes.categorias) {
    selectCategoria.add(new Option(categoria, categoria));
  }
  for (const prioridade of opcoes.prioridades) {
    selectPrioridade.add(new Option(prioridade, prioridade));
  }
  selectPrioridade.value = "Média"; // ponto de partida mais comum
}

const formChamado = document.getElementById("form-chamado");
const botaoAbrir = document.getElementById("botao-abrir");
const chamadoErro = document.getElementById("chamado-erro");
const chamadoResultado = document.getElementById("chamado-resultado");

function classeDePrioridade(prioridade) {
  return "pill pill-" + prioridade.toLowerCase().replace("é", "e");
}

formChamado.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  chamadoErro.classList.add("escondido");
  chamadoResultado.classList.add("escondido");
  botaoAbrir.disabled = true;
  botaoAbrir.textContent = "A IA está escrevendo a orientação…";

  try {
    const resposta = await fetchAuth("/chamados", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        titulo: document.getElementById("titulo").value.trim(),
        descricao: document.getElementById("descricao").value.trim(),
        categoria: document.getElementById("categoria").value,
        prioridade: document.getElementById("prioridade").value,
      }),
    });

    if (!resposta.ok) {
      const corpo = await resposta.json().catch(() => ({}));
      throw new Error(corpo.detail || "Não foi possível abrir o chamado. Tente novamente.");
    }

    const chamado = await resposta.json();
    document.getElementById("resultado-protocolo").textContent =
      "Chamado #" + chamado.id + " aberto — " + chamado.titulo;
    document.getElementById("resultado-categoria").textContent = chamado.categoria;
    const pillPrioridade = document.getElementById("resultado-prioridade");
    pillPrioridade.textContent = "Prioridade " + chamado.prioridade;
    pillPrioridade.className = classeDePrioridade(chamado.prioridade);
    document.getElementById("resultado-orientacao").textContent = chamado.orientacao;
    chamadoResultado.classList.remove("escondido");
    formChamado.reset();
    document.getElementById("prioridade").value = "Média";
  } catch (erro) {
    chamadoErro.textContent = erro.message;
    chamadoErro.classList.remove("escondido");
  } finally {
    botaoAbrir.disabled = false;
    botaoAbrir.textContent = "Abrir chamado";
  }
});

/* ---------- Chamados (tabela) ---------- */

async function carregarChamados() {
  // A coluna Solicitante só faz sentido para quem vê a fila inteira (técnico e admin).
  document
    .getElementById("tabela-chamados")
    .classList.toggle("sem-solicitante", !veAFilaInteira());

  const resposta = await fetchAuth("/chamados");
  if (!resposta.ok) return;
  const chamados = await resposta.json();

  const corpo = document.getElementById("chamados-linhas");
  const vazio = document.getElementById("chamados-vazio");
  corpo.innerHTML = "";
  vazio.classList.toggle("escondido", chamados.length > 0);

  for (const chamado of chamados) {
    const linha = document.createElement("tr");

    const colunaId = document.createElement("td");
    colunaId.textContent = "#" + chamado.id;

    const colunaSolicitante = document.createElement("td");
    colunaSolicitante.className = "col-solicitante";
    colunaSolicitante.textContent = chamado.solicitante;

    const colunaTitulo = document.createElement("td");
    colunaTitulo.className = "col-pergunta";
    colunaTitulo.textContent = chamado.titulo;
    colunaTitulo.title = chamado.descricao; // a descrição completa aparece ao passar o mouse

    const colunaCategoria = document.createElement("td");
    const pillCategoria = document.createElement("span");
    pillCategoria.className = "pill";
    pillCategoria.textContent = chamado.categoria;
    colunaCategoria.appendChild(pillCategoria);

    const colunaPrioridade = document.createElement("td");
    const pillPrioridade = document.createElement("span");
    pillPrioridade.className = classeDePrioridade(chamado.prioridade);
    pillPrioridade.textContent = chamado.prioridade;
    colunaPrioridade.appendChild(pillPrioridade);

    const colunaStatus = document.createElement("td");
    colunaStatus.textContent = chamado.status;

    const colunaData = document.createElement("td");
    colunaData.className = "col-data";
    colunaData.textContent = new Date(chamado.criado_em).toLocaleString("pt-BR");

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
  const digitando = adicionarBalao("A assistente está pensando…", "assistente digitando");

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
    campoPergunta.value = pergunta; // devolve a pergunta para o usuário tentar de novo
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
