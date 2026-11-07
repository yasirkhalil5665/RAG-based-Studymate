import { post } from "./api.js";
import { getScope } from "./library.js";
import { $, busy, download, esc } from "./utils.js";

let deck = { cards: [], index: 0, revealed: false, missed: [] };

function render() {
  const area = $("#cardArea");
  const { cards, index } = deck;
  if (!cards.length) {
    area.innerHTML = '<div class="empty-state">Generate a deck to start studying.</div>';
    return;
  }
  let html;
  if (index < cards.length) {
    const card = cards[index];
    html = `<div class="progress"><i style="width:${(index / cards.length) * 100}%"></i></div>
      <div class="meta">Card ${index + 1} of ${cards.length}</div>
      <div class="card"><div class="q">${esc(card.q)}</div>` +
      (deck.revealed
        ? `<div class="a">${esc(card.a)}</div>
           <div class="actions"><button class="btn" id="knew">I knew it</button>
           <button class="btn ghost" id="again">Study again</button></div>`
        : `<div class="actions"><button class="btn" id="reveal">Show answer</button>
           <span class="hint">or press Space</span></div>`) +
      "</div>";
  } else {
    const known = cards.length - deck.missed.length;
    html = `<div class="progress"><i style="width:100%"></i></div>
      <div class="card"><div class="q">You knew ${known} of ${cards.length} cards.</div>
      <div class="actions">${deck.missed.length ? `<button class="btn" id="redo">Study ${deck.missed.length} missed</button>` : ""}</div></div>`;
  }
  html += '<div class="below"><button class="btn ghost" id="export">Export for Anki or Excel</button></div>';
  area.innerHTML = html;

  const on = (id, handler) => { const el = $(`#${id}`, area); if (el) el.onclick = handler; };
  on("reveal", reveal);
  on("knew", () => next(false));
  on("again", () => next(true));
  on("redo", () => { deck = { cards: deck.missed, index: 0, revealed: false, missed: [] }; render(); });
  on("export", () => download("flashcards.tsv", cards.map((c) => `${c.q.replace(/\s+/g, " ")}\t${c.a.replace(/\s+/g, " ")}`).join("\n")));
}

function reveal() { deck.revealed = true; render(); }

function next(missed) {
  if (missed) deck.missed.push(deck.cards[deck.index]);
  deck.index += 1;
  deck.revealed = false;
  render();
}

export function initCards() {
  render();
  $("#cardGo").addEventListener("click", (e) =>
    busy(e.currentTarget, "Creating cards", async () => {
      const result = await post("/api/flashcards", {
        scope: getScope(), topic: $("#cardTopic").value, n: Number($("#cardN").value) || 10,
      });
      deck = { cards: result.cards, index: 0, revealed: false, missed: [] };
      render();
    }));
  document.addEventListener("keydown", (e) => {
    const typing = /INPUT|TEXTAREA|SELECT|BUTTON/.test(e.target.tagName);
    if (e.code === "Space" && !typing && $("#tab-cards").classList.contains("on")
        && deck.cards.length && deck.index < deck.cards.length && !deck.revealed) {
      e.preventDefault();
      reveal();
    }
  });
}
