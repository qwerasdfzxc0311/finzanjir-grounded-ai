(() => {
  "use strict";

  const byId = id => document.getElementById(id);
  const photoSessions = new Map();

  async function request(path, options = {}) {
    const headers = {...(options.headers || {})};
    if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    const response = await fetch(apiUrl(path), {...options, headers, credentials:"include"});
    const type = response.headers.get("content-type") || "";
    const body = type.includes("application/json") ? await response.json() : {};
    if (!response.ok) throw new Error(body.detail || "Google so‘rovi bajarilmadi.");
    return body;
  }

  function button(label, handler, secondary = false) {
    const node = element("button", secondary ? "secondary-button" : "primary-button", label);
    node.type = "button";
    node.addEventListener("click", handler);
    return node;
  }

  function message(target, text, cls = "muted") {
    target.replaceChildren(element("p", cls, text));
  }

  function addLine(target, title, detail, action) {
    const row = element("div", "cloud-memory-row");
    row.append(element("strong", "", title), element("span", "muted", detail));
    if (action) row.appendChild(action);
    target.appendChild(row);
  }

  async function refreshMemory() {
    const target = byId("googleMemoryResults");
    try {
      const [sources, media, audit] = await Promise.all([
        request("/api/google/memory/sources?limit=200"),
        request("/api/google/memory/media?limit=200"),
        request("/api/google/memory/audit?limit=50")
      ]);
      target.replaceChildren();
      target.appendChild(element("p", "muted",
        "Hujjatlar: " + sources.sources.length + " · Media: " + media.media.length +
        " · Barcha importlar karantinda va shifrlangan."));
      const list = element("div", "cloud-memory-list");
      sources.sources.forEach(x => addLine(list, x.file_name, x.provider + " · " + x.mime_type + " · " + x.status));
      media.media.forEach(x => addLine(list, x.file_name, x.provider + " · " + x.media_type + " · " + x.mime_type + " · " + x.status));
      if (!list.childElementCount) list.appendChild(element("p", "muted", "Hozircha import qilingan manba yo‘q."));
      target.appendChild(list);
    } catch (error) {
      message(target, error.message, "status-error");
    }
  }

  async function searchMemory() {
    const target = byId("googleMemoryResults");
    const query = byId("googleMemoryQuery").value.trim();
    if (!query) return message(target, "Qidirish uchun so‘z kiriting.");
    message(target, "Shifrlangan shaxsiy hujjatlar qidirilmoqda...");
    try {
      const result = await request("/api/google/memory/search?q=" + encodeURIComponent(query));
      target.replaceChildren();
      const list = element("div", "cloud-memory-list");
      result.results.forEach(hit => addLine(list, hit.file_name, hit.snippet));
      if (!list.childElementCount) list.appendChild(element("p", "muted", "Mos manba topilmadi."));
      target.appendChild(list);
    } catch (error) {
      message(target, error.message, "status-error");
    }
  }

  async function loadDrive(account, target, pageToken = null, append = false) {
    if (!append) message(target, "Drive fayllari olinmoqda...");
    try {
      const page = pageToken ? "?page_token=" + encodeURIComponent(pageToken) : "";
      const result = await request("/api/google/accounts/" + encodeURIComponent(account.account_id) + "/drive/files" + page);
      if (!append) target.replaceChildren();
      target.querySelector(".cloud-next-page")?.remove();
      let list = target.querySelector(".cloud-memory-list");
      if (!list) {
        list = element("div", "cloud-memory-list");
        target.appendChild(list);
      }
      result.files.forEach(file => {
        const isMedia = /^(image|audio|video)\//.test(file.mimeType || "");
        const action = button("Import", async () => {
          action.disabled = true;
          action.textContent = "Saqlanmoqda...";
          try {
            const suffix = isMedia ? "import-media" : "import";
            const saved = await request(
              "/api/google/accounts/" + encodeURIComponent(account.account_id) +
              "/drive/files/" + encodeURIComponent(file.id) + "/" + suffix,
              {method:"POST", body:"{}"}
            );
            action.textContent = "Saqlandi";
            detail.textContent = saved.message;
          } catch (error) {
            action.disabled = false;
            action.textContent = "Qayta urinish";
            detail.textContent = error.message;
          }
        }, true);
        const row = element("div", "cloud-memory-row");
        const detail = element("span", "muted", file.mimeType + " · " + (file.modifiedTime || ""));
        row.append(element("strong", "", file.name), detail, action);
        list.appendChild(row);
      });
      if (!list.childElementCount) list.appendChild(element("p", "muted", "Drive fayllari topilmadi."));
      target.appendChild(list);
      if (result.next_page_token) {
        const next = button("Keyingi 100 ta fayl", () => loadDrive(account, target, result.next_page_token, true), true);
        next.classList.add("cloud-next-page");
        target.appendChild(next);
      }
    } catch (error) {
      message(target, error.message, "status-error");
    }
  }

  async function loadGmail(account, query, target, pageToken = null, append = false) {
    if (!append) message(target, "Gmail xabarlari olinmoqda...");
    try {
      const page = pageToken ? "&page_token=" + encodeURIComponent(pageToken) : "";
      const result = await request(
        "/api/google/accounts/" + encodeURIComponent(account.account_id) +
        "/gmail/messages?q=" + encodeURIComponent(query) + page
      );
      if (!append) target.replaceChildren();
      target.querySelector(".cloud-next-page")?.remove();
      let list = target.querySelector(".cloud-memory-list");
      if (!list) {
        list = element("div", "cloud-memory-list");
        target.appendChild(list);
      }
      result.messages.forEach(item => {
        const row = element("div", "cloud-memory-row");
        const detail = element("span", "muted", "Xabar ID: " + item.id);
        const action = button("Xatni import qilish", async () => {
          action.disabled = true;
          action.textContent = "Import...";
          try {
            const saved = await request(
              "/api/google/accounts/" + encodeURIComponent(account.account_id) +
              "/gmail/messages/" + encodeURIComponent(item.id) + "/import",
              {method:"POST", body:"{}"}
            );
            action.textContent = "Saqlandi";
            detail.textContent = saved.subject || saved.message;
          } catch (error) {
            action.disabled = false;
            action.textContent = "Qayta urinish";
            detail.textContent = error.message;
          }
        }, true);
        row.append(element("strong", "", item.threadId || "Gmail xabari"), detail, action);
        list.appendChild(row);
      });
      if (!list.childElementCount) list.appendChild(element("p", "muted", "Xabar topilmadi."));
      target.appendChild(list);
      if (result.next_page_token) {
        const next = button("Keyingi xabarlar", () => loadGmail(account, query, target, result.next_page_token, true), true);
        next.classList.add("cloud-next-page");
        target.appendChild(next);
      }
    } catch (error) {
      message(target, error.message, "status-error");
    }
  }

  async function photosPicker(account, target) {
    message(target, "Google Photos tanlash sessiyasi yaratilmoqda...");
    try {
      const result = await request(
        "/api/google/accounts/" + encodeURIComponent(account.account_id) + "/photos/sessions",
        {method:"POST", body:"{}"}
      );
      photoSessions.set(account.account_id, result.session_id);
      target.replaceChildren();
      const link = element("a", "cloud-picker-link", "Google Photos’da rasm yoki video tanlash");
      link.href = result.picker_uri;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      target.append(link, button("Tanlovni tekshirish", () => pollPhotos(account, target, result.session_id), true));
    } catch (error) {
      message(target, error.message, "status-error");
    }
  }

  async function pollPhotos(account, target, sessionId) {
    message(target, "Google Photos tanlovi tekshirilmoqda...");
    try {
      const state = await request(
        "/api/google/accounts/" + encodeURIComponent(account.account_id) +
        "/photos/sessions/" + encodeURIComponent(sessionId)
      );
      if (!state.media_items_set) {
        message(target, "Tanlov hali tugamagan. Google Photos oynasida tanlashni yakunlang.");
        target.appendChild(button("Yana tekshirish", () => pollPhotos(account, target, sessionId), true));
        return;
      }
      const result = await request(
        "/api/google/accounts/" + encodeURIComponent(account.account_id) +
        "/photos/sessions/" + encodeURIComponent(sessionId) + "/media-items"
      );
      target.replaceChildren();
      const list = element("div", "cloud-memory-list");
      result.media_items.forEach(item => {
        const row = element("div", "cloud-memory-row");
        const detail = element("span", "muted", item.type + " · " + item.mime_type);
        const action = button("Shifrlab saqlash", async () => {
          action.disabled = true;
          action.textContent = "Saqlanmoqda...";
          try {
            await request(
              "/api/google/accounts/" + encodeURIComponent(account.account_id) +
              "/photos/sessions/" + encodeURIComponent(sessionId) +
              "/media-items/" + encodeURIComponent(item.id) + "/import",
              {method:"POST", body:"{}"}
            );
            action.textContent = "Saqlandi";
          } catch (error) {
            action.disabled = false;
            action.textContent = "Qayta urinish";
            detail.textContent = error.message;
          }
        }, true);
        row.append(element("strong", "", item.filename || item.id), detail, action);
        list.appendChild(row);
      });
      if (!list.childElementCount) list.appendChild(element("p", "muted", "Tanlangan media topilmadi."));
      target.appendChild(list);
      target.appendChild(button("Photos sessiyasini yopish", async () => {
        await request(
          "/api/google/accounts/" + encodeURIComponent(account.account_id) +
          "/photos/sessions/" + encodeURIComponent(sessionId),
          {method:"DELETE"}
        );
        photoSessions.delete(account.account_id);
        message(target, "Google Photos sessiyasi yopildi.");
      }, true));
    } catch (error) {
      message(target, error.message, "status-error");
    }
  }

  async function loadAccounts(accounts) {
    const target = byId("googleAccounts");
    target.replaceChildren();
    accounts.forEach(account => {
      const card = element("article", "cloud-account-card");
      card.append(
        element("strong", "", account.google_email),
        element("span", "muted", account.status + " · " + account.scopes.length + " ruxsat")
      );
      const actions = element("div", "cloud-toolbar");
      const output = element("div", "cloud-account-output");
      if (account.scopes.some(x => x.includes("drive.readonly"))) {
        actions.appendChild(button("Drive fayllari", () => loadDrive(account, output), true));
      }
      if (account.scopes.some(x => x.includes("gmail.readonly"))) {
        const query = element("input", "cloud-query");
        query.value = "in:anywhere newer_than:30d";
        query.setAttribute("aria-label", "Gmail qidiruv so‘rovi");
        actions.append(query, button("Gmail qidirish", () => loadGmail(account, query.value, output), true));
      }
      if (account.scopes.some(x => x.includes("photospicker.mediaitems.readonly"))) {
        actions.appendChild(button("Google Photos", () => photosPicker(account, output), true));
      }
      actions.appendChild(button("Akkauntni uzish", async () => {
        if (!window.confirm("Google akkauntni FINZANJIRdan uzasizmi?")) return;
        try {
          await request("/api/google/accounts/" + encodeURIComponent(account.account_id) + "/disconnect", {method:"POST", body:"{}"});
          await refreshStatus();
        } catch (error) {
          message(output, error.message, "status-error");
        }
      }, true));
      card.append(actions, output);
      target.appendChild(card);
    });
  }

  async function refreshStatus() {
    const status = byId("googleCloudStatus");
    const controls = byId("googleCloudControls");
    const memory = byId("googleMemoryWorkspace");
    try {
      const result = await request("/api/google/status");
      if (!result.configured) {
        controls.hidden = true;
        memory.hidden = true;
        message(status, result.message || "Google ulanishi hali sozlanmagan.");
        return;
      }
      controls.hidden = false;
      if (!result.authenticated) {
        memory.hidden = true;
        byId("googleOwnerLogin").hidden = false;
        byId("googleAddAccount").hidden = true;
        byId("googleOwnerLogout").hidden = true;
        message(status, "Google server sozlamalari tayyor. Egasi Google akkaunti bilan kirsin.");
        return;
      }
      memory.hidden = false;
      byId("googleOwnerLogin").hidden = true;
      byId("googleAddAccount").hidden = false;
      byId("googleOwnerLogout").hidden = false;
      message(status, "Egasi: " + result.owner_email + " · Akkauntlar: " +
        result.account_count + " / " + result.account_limit, "status-success");
      await loadAccounts(result.accounts || []);
      await refreshMemory();
    } catch (error) {
      controls.hidden = true;
      memory.hidden = true;
      message(status, error.message, "status-error");
    }
  }

  byId("googleOwnerLogin").addEventListener("click", () => {
    window.location.href = apiUrl("/api/google/oauth/start?purpose=owner_login");
  });
  byId("googleAddAccount").addEventListener("click", () => {
    const services = [
      byId("googleServiceDrive").checked ? "drive" : "",
      byId("googleServiceGmail").checked ? "gmail" : "",
      byId("googleServicePhotos").checked ? "photos" : ""
    ].filter(Boolean).join(",");
    if (!services) return message(byId("googleCloudStatus"), "Kamida bitta xizmatni tanlang.", "status-error");
    window.location.href = apiUrl("/api/google/oauth/start?purpose=add_account&services=" + encodeURIComponent(services));
  });
  byId("googleOwnerLogout").addEventListener("click", async () => {
    try {
      await request("/api/google/logout", {method:"POST", body:"{}"});
      window.location.reload();
    } catch (error) {
      message(byId("googleCloudStatus"), error.message, "status-error");
    }
  });
  byId("googleMemorySearch").addEventListener("click", searchMemory);
  byId("googleMemoryQuery").addEventListener("keydown", event => {
    if (event.key === "Enter") searchMemory();
  });
  byId("googleMemoryRefresh").addEventListener("click", refreshMemory);
  refreshStatus();
})();
