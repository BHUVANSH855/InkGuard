/* GrammarLens — frontend */

"use strict";

// ── Tabs ──────────────────────────────────────────
document.querySelectorAll(".gl-nav-link").forEach(link => {
  link.addEventListener("click", e => {
    e.preventDefault();
    const tab = link.dataset.tab;
    document.querySelectorAll(".gl-nav-link").forEach(l => l.classList.remove("active"));
    document.querySelectorAll(".gl-tab").forEach(t => { t.classList.add("hidden"); t.classList.remove("active"); });
    link.classList.add("active");
    const el = document.getElementById(`tab-${tab}`);
    if (el) { el.classList.remove("hidden"); el.classList.add("active"); }
  });
});

// ── Editor word count ─────────────────────────────
const editor   = document.getElementById("editor");
const wordCount = document.getElementById("wordCount");

editor.addEventListener("input", () => {
  const text = editor.innerText.trim();
  const n = text ? text.split(/\s+/).length : 0;
  wordCount.textContent = `${n} word${n !== 1 ? "s" : ""}`;
});

// ── Clear ─────────────────────────────────────────
document.getElementById("clearBtn").addEventListener("click", () => {
  editor.innerText = "";
  wordCount.textContent = "0 words";
  document.getElementById("resultsEmpty").style.display  = "flex";
  document.getElementById("resultsContent").classList.add("hidden");
});

// ── File upload ───────────────────────────────────
document.getElementById("fileInput").addEventListener("change", async e => {
  const file = e.target.files[0];
  if (!file) return;
  const text = await file.text();
  editor.innerText = text;
  editor.dispatchEvent(new Event("input"));
});

// ── Analyse ───────────────────────────────────────
document.getElementById("checkBtn").addEventListener("click", analyse);

async function analyse() {
  const text = editor.innerText.trim();
  if (!text) return;

  const btn = document.getElementById("checkBtn");
  btn.textContent = "Analysing…";
  btn.disabled = true;

  try {
    const res = await fetch("/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    renderResults(data);
  } catch {
    alert("Request failed. Is the server running?");
  } finally {
    btn.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg> Analyse`;
    btn.disabled = false;
  }
}

// ── Render ────────────────────────────────────────
function renderResults(data) {
  document.getElementById("resultsEmpty").style.display  = "none";
  document.getElementById("resultsContent").classList.remove("hidden");

  // Score ring
  const arc   = document.getElementById("scoreArc");
  const score = data.score ?? 0;
  const circ  = 163.4;
  arc.style.strokeDashoffset = circ - (score / 100) * circ;
  arc.style.stroke = score >= 90 ? "#4ade80" : score >= 70 ? "#fbbf24" : "#f87171";
  document.getElementById("scoreNum").textContent  = score;
  document.getElementById("scoreGrade").textContent = `Grade ${data.grade}`;
  document.getElementById("scoreSub").textContent  =
    `${data.error_count} issue${data.error_count !== 1 ? "s" : ""} in ${data.word_count} words`;

  // Category chips
  const chips = document.getElementById("categoryChips");
  chips.innerHTML = (data.categories || [])
    .map(c => `<span class="gl-chip">${c}</span>`).join("");

  // Highlighted text
  document.getElementById("highlightBox").innerHTML = data.highlighted || data.corrected;

  // Corrected
  document.getElementById("correctedBox").textContent = data.corrected;

  // Errors
  const badge = document.getElementById("errorBadge");
  badge.textContent = data.error_count;
  const list = document.getElementById("errorList");
  list.innerHTML = "";
  (data.errors || []).forEach((e, i) => {
    const card = document.createElement("div");
    card.className = "gl-error-card";
    card.dataset.cat = e.category || "agreement";
    card.style.animationDelay = `${i * 40}ms`;
    card.innerHTML = `
      <span class="gl-error-label err">Error</span>
      <span class="gl-error-value">"${escHtml(e.issue)}"</span>
      <span class="gl-error-label fix">Fix</span>
      <span class="gl-error-value">${escHtml(e.correction)}</span>
      <span class="gl-error-label why">Why</span>
      <span class="gl-error-value">${escHtml(e.message)}</span>
    `;
    list.appendChild(card);
  });

  // Store for export
  window._lastResult = data;
}

// ── Copy corrected ────────────────────────────────
document.getElementById("copyBtn").addEventListener("click", () => {
  const text = document.getElementById("correctedBox").textContent;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("copyBtn");
    btn.textContent = "Copied!";
    setTimeout(() => (btn.textContent = "Copy"), 1500);
  });
});

// ── Export ────────────────────────────────────────
document.getElementById("exportBtn").addEventListener("click", async () => {
  const text = editor.innerText.trim();
  if (!text) return;
  const res = await fetch("/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "grammarlens-report.json";
  a.click();
});

// ── Batch tab ─────────────────────────────────────
document.getElementById("batchRunBtn").addEventListener("click", async () => {
  const raw = document.getElementById("batchInput").value.trim();
  const out = document.getElementById("batchOutput");
  try {
    const body = JSON.parse(raw);
    out.textContent = "Running…";
    const res = await fetch("/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    out.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    out.textContent = `Error: ${err.message}`;
  }
});

// ── Helpers ───────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
