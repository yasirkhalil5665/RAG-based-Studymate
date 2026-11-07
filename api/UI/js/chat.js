import { post, remove } from "./api.js";
import { getScope } from "./library.js";
import { $, esc, icons, md, toast } from "./utils.js";

const sessionId = localStorage.getItem("sid") || (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2));
localStorage.setItem("sid", sessionId);

let emptyState = "";

function addMessage(role, html) {
  $("#chatEmpty")?.remove();
  const row = document.createElement("div");
  row.className = `msg ${role}`;
  row.innerHTML = `<div class="avatar">${role === "user" ? "You" : "AI"}</div><div class="bubble">${html}</div>`;
  $("#msgs").append(row);
  $("#msgs").scrollTop = $("#msgs").scrollHeight;
  return $(".bubble", row);
}

function renderSources(bubble, sources) {
  if (!sources.length) return;
  const chips = document.createElement("div");
  chips.className = "chips";
  const snippet = document.createElement("div");
  snippet.className = "snippet";
  snippet.hidden = true;
  let open = -1;
  sources.forEach((s, i) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.setAttribute("aria-expanded", "false");
    chip.innerHTML = `${icons.file}${esc(s.file)} · p.${s.page}`;
    chip.addEventListener("click", () => {
      chips.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-expanded", "false"));
      if (open === i) { snippet.hidden = true; open = -1; return; }
      chip.setAttribute("aria-expanded", "true");
      snippet.textContent = `${s.text}…`;
      snippet.hidden = false;
      open = i;
    });
    chips.append(chip);
  });
  bubble.append(chips, snippet);
}

async function send(question) {
  addMessage("user", `<p>${esc(question)}</p>`);
  const bubble = addMessage("bot", '<span class="typing"><i></i><i></i><i></i></span>');
  $("#sendBtn").disabled = true;
  try {
    const result = await post("/api/chat", { session_id: sessionId, question, scope: getScope() });
    bubble.innerHTML = md(result.answer);
    renderSources(bubble, result.sources);
  } catch (error) {
    bubble.closest(".msg").remove();
    toast(error.message, "error");
  } finally {
    $("#sendBtn").disabled = false;
    $("#msgs").scrollTop = $("#msgs").scrollHeight;
    $("#question").focus();
  }
}

export function initChat() {
  const input = $("#question");
  emptyState = $("#msgs").innerHTML;

  const grow = () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
  };
  const submit = () => {
    const question = input.value.trim();
    if (!question || $("#sendBtn").disabled) return;
    input.value = "";
    grow();
    send(question);
  };

  $("#chatForm").addEventListener("submit", (e) => { e.preventDefault(); submit(); });
  input.addEventListener("input", grow);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
  });
  $("#msgs").addEventListener("click", (e) => {
    const suggestion = e.target.closest(".suggest button");
    if (suggestion) { input.value = suggestion.textContent; input.focus(); grow(); }
  });
  $("#clearBtn").addEventListener("click", async () => {
    $("#msgs").innerHTML = emptyState;
    try { await remove(`/api/chat/${encodeURIComponent(sessionId)}`); } catch { /* ignore */ }
  });
}
