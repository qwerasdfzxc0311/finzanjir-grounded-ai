const API_BASE_URL = "https://finzanjir-grounded-ai-api.onrender.com";

function apiUrl(path) {
  return new URL(path, API_BASE_URL).toString();
}

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

let currentManifest = null;
let lastExecution = null;
let activeWindowId = "dashboard";
let executionStatus = "demo";
let executionError = "";
let liveWindowTrace = [];

function windowSummaryLines(windowId) {
  const snapshot = lastExecution || {};
  const runtime = snapshot.runtime || {};
  const pipeline = snapshot.pipeline || {};
  const risk = pipeline.risk || {};
  const transaction = snapshot.transaction || {};
  const caseRecord = snapshot.case || {};
  const human = snapshot.decision?.human_decision || {};
  const citizen = snapshot.citizen_status || {};
  const crossBank = snapshot.cross_bank || {};
  const audit = snapshot.audit || [];
  const kpi = snapshot.kpi || {};
  const ai = snapshot.ai || {};
  const layers = snapshot.layers_16 || [];
  const value = item => item === undefined || item === null || item === "" ? "—" : String(item);

  switch (windowId) {
    case "dashboard":
      return [
        "Data mode: " + value(snapshot.data_mode || "synthetic"),
        "Transaction: " + value(runtime.transaction_id || snapshot.transaction_id || transaction.transaction_id),
        "Risk: " + value(runtime.risk_level || risk.level) + " · " + value(runtime.risk_score ?? risk.score) + " ball",
        "Case: " + value(runtime.case_id || caseRecord.case_id || caseRecord.id),
        "Qatlamlar: " + value(runtime.layers_traced ?? layers.length ?? 0) + " / 16"
      ];
    case "citizen":
      return [
        "Status: " + value(citizen.status || "Sinov natijasidan keyin ko‘rsatiladi"),
        "Xabar: " + value(citizen.message),
        "Case ID: " + value(citizen.case_id)
      ];
    case "human_case":
      return [
        "Case ID: " + value(caseRecord.case_id || caseRecord.id || runtime.case_id),
        "Case status: " + value(caseRecord.status),
        "Human review: " + value(human.decision),
        "Rasmiy qaror: " + (human.is_authoritative === true ? "Ha" : "Yo‘q — sintetik namuna")
      ];
    case "synthetic_bank":
      return [
        "Transaction: " + value(transaction.transaction_id || runtime.transaction_id || snapshot.transaction_id),
        "Bank: " + value(transaction.bank_id),
        "Amount: " + value(transaction.amount),
        "Synthetic: " + (transaction.synthetic === true || snapshot.data_mode === "synthetic" ? "Ha" : "Tasdiqlanmagan")
      ];
    case "signal_risk": {
      const contributions = Array.isArray(risk.contributions) ? risk.contributions : [];
      const detectorOutcomes = Array.isArray(snapshot.detector?.detections) ? snapshot.detector.detections : [];
      const detectorCounts = detectorOutcomes.reduce((counts, item) => {
        counts[item.status] = (counts[item.status] || 0) + 1;
        return counts;
      }, {});
      const detectorLines = detectorOutcomes.map(item =>
        "Detector " + value(item.signal_id) + " — " + value(item.name)
          + " · " + value(item.status) + " · sabab " + value(item.reason_code)
          + " · mos fieldlar " + value((item.matched_features || []).join(", ") || "—")
          + " · yetishmaydi " + value((item.missing_features || []).join(", ") || "—")
          + " · yaroqsiz " + value((item.invalid_features || []).join(", ") || "—")
      );
      const evidenceById = new Map((pipeline.evidences || []).map(item => [item.id, item]));
      const signalLines = contributions.length
        ? contributions.map(item => {
            const contribution = item.score_eligible
              ? value(item.raw_contribution) + " ball"
              : "0 ball · hisobga olinmadi: " + value(item.score_suppressed_reason);
            return "Signal " + value(item.signal_id) + " — " + value(item.signal_name)
              + " · " + value(item.family) + " · " + contribution;
          })
        : ["Signal contribution: hozircha mavjud emas"];
      const evidenceLines = contributions.map(item => {
        const evidence = evidenceById.get(item.evidence_id) || {};
        const provenance = evidence.provenance || {};
        return "Dalil " + value(item.evidence_id)
          + " · manba " + value(provenance.source || item.source)
          + " · vaqt " + value(item.observed_at || evidence.observed_at)
          + " · sifat " + value(item.evidence_quality ?? evidence.evidence_quality)
          + " · freshness " + value(item.recency_factor ?? evidence.recency_factor)
          + " · qoida " + value(item.rule_version);
      });
      const familyLines = Object.entries(risk.family_contributions || {}).map(
        ([family, score]) => "Oila " + family + ": " + value(score) + " ball"
      );
      return [
        "Signals: " + value(pipeline.signals?.length ?? runtime.signal_ids?.length ?? 0),
        "Evidence: " + value(pipeline.evidences?.length ?? runtime.evidence_ids?.length ?? 0),
        "40 detector holati: " + value(detectorOutcomes.length) + " · " + Object.entries(detectorCounts).map(([status, count]) => status + "=" + count).join(", "),
        "Risk score: " + value(risk.score ?? runtime.risk_score) + " / 100",
        "Risk level: " + value(risk.level ?? runtime.risk_level),
        "Threshold: " + value(risk.escalation_threshold ?? risk.threshold?.value ?? runtime.threshold) + " / 100",
        "Threshold reason: " + value(risk.threshold?.reason),
        "Threshold met: " + value(risk.threshold_met),
        "Case eligibility: " + value(risk.case_eligible),
        "Case block/suppression: " + value(risk.case_block_reason || risk.case_suppressed_reason || "yo‘q"),
        "Score meaning: ustuvorlik balli, firibgarlik ehtimoli yoki aybdorlik emas",
        ...familyLines,
        ...(detectorOutcomes.length ? detectorLines : ["Detector rule sababi: bu run oldindan tayyor signal eventlaridan foydalandi"]),
        ...signalLines,
        ...evidenceLines
      ];
    }
    case "cross_bank_fraud":
      return [
        "Scope: " + value(crossBank.scope || "cross_bank"),
        "Matches: " + value(crossBank.matches?.length ?? runtime.cross_bank_matches ?? 0),
        "Cross-bank ruxsati: " + (runtime.cross_bank_authorized === true ? "Ha" : "Yo‘q")
      ];
    case "audit_kpi":
      return [
        "Audit events: " + value(audit.length || runtime.audit_events || 0),
        "Signal → Case: " + value(kpi.signal_to_case_rate),
        "Case action rate: " + value(kpi.case_action_rate),
        "Data mode: synthetic"
      ];
    case "finzanjir_ai":
      return [
        "AI izohi: " + value(ai.answer?.answer || snapshot.explanation?.summary || "Sinov natijasidan keyin ko‘rsatiladi"),
        "Confidence: " + value(ai.answer?.confidence),
        "Abstained: " + value(ai.answer?.abstained),
        "Knowledge refs: " + value(ai.answer?.citations?.length ?? 0)
      ];
    case "layers_16":
      return [
        "Layer traces: " + value(layers.length || runtime.layers_traced || 0) + " / 16",
        "Holat: " + value(runtime.layer_status_summary?.partial) + " qisman, " + value(runtime.layer_status_summary?.planned) + " rejalashtirilgan"
      ];
    default:
      return ["Bu oyna uchun runtime ma’lumoti mavjud emas."];
  }
}


