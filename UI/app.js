// ---------- helpers ----------
const $ = (selector, root = document) => root.querySelector(selector);

const esc = (value) =>
  String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const FILE_ICON = '<svg viewBox="0 0 24 24"><path d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>';
const X_ICON = '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>';
const CHECK_ICON = '<svg viewBox="0 0 24 24"><path d="M4.5 12.75l6 6 9-13.5"/></svg>';
const COPY_ICON = '<svg viewBox="0 0 24 24"><path d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184"/></svg>';
const BOOK_ICON = '<svg viewBox="0 0 24 24"><path d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25"/></svg>';

function md(text) {
  const inline = (t) => t.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/`(.+?)`/g, "<code>$1</code>");
  let html = "";
  let inList = false;
  for (const raw of esc(text).split("\n")) {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*•]\s+(.*)/);
    if (bullet) {
      if (!inList) { html += "<ul>"; inList = true; }
      html += `<li>${inline(bullet[1])}</li>`;
      continue;
    }
    if (inList) { html += "</ul>"; inList = false; }
    const heading = line.match(/^#{1,6}\s+(.*)/);
    if (heading) html += `<h3>${inline(heading[1])}</h3>`;
    else if (line.trim()) html += `<p>${inline(line)}</p>`;
  }
  return html + (inList ? "</ul>" : "");
}

let toastTimer;
function toast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = "toast show" + (isError ? " error" : "");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 5000);
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(typeof data?.detail === "string" ? data.detail : `Request failed (${response.status})`);
  }
  return data;
}

const post = (path, body) =>
  api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

async function busy(button, label, task) {
  const original = button.textContent;
  button.disabled = true;
  button.classList.add("loading");
  button.textContent = label;
  try {
    return await task();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
    button.classList.remove("loading");
    button.textContent = original;
  }
}

async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    toast("Copied to clipboard.");
  } catch {
    toast("Could not copy. Select the text and copy it manually.", true);
  }
}

function download(name, text) {
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([text], { type: "text/plain" }));
  link.download = name;
  link.click();
  URL.revokeObjectURL(link.href);
}

// ---------- library ----------
let docs = [];
const scope = () => $("#scope").value || null;

function updateScopeHint() {
  const doc = docs.find((d) => d.source === scope());
  $("#scopeHint").textContent = doc
    ? `Searching in ${doc.name}`
    : `Searching all ${docs.length} document${docs.length === 1 ? "" : "s"}`;
}

async function loadDocs() {
  docs = await api("/api/documents");
  const keep = scope();
  $("#scope").innerHTML =
    '<option value="">All documents</option>' +
    docs.map((d) => `<option value="${esc(d.source)}">${esc(d.name)}</option>`).join("");
  if (docs.some((d) => d.source === keep)) $("#scope").value = keep;

  $("#docs").innerHTML = docs
    .map((d, i) =>
      `<li><span class="doc-icon">${FILE_ICON}</span>` +
      `<div class="doc-info"><span class="name" title="${esc(d.name)}">${esc(d.name)}</span>` +
      `<span class="doc-meta">${CHECK_ICON}Indexed</span></div>` +
      `<button data-i="${i}" aria-label="Remove ${esc(d.name)}" title="Remove">${X_ICON}</button></li>`)
    .join("");
  $("#docCount").textContent = docs.length;
  $("#docsEmpty").hidden = docs.length > 0;
  $("#notice").hidden = docs.length > 0;
  updateScopeHint();
}

async function upload(files) {
  const list = [...files];
  if (!list.length) return;
  const zone = $("#dropzone");
  const body = new FormData();
  list.forEach((f) => body.append("files", f));

  zone.classList.add("busy");
  $("#dropTitle").textContent = `Adding ${list.length} file${list.length > 1 ? "s" : ""}`;
  $("#dropHint").textContent = "Reading and indexing. Scanned PDFs can take a few minutes";
  try {
    const result = await api("/api/documents", { method: "POST", body });
    await loadDocs();
    const skipped = result.skipped.length ? ` Skipped: ${result.skipped.join("; ")}` : "";
    toast(`Added ${result.added.length} document${result.added.length === 1 ? "" : "s"}.${skipped}`);
  } catch (error) {
    toast(error.message, true);
  } finally {
    zone.classList.remove("busy");
    $("#dropTitle").textContent = "Add lecture PDFs";
    $("#dropHint").textContent = "Browse files or drag & drop";
    $("#file").value = "";
  }
}

