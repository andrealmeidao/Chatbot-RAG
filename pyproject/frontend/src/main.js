const TOKEN_KEY = "rag_token";
const USER_KEY = "rag_user";
const CONV_KEY = "rag_conversation_id";

const state = {
  token: localStorage.getItem(TOKEN_KEY),
  user: JSON.parse(localStorage.getItem(USER_KEY) || "null"),
  conversationId: localStorage.getItem(CONV_KEY) || null,
  conversations: [],
  health: { documents: 0, chunks: 0, llm_configured: false },
  analytics: { total_questions: 0, top_questions: [], feedback: {} },
};

const app = document.getElementById("app");

function el(html) {
  const wrap = document.createElement("div");
  wrap.innerHTML = html.trim();
  return wrap.firstElementChild;
}

function headers(extra = {}) {
  const result = { ...extra };
  if (state.token) result.Authorization = `Bearer ${state.token}`;
  return result;
}

function errorMessage(data, fallback) {
  const detail = data && data.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0];
    if (typeof first === "string") return first;
    if (first && first.msg) return first.msg;
  }
  return fallback;
}

async function api(path, options = {}) {
  const opts = { ...options, headers: { ...headers(), ...(options.headers || {}) } };
  const response = await fetch(`/api${path}`, opts);
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    logout(false);
    throw new Error(errorMessage(data, "Sessao expirada"));
  }
  if (!response.ok) {
    throw new Error(errorMessage(data, "Falha na requisicao"));
  }
  return data;
}

function logout(callApi) {
  if (callApi && state.token) {
    fetch("/api/auth/logout", { method: "POST", headers: headers() }).catch(() => {});
  }
  state.token = null;
  state.user = null;
  state.conversationId = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(CONV_KEY);
  render();
}

function setSession(payload) {
  state.token = payload.token;
  state.user = payload.user;
  localStorage.setItem(TOKEN_KEY, payload.token);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

function renderAuth() {
  app.innerHTML = `
    <div class="auth-wrap">
      <div class="card auth-card">
        <h1>Chatbot RAG</h1>
        <p>Crie uma conta ou entre para consultar documentos e manter o historico.</p>
        <form id="auth-form">
          <div class="field">
            <label for="username">Usuario</label>
            <input id="username" name="username" autocomplete="username" placeholder="minimo 3 caracteres" />
          </div>
          <div class="field">
            <label for="password">Senha</label>
            <input id="password" name="password" type="password" autocomplete="new-password" placeholder="minimo 6 caracteres" />
          </div>
          <div class="auth-actions">
            <button type="submit" id="login">Entrar</button>
            <button type="button" class="secondary" id="register">Criar conta</button>
          </div>
          <p class="auth-hint">Usuario: letras e numeros. Senha: pelo menos 6 caracteres.</p>
          <p class="auth-error" id="auth-error"></p>
        </form>
      </div>
    </div>
  `;
  const error = document.getElementById("auth-error");
  async function submit(mode) {
    error.textContent = "";
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    if (username.length < 3) {
      error.textContent = "Usuario deve ter entre 3 e 40 caracteres";
      return;
    }
    if (password.length < 6) {
      error.textContent = "Senha deve ter ao menos 6 caracteres";
      return;
    }
    try {
      const payload = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      }).then(async (response) => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(errorMessage(data, "Falha na autenticacao"));
        }
        return data;
      });
      setSession(payload);
      render();
    } catch (err) {
      error.textContent = err.message;
    }
  }
  document.getElementById("auth-form").addEventListener("submit", (event) => {
    event.preventDefault();
    submit("login");
  });
  document.getElementById("register").addEventListener("click", () => submit("register"));
}

function renderShell() {
  app.innerHTML = `
    <header class="header">
      <div>
        <h1>Chatbot RAG</h1>
        <p>Respostas baseadas nos documentos indexados</p>
      </div>
      <div class="header-actions">
        <div class="badge" id="llm-badge">Modo local</div>
        <span class="user-chip">${state.user ? state.user.username : ""}</span>
        <button class="secondary" id="logout">Sair</button>
      </div>
    </header>
    <div class="layout">
      <aside class="card sidebar">
        <h2>Monitoramento</h2>
        <div class="stat-grid">
          <div class="stat"><span>Documentos</span><strong id="stat-docs">0</strong></div>
          <div class="stat"><span>Chunks</span><strong id="stat-chunks">0</strong></div>
          <div class="stat"><span>Perguntas</span><strong id="stat-questions">0</strong></div>
          <div class="stat"><span>Feedback +</span><strong id="stat-up">0</strong></div>
        </div>
        <h2>Conversas</h2>
        <button id="new-chat">Nova conversa</button>
        <div class="conv-list" id="conversations"></div>
        <h2>Upload</h2>
        <form class="upload" id="upload-form">
          <input type="file" id="file" accept=".txt,.md,.pdf,.docx,.csv" />
          <button type="submit">Indexar documento</button>
        </form>
        <h2>Perguntas comuns</h2>
        <ol class="top-list" id="top-questions"></ol>
      </aside>
      <section class="card chat">
        <h2>Conversa</h2>
        <div class="examples" id="examples"></div>
        <div class="messages" id="messages"></div>
        <form class="composer" id="chat-form">
          <input id="question" placeholder="Pergunte sobre uma secao do documento..." autocomplete="off" />
          <button type="submit">Enviar</button>
        </form>
      </section>
    </div>
  `;
}

