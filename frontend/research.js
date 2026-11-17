(() => {
  "use strict";

  const queryInput = document.getElementById("researchQuery");
  const results = document.getElementById("researchResults");
  const webButton = document.getElementById("researchWebSearch");
  const youtubeButton = document.getElementById("researchYoutubeSearch");

  function showMessage(text, className = "muted") {
    results.replaceChildren();
    const p = document.createElement("p");
    p.className = className;
    p.textContent = text;
    results.appendChild(p);
  }

  function renderResults(data, kind) {
    results.replaceChildren();
    const items = Array.isArray(data.results) ? data.results : [];
    const summary = document.createElement("p");
    summary.className = "muted";
    summary.textContent = items.length
      ? (kind === "youtube" ? "YouTube videolari topildi: " : "Internet manbalari topildi: ") + items.length
      : "Mos natija topilmadi.";
    results.appendChild(summary);

    const list = document.createElement("div");
    list.className = "cloud-memory-list";
    for (const item of items) {
      let url;
      try { url = new URL(item.url); } catch { continue; }
      if (url.protocol !== "https:") continue;
      if (kind === "youtube" && !["youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"].includes(url.hostname)) continue;
      const row = document.createElement("div");
      row.className = "cloud-memory-row";
      const link = document.createElement("a");
      link.href = url.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = String(item.title || "Manbani ochish").slice(0, 300);
      const snippet = document.createElement("span");
      snippet.className = "muted";
      snippet.textContent = String(item.content || item.snippet || "").slice(0, 1200);
      row.append(link, snippet);
      list.appendChild(row);
    }
    if (list.childElementCount) results.appendChild(list);
    if (data.note) {
      const note = document.createElement("p");
      note.className = "muted";
      note.textContent = data.note;
      results.appendChild(note);
    }
  }

  async function search(kind) {
    const query = queryInput.value.trim();
    if (!query) return showMessage("Avval qidiruv so‘zini kiriting.");
    const button = kind === "youtube" ? youtubeButton : webButton;
    webButton.disabled = true;
    youtubeButton.disabled = true;
    showMessage(kind === "youtube" ? "YouTube manbalari qidirilmoqda..." : "Internet manbalari qidirilmoqda...");
    try {
      const path = kind === "youtube" ? "/api/research/youtube" : "/api/research/search";
      const response = await fetch(apiUrl(path), {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        credentials: "include",
        body: JSON.stringify({query, max_results: 5})
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "Qidiruv hozir bajarilmadi.");
      renderResults(body, kind);
    } catch (error) {
      showMessage(error.message || "Qidiruvda xatolik yuz berdi.", "status-error");
    } finally {
      webButton.disabled = false;
      youtubeButton.disabled = false;
      button.blur();
    }
  }

  webButton.addEventListener("click", () => search("web"));
  youtubeButton.addEventListener("click", () => search("youtube"));
  queryInput.addEventListener("keydown", event => {
    if (event.key === "Enter") search("web");
  });
})();