function setupLibrary() {
  const zone = $("#dropzone");
  $("#file").addEventListener("change", (e) => upload(e.target.files));
  $("#scope").addEventListener("change", updateScopeHint);
  zone.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("#file").click(); }
  });
  ["dragenter", "dragover"].forEach((name) =>
    zone.addEventListener(name, (e) => { e.preventDefault(); zone.classList.add("over"); }));
  ["dragleave", "drop"].forEach((name) =>
    zone.addEventListener(name, (e) => { e.preventDefault(); zone.classList.remove("over"); }));
  zone.addEventListener("drop", (e) => upload(e.dataTransfer.files));

  $("#docs").addEventListener("click", async (e) => {
    const button = e.target.closest("button");
    if (!button) return;
    const doc = docs[Number(button.dataset.i)];
    const note = doc.source.startsWith("data/")
      ? "\n\nIt lives in the data folder, so it returns on restart unless you delete the file."
      : "";
    if (!confirm(`Remove "${doc.name}" from the library?${note}`)) return;
    try {
      await api(`/api/documents?source=${encodeURIComponent(doc.source)}`, { method: "DELETE" });
      await loadDocs();
    } catch (error) {
      toast(error.message, true);
    }
  });
}

// ---------- chat ----------
const sessionId = localStorage.getItem("sid") || (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2));
localStorage.setItem("sid", sessionId);
let emptyChat = "";

function scrollFeed() {
  $("#msgs").scrollTop = $("#msgs").scrollHeight;
}

function addUser(text) {
  $("#chatEmpty")?.remove();
  const row = document.createElement("div");
  row.className = "turn user";
  row.innerHTML = `<div class="u-bubble"><p>${esc(text)}</p></div><div class="avatar-user">You</div>`;
  $("#msgs").append(row);
  scrollFeed();
}

function addAi() {
  const row = document.createElement("div");
  row.className = "turn ai";
  row.innerHTML = `<div class="avatar-ai">${BOOK_ICON}</div>
    <div class="ai-card">
      <div class="ai-head"><span class="ai-name">Studymate</span><span class="ai-meta" hidden></span></div>
      <div class="ai-body"><span class="typing"><i></i><i></i><i></i></span></div>
      <div class="ai-sources" hidden><div class="src-title">Source passages</div><div class="src-grid"></div></div>
      <div class="ai-actions" hidden><button type="button" class="link-btn">${COPY_ICON}Copy</button></div>
    </div>`;
  $("#msgs").append(row);
  scrollFeed();
  return {
    row,
    body: $(".ai-body", row),
    meta: $(".ai-meta", row),
    sources: $(".ai-sources", row),
    grid: $(".src-grid", row),
    actions: $(".ai-actions", row),
  };
}

