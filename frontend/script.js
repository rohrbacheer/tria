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

const NOME_PERFIL = { COLABORADOR: "Colaboradora(or)", TECNICO: "Técnico de TI" };

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

  // Zera a conversa (fica só a saudação) e carrega o histórico do usuário logado.
  conversa.querySelectorAll(".balao:not(#saudacao)").forEach((b) => b.remove());
  verificarSaude();
  carregarConversa();
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
  historico: "Histórico de perguntas",
  sobre: "Sobre o projeto",
};

document.querySelectorAll(".menu-item").forEach((botao) => {
  botao.addEventListener("click", () => {
    document.querySelectorAll(".menu-item").forEach((b) => b.classList.remove("ativo"));
    botao.classList.add("ativo");

    const view = botao.dataset.view;
    document.querySelectorAll(".view").forEach((v) => v.classList.add("escondido"));
    document.getElementById("view-" + view).classList.remove("escondido");
    document.getElementById("titulo-pagina").textContent = TITULOS[view];

    if (view === "historico") carregarTabelaHistorico();
  });
});

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
