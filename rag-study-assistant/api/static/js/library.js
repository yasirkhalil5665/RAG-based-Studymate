import { api, remove } from "./api.js";
import { $, esc, icons, toast } from "./utils.js";

let docs = [];

export const getScope = () => $("#scope").value || null;

export async function loadDocs() {
  docs = await api("/api/documents");
  const keep = getScope();
  $("#scope").innerHTML =
    '<option value="">All documents</option>' +
    docs.map((d) => `<option value="${esc(d.source)}">${esc(d.name)}</option>`).join("");
  if (docs.some((d) => d.source === keep)) $("#scope").value = keep;
  $("#docs").innerHTML = docs
    .map((d, i) =>
      `<li>${icons.file}<span class="name" title="${esc(d.name)}">${esc(d.name)}</span>` +
      `<button data-i="${i}" aria-label="Remove ${esc(d.name)}" title="Remove">${icons.remove}</button></li>`)
    .join("");
  $("#docCount").textContent = docs.length;
  $("#docsEmpty").hidden = docs.length > 0;
  $("#notice").hidden = docs.length > 0;
}

async function upload(files) {
  const list = [...files];
  if (!list.length) return;
  const zone = $("#dropzone");
  const body = new FormData();
  list.forEach((f) => body.append("files", f));
  zone.classList.add("busy");
  $("#dropTitle").textContent = `Adding ${list.length} file${list.length > 1 ? "s" : ""}`;
  $("#dropHint").textContent = "Reading and indexing, this can take a minute";
  try {
    const result = await api("/api/documents", { method: "POST", body });
    await loadDocs();
    const skipped = result.skipped.length ? ` Skipped: ${result.skipped.join("; ")}` : "";
    toast(`Added ${result.added.length} document${result.added.length === 1 ? "" : "s"}.${skipped}`);
  } catch (error) {
    toast(error.message, "error");
  } finally {
    zone.classList.remove("busy");
    $("#dropTitle").textContent = "Add PDFs";
    $("#dropHint").textContent = "Browse or drop files here";
    $("#file").value = "";
  }
}

export function initLibrary() {
  const zone = $("#dropzone");
  $("#file").addEventListener("change", (e) => upload(e.target.files));
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
    if (!confirm(`Remove "${doc.name}" from the library?`)) return;
    try {
      await remove(`/api/documents?source=${encodeURIComponent(doc.source)}`);
      await loadDocs();
    } catch (error) {
      toast(error.message, "error");
    }
  });
}