function windowTraceFor(windowId) {
  if (executionStatus === "running" || (executionStatus === "failed" && liveWindowTrace.length)) {
    const live = liveWindowTrace.find(item => item.window_id === windowId);
    if (live) return live;
    if (executionStatus === "failed") return null;
    const flowIds = currentManifest?.system_flow?.transitions?.length
      ? [currentManifest.system_flow.transitions[0][0], ...currentManifest.system_flow.transitions.map(item => item[1])]
      : [];
    const sequence = flowIds.indexOf(windowId);
    if (sequence >= 0) {
      return {
        sequence: sequence + 1,
        window_id: windowId,
        status: "PENDING",
        status_label: "Navbatda · oldingi bosqichlar kutilmoqda",
        summary: "Backend bosqich hodisasi kelishi bilan holat yangilanadi.",
        input_refs: [],
        output_refs: []
      };
    }
    return null;
  }
  const snapshot = lastExecution || {};
  return Array.isArray(snapshot.window_trace)
    ? snapshot.window_trace.find(item => item.window_id === windowId)
    : null;
}

function windowTraceLines(windowId) {
  const trace = windowTraceFor(windowId);
  if (!trace) return [];
  const refs = items => Array.isArray(items) && items.length ? items.join(", ") : "—";
  return [
    "Bosqich #" + trace.sequence + " · " + trace.status,
    "Holat: " + (trace.status_label || trace.status),
    "Izoh: " + (trace.summary || "—"),
    "Kirish refs: " + refs(trace.input_refs),
    "Chiqish refs: " + refs(trace.output_refs)
  ];
}