function fillAnswer(ai, result) {
  ai.body.innerHTML = md(result.answer);
  if (/^i don['’]t know/i.test(result.answer.trim())) {
    ai.body.insertAdjacentHTML("beforeend",
      '<p class="idk-hint">Try a more specific question, or pick one lecture under Study scope.</p>');
  }
  if (result.sources.length) {
    ai.meta.textContent = `• ${result.sources.length} passages retrieved`;
    ai.meta.hidden = false;
    ai.grid.innerHTML = result.sources
      .map((s) =>
        `<button type="button" class="src-card" aria-expanded="false">
          <div class="src-top"><span class="src-file">${esc(s.file)}</span><span class="src-page">p. ${s.page}</span></div>
          <p class="src-text">“${esc(s.text)}…”</p></button>`)
      .join("");
    ai.grid.querySelectorAll(".src-card").forEach((card) =>
      card.addEventListener("click", () => {
        const open = card.classList.toggle("open");
        card.setAttribute("aria-expanded", String(open));
      }));
    ai.sources.hidden = false;
  }
  ai.actions.hidden = false;
  $(".link-btn", ai.actions).onclick = () => copyText(result.answer);
}

async function sendQuestion(question) {
  addUser(question);
  const ai = addAi();
  $("#sendBtn").disabled = true;
  try {
    const result = await post("/api/chat", { session_id: sessionId, question, scope: scope() });
    fillAnswer(ai, result);
  } catch (error) {
    ai.row.remove();
    toast(error.message, true);
  } finally {
    $("#sendBtn").disabled = false;
    scrollFeed();
    $("#question").focus();
  }
}

function setupChat() {
  const input = $("#question");
  emptyChat = $("#msgs").innerHTML;

  const grow = () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 128)}px`;
  };
  const submit = () => {
    const question = input.value.trim();
    if (!question || $("#sendBtn").disabled) return;
    input.value = "";
    grow();
    sendQuestion(question);
  };

  $("#chatForm").addEventListener("submit", (e) => { e.preventDefault(); submit(); });
  input.addEventListener("input", grow);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  });
  $("#msgs").addEventListener("click", (e) => {
    const card = e.target.closest("[data-prompt]");
    if (card) { input.value = card.dataset.prompt; input.focus(); grow(); }
  });
  $("#clearBtn").addEventListener("click", async () => {
    $("#msgs").innerHTML = emptyChat;
    await api(`/api/chat/${encodeURIComponent(sessionId)}`, { method: "DELETE" }).catch(() => {});
  });
}

// ---------- flashcards ----------
let deck = { cards: [], index: 0, revealed: false, missed: [] };

function renderCards() {
  const area = $("#cardArea");
  const { cards, index, revealed, missed } = deck;
  if (!cards.length) {
    area.innerHTML = '<div class="empty-state">Generate a deck to start studying.</div>';
    return;
  }

  let html;
  if (index < cards.length) {
    const card = cards[index];
    const body = revealed
      ? `<div class="a">${esc(card.a)}</div>
         <div class="actions"><button class="btn" id="knew">I knew it</button>
         <button class="btn ghost" id="again">Study again</button></div>`
      : '<div class="actions"><button class="btn" id="reveal">Show answer</button></div>';
    html = `<div class="progress"><i style="width:${(index / cards.length) * 100}%"></i></div>
      <div class="meta">Card ${index + 1} of ${cards.length}</div>
      <div class="card"><div class="q">${esc(card.q)}</div>${body}</div>`;
  } else {
    const redo = missed.length ? `<button class="btn" id="redo">Study ${missed.length} missed</button>` : "";
    html = `<div class="progress"><i style="width:100%"></i></div>
      <div class="card"><div class="q">You knew ${cards.length - missed.length} of ${cards.length} cards.</div>
      <div class="actions">${redo}</div></div>`;
  }
  html += '<div class="below"><button class="btn ghost" id="export">Export for Anki or Excel</button></div>';
  area.innerHTML = html;

  const on = (id, handler) => { const el = $(`#${id}`, area); if (el) el.onclick = handler; };
  const next = (wasMissed) => {
    if (wasMissed) deck.missed.push(cards[index]);
    deck.index += 1;
    deck.revealed = false;
    renderCards();
  };
  on("reveal", () => { deck.revealed = true; renderCards(); });
  on("knew", () => next(false));
  on("again", () => next(true));
  on("redo", () => { deck = { cards: missed, index: 0, revealed: false, missed: [] }; renderCards(); });
  on("export", () =>
    download("flashcards.tsv", cards.map((c) => `${c.q.replace(/\s+/g, " ")}\t${c.a.replace(/\s+/g, " ")}`).join("\n")));
}

function setupCards() {
  renderCards();
  $("#cardGo").addEventListener("click", (e) =>
    busy(e.currentTarget, "Creating cards", async () => {
      const result = await post("/api/flashcards", {
        scope: scope(), topic: $("#cardTopic").value, n: Number($("#cardN").value) || 10,
      });
      deck = { cards: result.cards, index: 0, revealed: false, missed: [] };
      renderCards();
    }));
}

// ---------- quiz ----------
let quiz = { questions: [], picks: {}, done: false };

