import { post } from "./api.js";
import { getScope } from "./library.js";
import { $, busy, esc } from "./utils.js";

let quiz = { questions: [], picks: {}, done: false };

function render() {
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
      if (done) state = j === q.answer ? "right" : (picks[k] === j ? "wrong" : "");
      return `<label class="option ${state} ${done ? "locked" : ""}">
        <input type="radio" name="q${k}" value="${j}" ${picks[k] === j ? "checked" : ""} ${done ? "disabled" : ""}>
        <span class="badge">${"ABCD"[j] || j + 1}</span><span>${esc(option)}</span></label>`;
    }).join("");
    const note = done && q.explanation ? `<p class="expl">${esc(q.explanation)}</p>` : "";
    return `<div class="qbox"><h3>${k + 1}. ${esc(q.question)}</h3>${options}${note}</div>`;
  }).join("");

  const header = done
    ? `<div class="summary-bar ${percent >= 70 ? "good" : ""}"><strong>${score} / ${questions.length} correct (${percent}%)</strong>
       <span class="hint">Questions are written by AI. Check the cited page if unsure.</span></div>`
    : "";
  const footer = done ? "" : `<div class="below"><button class="btn" id="submitQuiz">Submit answers</button></div>`;
  area.innerHTML = `${header}<div class="qlist">${boxes}</div>${footer}`;

  area.querySelectorAll("input[type=radio]").forEach((input) =>
    input.addEventListener("change", () => { picks[Number(input.name.slice(1))] = Number(input.value); }));
  const submit = $("#submitQuiz", area);
  if (submit) submit.onclick = () => { quiz.done = true; render(); area.scrollTop = 0; };
}

export function initQuiz() {
  render();
  $("#quizGo").addEventListener("click", (e) =>
    busy(e.currentTarget, "Writing questions", async () => {
      const result = await post("/api/quiz", {
        scope: getScope(), topic: $("#quizTopic").value, n: Number($("#quizN").value) || 5,
      });
      quiz = { questions: result.questions, picks: {}, done: false };
      render();
    }));
}
