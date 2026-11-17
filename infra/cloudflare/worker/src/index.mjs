const WORK_WINDOW_MS = 60 * 60 * 1000;
const REST_WINDOW_MS = 10 * 60 * 1000;
const LEASE_MS = 4 * 60 * 1000;

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "no-store",
      "x-content-type-options": "nosniff",
      "referrer-policy": "no-referrer",
    },
  });
}

function iso(ms) {
  return new Date(ms).toISOString();
}

export async function runSupervisorTick(env, nowMs = Date.now()) {
  if (!env?.DB) throw new Error("D1 binding is not configured");
  const now = iso(nowMs);
  const leaseOwner = crypto.randomUUID();
  const leaseUntil = iso(nowMs + LEASE_MS);

  await env.DB.prepare(
    "INSERT OR IGNORE INTO runtime_state(id, mode, updated_at) VALUES (1, 'work', ?)"
  ).bind(now).run();

  const lease = await env.DB.prepare(`
    UPDATE runtime_state
       SET lease_owner = ?, lease_expires_at = ?, updated_at = ?
     WHERE id = 1
       AND (lease_expires_at IS NULL OR lease_expires_at < ? OR lease_owner = ?)
  `).bind(leaseOwner, leaseUntil, now, now, leaseOwner).run();

  if ((lease?.meta?.changes ?? 0) < 1) return { acquired: false, reason: "lease_held" };

  const row = await env.DB.prepare(
    "SELECT mode, work_started_at, work_deadline, rest_until FROM runtime_state WHERE id = 1"
  ).first();

  let eventType = "supervisor_checkpoint";
  let nextMode = row?.mode || "work";
  if (row?.mode === "paused") {
    eventType = "supervisor_paused";
  } else if (row?.mode === "rest" && row.rest_until && Date.parse(row.rest_until) > nowMs) {
    eventType = "rest_window";
  } else if (row?.mode === "rest") {
    nextMode = "work";
    eventType = "work_window_started";
    await env.DB.prepare(`
      UPDATE runtime_state
         SET mode = 'work', work_started_at = ?, work_deadline = ?,
             rest_until = NULL, last_checkpoint = ?, lease_owner = NULL,
             lease_expires_at = NULL, updated_at = ?
       WHERE id = 1 AND lease_owner = ?
    `).bind(now, iso(nowMs + WORK_WINDOW_MS), now, now, leaseOwner).run();
  } else if (row?.work_deadline && Date.parse(row.work_deadline) <= nowMs) {
    nextMode = "rest";
    eventType = "rest_window_started";
    await env.DB.prepare(`
      UPDATE runtime_state
         SET mode = 'rest', rest_until = ?, lease_owner = NULL,
             lease_expires_at = NULL, updated_at = ?
       WHERE id = 1 AND lease_owner = ?
    `).bind(iso(nowMs + REST_WINDOW_MS), now, leaseOwner).run();
  } else {
    await env.DB.prepare(`
      UPDATE runtime_state
         SET last_checkpoint = ?, lease_owner = NULL,
             lease_expires_at = NULL, updated_at = ?
       WHERE id = 1 AND lease_owner = ?
    `).bind(now, now, leaseOwner).run();
  }

  await env.DB.prepare(`
    INSERT INTO runtime_audit(event_id, event_type, details_json, created_at)
    VALUES (?, ?, ?, ?)
  `).bind(crypto.randomUUID(), eventType, JSON.stringify({ mode: nextMode }), now).run();

  return { acquired: true, mode: nextMode, event: eventType };
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET" && (url.pathname === "/" || url.pathname === "/health")) {
      try {
        await env.DB.prepare("SELECT 1 AS ok").first();
        return json({
          status: "ok",
          service: "finzanjir-runtime",
          durable_metadata: "d1_connected",
          object_storage: "r2_not_enabled",
          scheduler: "cron_configured",
          personal_data_import: "disabled_until_encryption_backup_and_auth_are_ready",
        });
      } catch {
        return json({ status: "degraded", service: "finzanjir-runtime", durable_metadata: "unavailable" }, 503);
      }
    }
    return json({ error: "not_found" }, 404);
  },

  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(runSupervisorTick(env).catch((error) => {
      console.error("FINZANJIR supervisor tick failed", error?.message || "unknown error");
    }));
  },
};
