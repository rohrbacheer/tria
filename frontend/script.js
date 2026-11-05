// Interface do PUCHUB — conversa com a API via fetch (mesma origem, sem CORS).

const conversa = document.getElementById("conversa");
const formulario = document.getElementById("form-pergunta");
const campoPergunta = document.getElementById("pergunta");
const botaoEnviar = document.getElementById("botao-enviar");
const mensagemErro = document.getElementById("mensagem-erro");
const statusDot = document.getElementById("status-dot");
const statusTexto = document.getElementById("status-texto");

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
  const resposta = await fetch("/historico");
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
    const resposta = await fetch("/perguntar", {
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

verificarSaude();
carregarConversa();
