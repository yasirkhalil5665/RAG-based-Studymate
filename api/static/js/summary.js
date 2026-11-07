import { post } from "./api.js";
import { getScope } from "./library.js";
import { $, busy, download, esc, md, toast } from "./utils.js";

let style = "";

function renderStyles(styles) {
  style = style || styles[0];
  $("#sumStyle").innerHTML = styles
    .map((s) => `<button type="button" role="radio" aria-checked="${s === style}" data-style="${esc(s)}">${esc(s)}</button>`)
    .join("");
}

export function initSummary(styles) {
  renderStyles(styles);
  $("#sumArea").innerHTML = '<div class="empty-state">Pick one document in Study scope, then summarize it.</div>';

  $("#sumStyle").addEventListener("click", (e) => {
    const button = e.target.closest("button");
    if (!button) return;
    style = button.dataset.style;
    renderStyles(styles);
  });

  $("#sumGo").addEventListener("click", (e) => {
    if (!getScope()) { toast("Pick one document under Study scope first.", "error"); return; }
    const area = $("#sumArea");
    area.innerHTML = '<div class="skeleton"><i></i><i></i><i></i><i></i><i></i><i></i></div>';
    busy(e.currentTarget, "Summarizing", async () => {
      const { summary } = await post("/api/summary", { scope: getScope(), style });
      area.innerHTML = `<div class="prose">${md(summary)}</div>
        <div class="below"><button class="btn ghost" id="copySum">Copy</button>
        <button class="btn ghost" id="saveSum">Download as Markdown</button></div>`;
      $("#copySum").onclick = async () => {
        await navigator.clipboard.writeText(summary);
        toast("Copied to clipboard.");
      };
      $("#saveSum").onclick = () => download("summary.md", summary);
    }).then((result) => {
      if (result === undefined && area.querySelector(".skeleton")) {
        area.innerHTML = '<div class="empty-state">Pick one document in Study scope, then summarize it.</div>';
      }
    });
  });
}