function renderQuiz() {
  const area = $("#quizArea");
  const { questions, picks, done } = quiz;
  if (!questions.length) {
    area.innerHTML = '<div class="empty-state">Generate a quiz to test yourself.</div>';
    return;
  }

  const score = questions.filter((q, k) => picks[k] === q.answer).length;
  const percent = Math.round((score / questions.length) * 100);
  const boxes = questions.map((q, k) => {
    const options = q.options.map((option, j) => {
      let state = "";
      if (done) state = j === q.answer ? "right" : picks[k] === j ? "wrong" : "";
      return `<label class="option ${state} ${done ? "locked" : ""}">
        <input type="radio" name="q${k}" value="${j}" ${picks[k] === j ? "checked" : ""} ${done ? "disabled" : ""}>
        <span class="badge">${"ABCD"[j] || j + 1}</span><span>${esc(option)}</span></label>`;
    }).join("");
    const note = done && q.explanation ? `<p class="expl">${esc(q.explanation)}</p>` : "";
    return `<div class="qbox"><h3>${k + 1}. ${esc(q.question)}</h3>${options}${note}</div>`;
  }).join("");

  const header = done
    ? `<div class="result ${percent >= 70 ? "good" : ""}"><strong>${score} / ${questions.length} correct (${percent}%)</strong>
       <span class="hint">Questions are written by AI. Check the cited page if unsure.</span></div>`
    : "";
  const footer = done ? "" : '<div class="below"><button class="btn" id="submitQuiz">Submit answers</button></div>';
  area.innerHTML = `${header}<div class="qlist">${boxes}</div>${footer}`;

  area.querySelectorAll("input[type=radio]").forEach((input) =>
    input.addEventListener("change", () => { picks[Number(input.name.slice(1))] = Number(input.value); }));
  const submit = $("#submitQuiz", area);
  if (submit) submit.onclick = () => { quiz.done = true; renderQuiz(); area.scrollTop = 0; };
}

function setupQuiz() {
  renderQuiz();
  $("#quizGo").addEventListener("click", (e) =>
    busy(e.currentTarget, "Writing questions", async () => {
      const result = await post("/api/quiz", {
        scope: scope(), topic: $("#quizTopic").value, n: Number($("#quizN").value) || 5,
      });
      quiz = { questions: result.questions, picks: {}, done: false };
      renderQuiz();
    }));
}

// ---------- summary ----------
const SUMMARY_HINT = '<div class="empty-state">Pick one document in Study scope, then summarize it.</div>';
let summaryStyle = "";

function renderStyles(styles) {
  summaryStyle = summaryStyle || styles[0];
  $("#sumStyle").innerHTML = styles
    .map((s) => `<button type="button" role="radio" aria-checked="${s === summaryStyle}" data-style="${esc(s)}">${esc(s)}</button>`)
    .join("");
}

function setupSummary(styles) {
  const area = $("#sumArea");
  renderStyles(styles);
  area.innerHTML = SUMMARY_HINT;

  $("#sumStyle").addEventListener("click", (e) => {
    const button = e.target.closest("button");
    if (!button) return;
    summaryStyle = button.dataset.style;
    renderStyles(styles);
  });

  $("#sumGo").addEventListener("click", (e) => {
    if (!scope()) { toast("Pick one document under Study scope first.", true); return; }
    area.innerHTML = '<div class="skeleton"><i></i><i></i><i></i><i></i><i></i><i></i></div>';
    busy(e.currentTarget, "Summarizing", async () => {
      const { summary } = await post("/api/summary", { scope: scope(), style: summaryStyle });
      area.innerHTML = `<div class="prose">${md(summary)}</div>
        <div class="below"><button class="btn ghost" id="copySum">Copy</button>
        <button class="btn ghost" id="saveSum">Download as Markdown</button></div>`;
      $("#copySum").onclick = () => copyText(summary);
      $("#saveSum").onclick = () => download("summary.md", summary);
    }).then(() => {
      if (area.querySelector(".skeleton")) area.innerHTML = SUMMARY_HINT;
    });
  });
}

// ---------- tabs and start ----------
const TITLES = {
  chat: ["Chat", "Cites your PDFs"],
  cards: ["Flashcards", "Made from your notes"],
  quiz: ["Practice quiz", "Written by AI"],
  summary: ["Summary", "Whole lecture, in short notes"],
};

function setupTabs() {
  const tabs = document.querySelectorAll(".modes button");
  tabs.forEach((tab) =>
    tab.addEventListener("click", () => {
      const name = tab.dataset.tab;
      tabs.forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
      document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("on", p.id === `tab-${name}`));
      $("#pageTitle").textContent = TITLES[name][0];
      $("#pill").textContent = TITLES[name][1];
    }));
}

async function start() {
  if (location.protocol === "file:") {
    $("#fileWarn").hidden = false;
    return;
  }
  setupTabs();
  setupLibrary();
  setupChat();
  setupCards();
  setupQuiz();
  try {
    const config = await api("/api/config");
    $("#cardN").max = $("#quizN").max = config.max_items;
    $("#ocrNote").textContent = config.ocr ? "Scanned pages are read with OCR" : "OCR is off: scanned pages can't be read";
    setupSummary(config.summary_styles);
    await loadDocs();
  } catch (error) {
    toast(error.message, true);
  }
}

start();
