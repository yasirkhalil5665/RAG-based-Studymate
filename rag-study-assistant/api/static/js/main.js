import { api } from "./api.js";
import { initCards } from "./cards.js";
import { initChat } from "./chat.js";
import { initLibrary, loadDocs } from "./library.js";
import { initQuiz } from "./quiz.js";
import { initSummary } from "./summary.js";
import { $, toast } from "./utils.js";

const titles = {
  chat: ["Chat", "Ask questions about your lectures."],
  cards: ["Flashcards", "Review key concepts one card at a time."],
  quiz: ["Quiz", "Test yourself with multiple-choice questions."],
  summary: ["Summary", "Turn a whole lecture into short notes."],
};

function initTabs() {
  const tabs = document.querySelectorAll(".tabs button");
  tabs.forEach((tab) =>
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.setAttribute("aria-selected", String(t === tab)));
      document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("on", p.id === `tab-${tab.dataset.tab}`));
      const [title, sub] = titles[tab.dataset.tab];
      $("#pageTitle").textContent = title;
      $("#pageSub").textContent = sub;
    }));
}

async function start() {
  initTabs();
  initLibrary();
  initChat();
  initCards();
  initQuiz();
  try {
    const config = await api("/api/config");
    $("#cardN").max = config.max_items;
    $("#quizN").max = config.max_items;
    initSummary(config.summary_styles);
    await loadDocs();
  } catch (error) {
    toast(error.message, "error");
  }
}

start();
