const scenarioTemplates = {
  multi_signal_high: {
    mfa_strength_decreased: true,
    mfa_change_to_transfer_seconds: 300,
    device_age_hours: 1,
    trusted_device: false,
    password_reset_to_transfer_seconds: 300,
    beneficiary_age_days: 1,
    beneficiary_prior_transaction_count: 0,
    transaction_count_10m: 5
  },
  micro_transaction: {
    micro_transaction_count_10m: 4,
    micro_transaction_followup_seconds: 600,
    transaction_count_10m: 5
  },
  new_device_benign: {
    device_age_hours: 2,
    trusted_device: false,
    verified_device_replacement: true
  },
  language_context: {
    app_language_changed: true
  }
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function renderList(target, items, renderItem) {
  target.replaceChildren();
  items.forEach((item, index) => target.appendChild(renderItem(item, index)));
}

async function loadShell() {
  const [manifestResponse, demoResponse] = await Promise.all([
    fetch("./prototype_manifest.json"),
    fetch("/api/prototype/demo")
  ]);
  if (!manifestResponse.ok || !demoResponse.ok) throw new Error("Prototype ma’lumotlari yuklanmadi");
  const [manifest, demo] = await Promise.all([manifestResponse.json(), demoResponse.json()]);

  document.querySelector("#mode").textContent = manifest.data_mode;
  const labels = Object.fromEntries(manifest.windows.map(([id, label]) => [id, label]));

  renderList(document.querySelector("#windows"), manifest.windows, ([id, label]) => {
    const role = manifest.window_roles[id];
    const article = element("article", "card");
    const title = element("strong", "", label);
    const purpose = element("p", "muted", role.output);
    const input = element("small", "", role.input);
    article.append(title, purpose, input);
    return article;
  });

  renderList(document.querySelector("#flow"), manifest.system_flow.transitions, ([from, to], index) => {
    const step = element("div", "flow-step");
    step.append(
      element("span", "badge", index + 1),
      element("strong", "", labels[from]),
      element("span", "arrow", "→"),
      element("strong", "", labels[to])
    );
    return step;
  });

  renderList(document.querySelector("#layers"), manifest.layers, ([id, label]) => {
    const item = element("li");
    item.append(element("span", "badge", id), document.createTextNode(" " + label));
    return item;
  });

  const runtime = demo.runtime;
  const result = document.querySelector("#prototypeResult");
  result.replaceChildren(
    element("p", "", runtime.transaction_id + " · " + demo.data_mode),
    element("p", "", "Risk: " + (runtime.risk_level ?? "NO_RISK") + " · Score: " + (runtime.risk_score ?? 0)),
    element("p", "", "Signals: " + runtime.signal_ids.length + " · Evidence: " + runtime.evidence_ids.length + " · Case: " + (runtime.case_id ?? "ochilmadi")),
    element("p", "muted", "Sintetik demo. Signal firibgarlik isboti emas, Risk aybdorlik emas, Case yakuniy huquqiy qaror emas.")
  );
}

function renderScenarioResult(body) {
  const target = document.querySelector("#scenarioResult");
  const detector = body.detector;
  const risk = body.pipeline?.risk;
  target.replaceChildren(
    element("p", "status-good", "Sinov muvaffaqiyatli bajarildi · " + body.data_mode),
    element("div", "result-grid")
  );
  const metrics = target.querySelector(".result-grid");
  [
    ["Risk balli", risk?.score ?? 0],
    ["Daraja", risk?.level ?? "OBSERVE"],
    ["Aniqlangan signal", detector?.detected_count ?? body.pipeline?.signals?.length ?? 0],
    ["Mustaqil oilalar", risk?.independent_families ?? 0],
    ["Case eligibility", risk?.case_eligible ? "Ha" : "Yo‘q"],
    ["Case", body.case ? "Sintetik ochildi" : "Ochildi yo‘q"]
  ].forEach(([label, value]) => {
    const metric = element("div", "metric");
    metric.append(element("span", "muted", label), element("strong", "", value));
    metrics.appendChild(metric);
  });

  if (detector) {
    const title = element("h3", "", "Detector natijalari");
    const list = element("ul", "layers");
    detector.detections
      .filter(item => item.status === "DETECTED" || item.status === "SUPPRESSED_BENIGN")
      .forEach(item => {
        list.appendChild(element("li", "", item.signal_id + " — " + item.name + " — " + item.status));
      });
    if (!list.children.length) list.appendChild(element("li", "muted", "Hech qanday signal aniqlanmadi."));
    target.append(title, list);
  }
  target.appendChild(element("p", "muted", "Bu sintetik sinov. Ball ehtimollik emas; hech qanday real to‘lov yoki bank qarori o‘zgartirilmagan."));
}

async function loadRunHistory() {
  const target = document.querySelector("#runHistory");
  try {
    const response = await fetch("/api/prototype/runs?limit=10");
    if (!response.ok) throw new Error("Tarix vaqtincha mavjud emas");
    const body = await response.json();
    if (!body.runs.length) {
      target.replaceChildren(element("p", "muted", "Hozircha saqlangan sintetik sinov yo‘q."));
      return;
    }
    const list = element("div", "history-list");
    body.runs.forEach(run => {
      const item = element("div", "history-item");
      const left = element("div");
      left.append(
        element("strong", "", run.risk_level + " · " + run.risk_score + " ball"),
        element("p", "muted", new Date(run.created_at).toLocaleString())
      );
      const right = element("div");
      right.append(
        element("span", "", run.signal_count + " signal · " + run.evidence_count + " dalil"),
        element("p", "muted", run.shadow_mode ? "Shadow Mode" : (run.case_opened ? "Sintetik Case" : "Case yo‘q"))
      );
      item.append(left, right);
      list.appendChild(item);
    });
    target.replaceChildren(list, element("p", "muted", "Saqlash muddati: " + body.retention_days + " kun. Tarixda xom tranzaksiya yoki shaxsiy identifikatorlar saqlanmaydi."));
  } catch (error) {
    target.replaceChildren(element("p", "muted", error.message));
  }
}

async function runSyntheticScenario() {
  const button = document.querySelector("#runSyntheticScenario");
  const selector = document.querySelector("#scenarioSelector");
  const openCase = document.querySelector("#openSyntheticCase").checked;
  const scenario = selector.value;
  const features = scenarioTemplates[scenario];
  button.disabled = true;
  button.textContent = "Sinov bajarilmoqda...";
  document.querySelector("#scenarioResult").replaceChildren(element("p", "muted", "Sintetik feature’lar tekshirilmoqda..."));

  const runToken = (window.crypto && window.crypto.randomUUID)
    ? window.crypto.randomUUID()
    : String(Date.now());
  const payload = {
    transaction_id: "TX-UI-" + runToken,
    bank_id: "synthetic-bank",
    actor_id: "synthetic-ui-actor",
    amount: 2500,
    occurred_at: new Date().toISOString(),
    synthetic: true,
    shadow_mode: !openCase,
    detector_scenario_id: scenario + "-" + runToken,
    signal_features: features
  };

  try {
    const response = await fetch("/api/prototype/run", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Sinov bajarilmadi");
    renderScenarioResult(body);
    await loadRunHistory();
  } catch (error) {
    document.querySelector("#scenarioResult").replaceChildren(element("p", "status-muted", error.message));
  } finally {
    button.disabled = false;
    button.textContent = "Sintetik sinovni ishga tushirish";
  }
}

document.querySelector("#runSyntheticScenario").addEventListener("click", runSyntheticScenario);

loadShell().catch(error => {
  document.querySelector("#windows").replaceChildren(element("p", "muted", error.message));
  document.querySelector("#flow").replaceChildren();
  document.querySelector("#prototypeResult").replaceChildren(element("p", "muted", "Runtime demo hozircha mavjud emas."));
});
loadRunHistory();