function windowExecutionStatus(windowId) {
  const trace = windowTraceFor(windowId);
  if (executionStatus === "failed") {
    if (trace?.status === "FAILED") return "Xato · bosqich xavfsiz to‘xtadi";
    if (trace?.status === "NOT_RUN") return "Bajarilmadi · oldingi bosqich to‘xtadi";
    if (trace) return trace.status_label || trace.status;
    return "Sinov xato bilan tugadi · oldingi natija saqlangan";
  }
  if (executionStatus === "running" && trace) {
    if (trace.status === "RUNNING") return "Hozir bajarilmoqda";
    if (trace.status === "PENDING") return "Navbatda";
    return trace.status_label || trace.status;
  }
  if (executionStatus === "running") return "Yagona oqim bajarilmoqda";
  if (trace) return trace.status_label || trace.status;
  if (executionStatus === "demo") return "Demo ko‘rinishi · to‘liq sinov hali ishga tushmagan";

  const snapshot = lastExecution || {};
  switch (windowId) {
    case "dashboard":
      return snapshot.pipeline ? "Yagona runtime natijasi yangilandi" : "Umumiy demo holati";
    case "synthetic_bank":
      return snapshot.transaction ? "Sintetik tranzaksiya qabul qilindi" : "Tranzaksiya natijasi yo‘q";
    case "signal_risk":
      return snapshot.pipeline?.risk ? "Signal va risk hisoblandi" : "Risk natijasi mavjud emas";
    case "cross_bank_fraud":
      if (snapshot.runtime?.cross_bank_authorized !== true) {
        return "Cross-bank almashinuvi o‘chiq · ruxsat yo‘q";
      }
      if (!Array.isArray(snapshot.cross_bank?.matches)) return "Cross-bank natijasi mavjud emas";
      return snapshot.cross_bank.matches.length
        ? "Ruxsatli scope ichida moslik bor"
        : "Ruxsatli scope tekshirildi · moslik topilmadi";
    case "human_case":
      if (snapshot.case) return "Sintetik Case va inson ko‘rigi qayd etildi";
      if (snapshot.pipeline?.risk?.shadow_mode === true) return "Shadow Mode · Case ochilmadi";
      return "Case ochilmadi";
    case "audit_kpi":
      return Array.isArray(snapshot.audit) && snapshot.kpi ? "Audit va KPI natijasi tayyor" : "Audit/KPI tafsiloti yo‘q";
    case "finzanjir_ai":
      if (!snapshot.ai) return "AI runtime izohi mavjud emas";
      return snapshot.ai.answer?.abstained ? "AI dalil yetishmasligini bildirdi" : "AI izohi tayyor";
    case "citizen":
      return snapshot.citizen_status ? "Fuqaro statusi tayyor" : "Fuqaro statusi mavjud emas";
    case "layers_16":
      return Array.isArray(snapshot.layers_16) && snapshot.layers_16.length === 16
        ? "16 qatlam izi tayyor"
        : "16 qatlam izi to‘liq emas";
    default:
      return "Holat aniqlanmagan";
  }
}

function refreshWindowStatuses() {
  document.querySelectorAll("#windows .window-card").forEach(button => {
    const status = button.querySelector(".window-status");
    if (status) {
      status.textContent = windowExecutionStatus(button.dataset.windowId);
      status.dataset.state = executionStatus;
    }
  });
  const activeStatus = document.querySelector("#activeWindowStatus");
  if (activeStatus) {
    activeStatus.textContent = windowExecutionStatus(activeWindowId);
    activeStatus.dataset.state = executionStatus;
  }
}

function selectWindow(windowId) {
  if (!currentManifest || !currentManifest.window_roles[windowId]) return;
  activeWindowId = windowId;
  const labels = Object.fromEntries(currentManifest.windows.map(([id, label]) => [id, label]));
  document.querySelectorAll("#windows .window-card").forEach(button => {
    button.setAttribute("aria-pressed", String(button.dataset.windowId === windowId));
  });
  document.querySelector("#activeWindowTitle").textContent = labels[windowId] || windowId;
  document.querySelector("#activeWindowPurpose").textContent = currentManifest.window_roles[windowId].output;
  document.querySelector("#activeWindowInput").textContent = "Kirish: " + currentManifest.window_roles[windowId].input;
  const list = document.querySelector("#activeWindowData");
  list.replaceChildren(...[...windowTraceLines(windowId), ...windowSummaryLines(windowId)].map(line => {
    const item = document.createElement("li");
    item.textContent = line;
    return item;
  }));
  refreshWindowStatuses();
  renderWindowInteractive(windowId);
}

