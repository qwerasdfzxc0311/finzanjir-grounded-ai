import test from "node:test";
import assert from "node:assert/strict";
import worker from "../infra/cloudflare/worker/src/index.mjs";

test("health endpoint checks D1 and reports import gate closed", async () => {
  const env = {
    DB: { prepare: (sql) => ({ first: async () => {
      assert.equal(sql, "SELECT 1 AS ok");
      return { ok: 1 };
    }}) },
  };
  const response = await worker.fetch(new Request("https://runtime.example/health"), env);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.status, "ok");
  assert.equal(body.durable_metadata, "d1_connected");
  assert.equal(body.personal_data_import, "disabled_until_encryption_backup_and_auth_are_ready");
});

test("unknown routes fail closed", async () => {
  const response = await worker.fetch(new Request("https://runtime.example/private"), { DB: {} });
  assert.equal(response.status, 404);
});
