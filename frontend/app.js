Promise.all([
  fetch("./prototype_manifest.json").then(r=>r.json()),
  fetch("/api/prototype/demo").then(r=>r.json())
]).then(([m, prototypeResult])=>{
  document.querySelector("#mode").textContent=m.data_mode;
  const labels=Object.fromEntries(m.windows.map(([id,label])=>[id,label]));
  document.querySelector("#windows").innerHTML=m.windows.map(([id,label])=>{
    const role=m.window_roles[id];
    const inFlow=id===m.system_flow.entry||m.system_flow.transitions.some(([a,b])=>a===id||b===id);
    return `<article class="card ${inFlow?"":"muted-card"}"><strong>${label}</strong><p class="muted">${role.output}</p><small>${role.input}</small></article>`;
  }).join("");
  document.querySelector("#flow").innerHTML=m.system_flow.transitions.map(([a,b],i)=>
    `<div class="flow-step"><span class="badge">${i+1}</span><strong>${labels[a]}</strong><span class="arrow">→</span><strong>${labels[b]}</strong></div>`
  ).join("");
  document.querySelector("#layers").innerHTML=m.layers.map(([id,label])=>`<li><span class="badge">${id}</span> ${label}</li>`).join("");

  const runtime=prototypeResult.runtime;
  const rules=prototypeResult.explanation;
  document.querySelector("#prototypeResult").innerHTML=`
    <p><strong>${runtime.transaction_id}</strong> · ${prototypeResult.data_mode} · risk: ${runtime.risk_level ?? "NO_RISK"}</p>
    <p>Signal: ${runtime.signal_id ?? "yo‘q"} · Evidence: ${runtime.evidence_id ?? "yo‘q"} · Case: ${runtime.case_id ?? "ochilmadi"}</p>
    <p>Cross-bank matches: ${runtime.cross_bank_matches} · 16 qatlam qamrovi: ${runtime.layers_covered}</p>
    <p class="muted">Bu demo tushuntirish uchun sintetik. Signal firibgarlik isboti emas, Risk aybdorlik emas, Case yakuniy huquqiy qaror emas. AI ham yakuniy qaror egasi emas.</p>
  `;
}).catch(()=>{
  document.querySelector("#windows").innerHTML="<p>Prototype manifest unavailable.</p>";
  document.querySelector("#flow").innerHTML="<p>System flow unavailable.</p>";
  document.querySelector("#prototypeResult").innerHTML="<p>Runtime demo unavailable.</p>";
});