async function loadShell() {
  const [manifestResponse, demoResponse] = await Promise.all([
    fetch("./prototype_manifest.json"),
    fetch(apiUrl("/api/prototype/demo"))
  ]);
  if (!manifestResponse.ok || !demoResponse.ok) throw new Error("Prototype ma’lumotlari yuklanmadi");
  const [manifest, demo] = await Promise.all([manifestResponse.json(), demoResponse.json()]);

  document.querySelector("#mode").textContent = manifest.data_mode;
  const labels = Object.fromEntries(manifest.windows.map(([id, label]) => [id, label]));

  currentManifest = manifest;
  lastExecution = demo;
  executionStatus = "demo";
  executionError = "";
  renderList(document.querySelector("#windows"), manifest.windows, ([id, label]) => {
    const role = manifest.window_roles[id];
    const button = element("button", "window-card");
    button.type = "button";
    button.dataset.windowId = id;
    button.setAttribute("aria-pressed", "false");
    button.append(
      element("strong", "", label),
      element("p", "muted", role.output),
      element("small", "", role.input),
      element("small", "window-status", windowExecutionStatus(id))
    );
    button.addEventListener("click", () => {
      selectWindow(id);
      if (id === "synthetic_bank") runSyntheticScenario();
    });
    return button;
  });
  selectWindow("dashboard");

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
      .filter(item => ["DETECTED", "SUPPRESSED_BENIGN", "INSUFFICIENT_DATA"].includes(item.status))
      .forEach(item => {
        const detail = item.invalid_features?.length
          ? " — noto‘g‘ri qiymat: " + item.invalid_features.join(", ")
          : item.missing_features?.length
            ? " — yetishmaydi: " + item.missing_features.join(", ")
            : "";
        list.appendChild(element("li", "", item.signal_id + " — " + item.name + " — " + item.status + detail));
      });
    if (!list.children.length) list.appendChild(element("li", "muted", "Hech qanday signal aniqlanmadi."));
    target.append(title, list);
  }
  const human = body.decision?.human_decision;
  const ai = body.ai;
  const aiAnswer = ai?.answer?.answer ?? "AI izohi mavjud emas.";
  const aiRefs = ai?.runtime_context?.runtime_refs ?? [];
  const layerRows = Array.isArray(body.layers_16) ? body.layers_16 : [];
  const crossMatches = body.cross_bank?.matches ?? [];
  const auditRows = Array.isArray(body.audit) ? body.audit : [];

  const modules = element("div", "module-results");
  const addModule = (heading, lines) => {
    const section = element("section", "module-card");
    section.appendChild(element("h3", "", heading));
    const list = element("ul", "layers");
    lines.forEach(line => list.appendChild(element("li", "", line)));
    section.appendChild(list);
    modules.appendChild(section);
  };

  addModule("Synthetic Bank → Signal / Evidence / Risk", [
    "Transaction: " + (body.transaction_id ?? "—"),
    "Signal: " + (body.pipeline?.signals?.length ?? 0),
    "Evidence: " + (body.pipeline?.evidences?.length ?? 0),
    "Threshold: " + (risk?.threshold ?? risk?.escalation_threshold ?? "—")
  ]);
  addModule("Human + Case", [
    "Case: " + (body.case?.case_id ?? body.case?.id ?? "ochilmadi"),
    "Review decision: " + (human?.decision ?? "yo‘q"),
    "Authoritative: " + (human?.is_authoritative === true ? "Ha" : "Yo‘q — synthetic demo")
  ]);
  addModule("Cross-Bank Fraud", [
    "Scope: " + (body.cross_bank?.scope ?? "cross_bank"),
    "Matches: " + crossMatches.length,
    "Real interbank exchange: o‘chiq"
  ]);
  addModule("Audit / KPI", [
    "Audit events: " + auditRows.length,
    "Signal → Case rate: " + (body.kpi?.signal_to_case_rate ?? 0),
    "Case action rate: " + (body.kpi?.case_action_rate ?? 0)
  ]);
  addModule("FINZANJIR AI", [
    aiAnswer,
    "Knowledge refs: " + (ai?.answer?.citations?.length ?? 0),
    "Runtime refs: " + aiRefs.length
  ]);
  addModule("Citizen", [
    "Status: " + (body.citizen_status?.status ?? "—"),
    "Message: " + (body.citizen_status?.message ?? "—"),
    "Case ID: " + (body.citizen_status?.case_id ?? "yo‘q")
  ]);
  addModule("16 Layers", [
    "Layer traces: " + layerRows.length + " / 16",
    "Data mode: synthetic",
    ...layerRows.slice(0, 16).map(item => item.layer_id + " — " + (item.status ?? "traced"))
  ]);
  target.appendChild(modules);
  target.appendChild(element("p", "muted", "Bu sintetik sinov. Ball ehtimollik emas; hech qanday real to‘lov yoki bank qarori o‘zgartirilmagan."));
}

