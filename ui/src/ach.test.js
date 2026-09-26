import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { score } from "./ach.js";

const data = JSON.parse(readFileSync(new URL("../public/demo-data.json", import.meta.url)));

test("client-side scoring reproduces the server ranking for every bundled scenario", () => {
  for (const [name, s] of Object.entries(data.scenarios)) {
    const snap = { ...s, base_matrix: s.matrix };
    const r = score(snap, {}, data.spoofable_discount);
    assert.equal(r.ranking[0].id, s.ranking[0].id, name);
    r.ranking.forEach((h, i) => assert.ok(Math.abs(h.inconsistency - s.ranking[i].inconsistency) < 1e-3, `${name} ${h.id}`));
  }
});

test("an override changes the matrix and can move the ranking", () => {
  const s = data.scenarios.false_flag_games;
  const snap = { ...s, base_matrix: s.matrix };
  const top = s.ranking[0].id;
  const ov = {};
  for (const e of s.evidence) ov[`${e.id}|${top}`] = "II";
  const r = score(snap, ov, data.spoofable_discount);
  assert.notEqual(r.ranking[0].id, top);
});