function addMessage(role, text, extra = "") {
  const box = document.getElementById("messages");
  const node = el(`<div class="bubble ${role}"></div>`);
  node.textContent = text;
  if (extra) {
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = extra;
    node.appendChild(meta);
  }
  box.appendChild(node);
  box.scrollTop = box.scrollHeight;
  return node;
}

function renderConversations() {
  const list = document.getElementById("conversations");
  if (!list) return;
  list.innerHTML = "";
  state.conversations.forEach((item) => {
    const btn = document.createElement("button");
    btn.className = `conv-item ${item.id === state.conversationId ? "active" : ""}`;
    btn.type = "button";
    btn.textContent = item.title || "Nova conversa";
    btn.addEventListener("click", () => loadConversation(item.id));
    list.appendChild(btn);
  });
}

async function refreshMeta() {
  const health = await api("/health");
  const analytics = await api("/analytics");
  const convs = await api("/conversations");
  state.health = health;
  state.analytics = analytics;
  state.conversations = convs.conversations || [];
  document.getElementById("stat-docs").textContent = health.documents;
  document.getElementById("stat-chunks").textContent = health.chunks;
  document.getElementById("stat-questions").textContent = analytics.total_questions;
  document.getElementById("stat-up").textContent = analytics.feedback["1"] || 0;
  document.getElementById("llm-badge").textContent = health.llm_configured ? "OpenAI conectado" : "Modo local";
  const list = document.getElementById("top-questions");
  list.innerHTML = "";
  (analytics.top_questions || []).slice(0, 5).forEach((item) => {
    const li = document.createElement("li");
    li.textContent = `${item.question} (${item.count})`;
    list.appendChild(li);
  });
  renderConversations();
}

async function loadConversation(conversationId) {
  state.conversationId = conversationId;
  localStorage.setItem(CONV_KEY, conversationId);
  const box = document.getElementById("messages");
  box.innerHTML = "";
  const data = await api(`/history/${conversationId}`);
  if (!data.messages.length) {
    addMessage("bot", "Conversa vazia. Envie uma pergunta sobre os documentos indexados.");
  } else {
    data.messages.forEach((msg) => {
      addMessage("user", msg.question);
      addMessage("bot", msg.answer, `fontes: ${msg.sources || "nenhuma"} | confianca: ${msg.confidence}`);
    });
  }
  renderConversations();
}

async function startNewConversation() {
  const created = await api("/conversations", {
    method: "POST",
    headers: { ...headers(), "Content-Type": "application/json" },
    body: JSON.stringify({ title: "Nova conversa" }),
  });
  state.conversationId = created.id;
  localStorage.setItem(CONV_KEY, created.id);
  document.getElementById("messages").innerHTML = "";
  addMessage("bot", "Nova conversa iniciada.");
  await refreshMeta();
}

async function sendQuestion(question) {
  addMessage("user", question);
  const waiting = addMessage("bot", "Consultando a base...");
  try {
    const data = await api("/chat", {
      method: "POST",
      headers: { ...headers(), "Content-Type": "application/json" },
      body: JSON.stringify({ question, conversation_id: state.conversationId }),
    });
    state.conversationId = data.conversation_id;
    localStorage.setItem(CONV_KEY, data.conversation_id);
    waiting.textContent = data.answer;
    const extra = `fontes: ${data.sources.join(", ") || "nenhuma"} | confianca: ${data.confidence}`;
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent = extra;
    waiting.appendChild(meta);
    const fb = el(`<div class="feedback">
      <button type="button" data-rating="1">util</button>
      <button type="button" class="secondary" data-rating="-1">nao util</button>
    </div>`);
    fb.querySelectorAll("button").forEach((btn) => {
      btn.addEventListener("click", async () => {
        await api("/feedback", {
          method: "POST",
          headers: { ...headers(), "Content-Type": "application/json" },
          body: JSON.stringify({ message_id: data.message_id, rating: Number(btn.dataset.rating) }),
        });
        btn.textContent = "registrado";
        refreshMeta();
      });
    });
    waiting.appendChild(fb);
    await refreshMeta();
  } catch (err) {
    waiting.textContent = err.message;
  }
}

function bind() {
  const examples = [
    "EXPLICACAO DO FUNCIONAMENTO",
    "Qual e a politica de refund?",
    "Quanto de ferias tenho direito?",
    "Qual desconto para compra em bulk?",
  ];
  const wrap = document.getElementById("examples");
  examples.forEach((text) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = text;
    btn.addEventListener("click", () => sendQuestion(text));
    wrap.appendChild(btn);
  });
  document.getElementById("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.getElementById("question");
    const question = input.value.trim();
    if (!question) return;
    input.value = "";
    sendQuestion(question);
  });
  document.getElementById("upload-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const file = document.getElementById("file").files[0];
    if (!file) return;
    const body = new FormData();
    body.append("file", file);
    try {
      const data = await api("/upload", { method: "POST", headers: headers(), body });
      addMessage("bot", `Documento ${data.filename} indexado (${data.chunks} chunks).`);
      await refreshMeta();
    } catch (err) {
      addMessage("bot", err.message);
    }
  });
  document.getElementById("new-chat").addEventListener("click", startNewConversation);
  document.getElementById("logout").addEventListener("click", () => logout(true));
}

async function renderApp() {
  renderShell();
  bind();
  try {
    await refreshMeta();
    if (state.conversationId) {
      await loadConversation(state.conversationId);
    } else {
      addMessage("bot", `Ola, ${state.user.username}. Pergunte por uma secao, por exemplo "explicacao do funcionamento".`);
    }
  } catch (err) {
    addMessage("bot", err.message);
  }
}

function render() {
  if (!state.token) {
    renderAuth();
    return;
  }
  renderApp();
}

render();