async function loadRunHistory() {
  const target = document.querySelector("#runHistory");
  try {
    const response = await fetch(apiUrl("/api/prototype/runs?limit=10"));
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
    target.replaceChildren(
      list,
      element("p", "muted", "Saqlash muddati: " + body.retention_days + " kun. Tarixda xom tranzaksiya yoki shaxsiy identifikatorlar saqlanmaydi."),
      element("p", "muted", body.persistence_note || "Tarixning doimiy saqlanishi hosting disk sozlamasiga bog‘liq.")
    );
  } catch (error) {
    target.replaceChildren(element("p", "muted", error.message));
  }
}

async function readPrototypeProgress(response) {
  if (!response.body || typeof response.body.getReader !== "function") {
    throw new Error("Brauzer oqimli progressni qo‘llab-quvvatlamaydi.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult = null;
  let streamError = null;

  function handleFrame(frame) {
    const lines = frame.split(/\r?\n/);
    const eventLine = lines.find(line => line.startsWith("event: "));
    const dataLine = lines.find(line => line.startsWith("data: "));
    if (!eventLine || !dataLine) return;
    const eventName = eventLine.slice(7);
    const data = JSON.parse(dataLine.slice(6));
    if (eventName === "stage") {
      const index = liveWindowTrace.findIndex(item => item.window_id === data.window_id);
      if (index >= 0) liveWindowTrace[index] = data;
      else liveWindowTrace.push(data);
      liveWindowTrace.sort((a, b) => a.sequence - b.sequence);
      refreshWindowStatuses();
      selectWindow(activeWindowId);
    } else if (eventName === "result") {
      finalResult = data;
    } else if (eventName === "error") {
      streamError = new Error(data.detail || "Sinov bajarilmadi");
    }
  }

  while (true) {
    const chunk = await reader.read();
    buffer += decoder.decode(chunk.value || new Uint8Array(), {stream: !chunk.done});
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      handleFrame(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
    if (chunk.done) break;
  }
  if (streamError) throw streamError;
  if (!finalResult) throw new Error("Progress oqimi yakuniy natijasiz tugadi.");
  return finalResult;
}

async function runSyntheticScenario() {
  const button = document.querySelector("#runSyntheticScenario");
  if (button.disabled) return;
  const selector = document.querySelector("#scenarioSelector");
  const openCase = document.querySelector("#openSyntheticCase").checked;
  const scenario = selector.value;
  const features = scenarioTemplates[scenario];
  button.disabled = true;
  executionStatus = "running";
  executionError = "";
  liveWindowTrace = [];
  refreshWindowStatuses();
  button.textContent = "Sinov bajarilmoqda...";
  document.querySelector("#scenarioResult").replaceChildren(element("p", "muted", "Backend bosqichlari ketma-ket bajarilmoqda..."));

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
    const response = await fetch(apiUrl("/api/prototype/run/stream"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      const body = await response.json();
      throw new Error(body.detail || "Progress oqimini boshlash imkoni bo‘lmadi");
    }
    const body = await readPrototypeProgress(response);
    lastExecution = body;
    liveWindowTrace = [];
    executionStatus = "success";
    refreshWindowStatuses();
    selectWindow(activeWindowId);
    renderScenarioResult(body);
    await loadRunHistory();
  } catch (error) {
    executionStatus = "failed";
    executionError = error.message;
    refreshWindowStatuses();
    document.querySelector("#scenarioResult").replaceChildren(element("p", "status-muted", error.message));
  } finally {
    button.disabled = false;
    refreshWindowStatuses();
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


function makeShadowEvents(prefix) {
  const definitions = [
    ["SIG-018", "auth"],
    ["SIG-006", "device"],
    ["SIG-012", "account"],
    ["SIG-004", "beneficiary"],
    ["SIG-002", "velocity"]
  ];
  return definitions.map(([signal_id, suffix], index) => ({
    signal_id,
    evidence_id: prefix + "-" + suffix,
    source: "synthetic-shadow-ui",
    observed_at: new Date(Date.now() + index * 1000).toISOString(),
    evidence_quality: 1.0,
    recency_factor: 1.0
  }));
}

function buildShadowScenarios() {
  const highIds = ["SIG-018", "SIG-006", "SIG-012", "SIG-004", "SIG-002"];
  const highFeatures = {
    mfa_strength_decreased: true,
    mfa_change_to_transfer_seconds: 300,
    device_age_hours: 1,
    trusted_device: false,
    password_reset_to_transfer_seconds: 300,
    beneficiary_age_days: 1,
    beneficiary_prior_transaction_count: 0,
    transaction_count_10m: 5
  };
  const benignFeatures = {
    amount_to_customer_p95_ratio: 1.2,
    customer_baseline_sample_count: 20
  };
  const timestamp = new Date().toISOString();
  const scenarios = [];
  for (let index = 0; index < 4; index += 1) {
    scenarios.push({
      scenario_id: "ui-detector-tp-" + index,
      expected_label: "suspicious",
      synthetic: true,
      observed_at: timestamp,
      target_signal_ids: highIds,
      features: highFeatures
    });
  }
  for (let index = 0; index < 3; index += 1) {
    scenarios.push({
      scenario_id: "ui-detector-tn-" + index,
      expected_label: "benign",
      synthetic: true,
      observed_at: timestamp,
      target_signal_ids: ["SIG-001"],
      features: benignFeatures
    });
  }
  scenarios.push({
    scenario_id: "ui-detector-fp-example",
    expected_label: "benign",
    synthetic: true,
    observed_at: timestamp,
    target_signal_ids: highIds,
    features: highFeatures
  });
  scenarios.push({
    scenario_id: "ui-detector-fn-example",
    expected_label: "suspicious",
    synthetic: true,
    observed_at: timestamp,
    target_signal_ids: ["SIG-001"],
    features: benignFeatures
  });
  return scenarios;
}

async function runShadowEvaluation() {
  const button = document.querySelector("#runShadowEvaluation");
  const target = document.querySelector("#shadowResult");
  button.disabled = true;
  button.textContent = "Shadow Mode baholanmoqda...";
  target.replaceChildren(element("p", "muted", "9 ta sintetik scenario detector va Risk Engine orqali tekshirilmoqda..."));
  try {
    const response = await fetch(apiUrl("/api/prototype/detector-shadow-evaluate"), {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({scenarios: buildShadowScenarios(), escalation_threshold: 75})
    });
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail || "Shadow baholash bajarilmadi");
    const matrix = body.confusion_matrix;
    const metrics = body.metrics;
    const grid = element("div", "result-grid");
    [
      ["Ssenariylar", body.scenario_count],
      ["TP / FP", matrix.tp + " / " + matrix.fp],
      ["TN / FN", matrix.tn + " / " + matrix.fn],
      ["Precision", (metrics.precision * 100).toFixed(1) + "%"],
      ["Recall", (metrics.recall * 100).toFixed(1) + "%"],
      ["Specificity", (metrics.specificity * 100).toFixed(1) + "%"],
      ["False-positive rate", (metrics.false_positive_rate * 100).toFixed(1) + "%"],
      ["False-negative rate", (metrics.false_negative_rate * 100).toFixed(1) + "%"],
      ["Accuracy", (metrics.accuracy * 100).toFixed(1) + "%"],
      ["Coverage", (body.coverage * 100).toFixed(1) + "%"],
      ["Abstention rate", (body.abstention_rate * 100).toFixed(1) + "%"]
    ].forEach(([label, value]) => {
      const metric = element("div", "metric");
      metric.append(element("span", "muted", label), element("strong", "", value));
      grid.appendChild(metric);
    });
    target.replaceChildren(
      element("p", "status-good", "Sintetik Shadow Mode baholashi tugadi"),
      grid,
      element("p", "muted", "Bu ko‘rsatkichlar faqat ushbu 9 ta qo‘lda tuzilgan sintetik feature fixture uchun. Ular real fraud precision/recall yoki bank source-data qamrovini isbotlamaydi. Yetishmayotgan target feature benign emas, abstention sifatida hisoblanadi."),
      element("p", "muted", "Shadow Mode: Case ochilmaydi, to‘lov/bank/fuqaro holati o‘zgarmaydi.")
    );
  } catch (error) {
    target.replaceChildren(element("p", "status-muted", error.message));
  } finally {
    button.disabled = false;
    button.textContent = "Shadow Mode sinovini bajarish";
  }
}

document.querySelector("#runShadowEvaluation").addEventListener("click", runShadowEvaluation);


const aiConversation = [];

function generationModeLabel(mode) {
  const labels = {
    model: "AI modeli javobni tuzdi",
    deterministic_fallback: "Model javobi yo‘q · manba matnlari alohida ko‘rsatildi",
    fallback_refused_long_source: "Model javobi yo‘q · uzun manba xom holda chiqarilmadi",
    no_grounded_evidence: "Mos tasdiqlangan dalil topilmadi",
    insufficient_evidence: "Dalil yetarli emas",
  };
  return labels[mode] || "";
}

function appendChatMessage(role, content, refs = [], mode = "") {
  const log = document.querySelector("#aiChatLog");
  if (!log) return;
  const item = element("article", "chat-message " + (role === "user" ? "chat-user" : "chat-assistant"));
  item.append(element("span", "chat-role", role === "user" ? "Siz" : "FINZANJIR AI"));
  item.append(element("p", "", content));
  if (refs.length) {
    const citationLine = element("small", "chat-refs", "Bilim manbalari: " + refs.join(", "));
    item.appendChild(citationLine);
  }
  const modeLabel = generationModeLabel(mode);
  if (modeLabel) item.appendChild(element("small", "chat-refs", modeLabel));
  log.appendChild(item);
  log.scrollTop = log.scrollHeight;
}

function renderWindowInteractive(windowId) {
  const target = document.querySelector("#windowInteractive");
  if (!target || !currentManifest) return;
  target.replaceChildren();
  const snapshot = lastExecution || {};
  const lines = windowSummaryLines(windowId);
  const heading = element("div", "module-intro");
  const title = Object.fromEntries(currentManifest.windows.map(([id, label]) => [id, label]))[windowId] || windowId;
  heading.append(element("span", "module-kicker", "MODUL ISH MAYDONI"), element("h3", "", title));
  target.appendChild(heading);

  if (windowId === "finzanjir_ai") {
    const notice = element("p", "module-notice", "AI javoblari loyiha bilimlar bazasidagi dalillarga tayanadi. Dalil yetarli bo‘lmasa, tizim javobni cheklashi mumkin. Hozircha suhbat xotirasi faqat ushbu sahifa ochiq turgan paytda saqlanadi.");
    const chat = element("div", "ai-chat-panel");
    const log = element("div", "ai-chat-log");
    log.id = "aiChatLog";
    if (!aiConversation.length) {
      log.appendChild(element("p", "muted chat-empty", "Savolingizni yozing. Masalan: “FINZANJIR qanday qilib firibgarlik zanjirini tahlil qiladi?”"));
    } else {
      aiConversation.forEach(message => {
        const item = element("article", "chat-message " + (message.role === "user" ? "chat-user" : "chat-assistant"));
        item.append(element("span", "chat-role", message.role === "user" ? "Siz" : "FINZANJIR AI"), element("p", "", message.content));
        if (message.refs?.length) item.appendChild(element("small", "chat-refs", "Bilim manbalari: " + message.refs.join(", ")));
        const modeLabel = generationModeLabel(message.mode);
        if (modeLabel) item.appendChild(element("small", "chat-refs", modeLabel));
        log.appendChild(item);
      });
    }
    const form = element("form", "ai-chat-form");
    const input = element("textarea", "ai-question");
    input.id = "aiQuestion";
    input.name = "question";
    input.rows = 3;
    input.maxLength = 4000;
    input.required = true;
    input.placeholder = "FINZANJIR haqida savolingizni yozing...";
    input.setAttribute("aria-label", "FINZANJIR AI savoli");
    const submit = element("button", "primary-button", "Savol yuborish");
    submit.type = "submit";
    const formHint = element("small", "muted", "Maksimal 4 000 belgi. Shaxsiy yoki haqiqiy bank ma’lumotlarini yubormang.");
    form.append(input, submit, formHint);
    form.addEventListener("submit", async event => {
      event.preventDefault();
      const question = input.value.trim();
      if (!question || submit.disabled) return;
      aiConversation.push({role:"user", content:question});
      appendChatMessage("user", question);
      input.value = "";
      submit.disabled = true;
      submit.textContent = "Javob tayyorlanmoqda...";
      try {
        const runtimeRefs = Array.isArray(lastExecution?.ai?.runtime_context?.runtime_refs)
          ? lastExecution.ai.runtime_context.runtime_refs.filter(ref => typeof ref === "string").slice(0, 64)
          : [];
        const response = await fetch(apiUrl("/api/ai/answer"), {
          method: "POST",
          headers: {"Content-Type":"application/json"},
          body: JSON.stringify({question, runtime_refs:runtimeRefs, working_memory_scope:"prototype-ui-session"})
        });
        const body = await response.json();
        if (!response.ok) throw new Error(body.detail || "AI javobini olish imkoni bo‘lmadi");
        const answer = body.answer || "Dalilga tayangan javob qaytmadi.";
        const refs = Array.isArray(body.knowledge_refs) ? body.knowledge_refs : [];
        const mode = body.generation_mode || "";
        aiConversation.push({role:"assistant", content:answer, refs, mode});
        appendChatMessage("assistant", answer, refs, mode);
        if (body.abstained) appendChatMessage("assistant", "Eslatma: mavjud dalillar yetarli bo‘lmagani uchun javob cheklangan.");
      } catch (error) {
        aiConversation.push({role:"assistant", content:"Xatolik: " + error.message});
        appendChatMessage("assistant", "Xatolik: " + error.message);
      } finally {
        submit.disabled = false;
        submit.textContent = "Savol yuborish";
        input.focus();
      }
    });
    chat.append(log, form);
    target.append(notice, chat);
    return;
  }

  if (windowId === "synthetic_bank") {
    target.appendChild(element("p", "module-notice", "Bu oyna faqat sun’iy tranzaksiya ssenariylarini ishga tushiradi. Haqiqiy karta, hisob, mijoz yoki bank ma’lumotlarini kiritmang."));
    const runButton = element("button", "primary-button", "Tanlangan sintetik ssenariyni bajarish");
    runButton.type = "button";
    runButton.addEventListener("click", runSyntheticScenario);
    target.appendChild(runButton);
  } else if (windowId === "cross_bank_fraud") {
    target.appendChild(element("p", "module-warning", "Cross-Bank almashinuvi o‘chiq. Bu prototip banklararo ma’lumot uzatmaydi va ruxsat mavjud deb da’vo qilmaydi."));
  } else if (windowId === "human_case") {
    target.appendChild(element("p", "module-notice", "Bu ko‘rinish sintetik Case va inson ko‘rigi izlarini namoyish etadi. U rasmiy qaror qabul qilmaydi va real mijozga ta’sir ko‘rsatmaydi."));
  } else if (windowId === "citizen") {
    target.appendChild(element("p", "module-notice", "Fuqaro oynasi faqat sintetik demo statusini ko‘rsatadi. Hozircha haqiqiy murojaat yuborish yoki bankdagi cheklovni o‘zgartirish funksiyasi yo‘q."));
  } else if (windowId === "audit_kpi") {
    target.appendChild(element("p", "module-notice", "Audit va KPI ko‘rsatkichlari joriy sintetik bajarilishdan olinadi. Ular real bank samaradorligini ifodalamaydi."));
  } else if (windowId === "signal_risk") {
    target.appendChild(element("p", "module-notice", "Risk balli ustuvorlik ko‘rsatkichi; u firibgarlik ehtimoli, aybdorlik yoki avtomatik bloklash qarori emas."));
  } else if (windowId === "layers_16") {
    const rows = Array.isArray(snapshot.layers_16) ? snapshot.layers_16 : [];
    const list = element("ol", "layer-detail-list");
    currentManifest.layers.forEach(([id, label], index) => {
      const runtimeLayer = rows.find(row => row.layer_id === id || row.layer_id === "L" + String(index + 1).padStart(2,"0"));
      const item = element("li", "layer-detail-item");
      item.append(element("strong", "", label), element("span", "layer-state", runtimeLayer?.status || "PARTIAL · tasdiqlanmagan"));
      list.appendChild(item);
    });
    target.appendChild(list);
  } else if (windowId === "dashboard") {
    target.appendChild(element("p", "module-notice", "Umumiy ko‘rinish barcha modullarning so‘nggi sintetik runtime natijasini jamlaydi. Quyidagi qiymatlar demo yoki oxirgi sinovdan olinadi."));
  }

  if (windowId !== "layers_16") {
    const metrics = element("div", "workspace-metrics");
    lines.forEach(line => {
      const card = element("div", "workspace-metric");
      card.appendChild(element("span", "metric-label", line.split(":")[0] || "Ko‘rsatkich"));
      card.appendChild(element("strong", "metric-value", line.includes(":") ? line.slice(line.indexOf(":")+1).trim() : line));
      metrics.appendChild(card);
    });
    target.appendChild(metrics);
  }
}
