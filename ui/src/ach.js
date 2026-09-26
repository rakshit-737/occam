// Client-side port of the ACH scoring in occam/ach.py (weights + least-inconsistency ranking).
// Used only in the static demo, where no API is available. Confidence grading and its caps
// stay server-side; the static demo only shows them for the unedited matrix.
export const RATINGS = ["CC", "C", "N", "I", "II"];
export const VALUE = { CC: 2, C: 1, N: 0, I: -1, II: -2 };
const ORDER = { unknown: 0, false_flag: 1, actor: 2 };

export function diagWeight(ev, row, discount) {
  const vals = Object.values(row).map((r) => VALUE[r]);
  const spread = (Math.max(...vals) - Math.min(...vals)) / 4;
  const w = ev.base_weight * spread;
  return ev.spoofable ? w * discount : w;
}

export function score(snapshot, overrides, discount) {
  const matrix = {};
  for (const e of snapshot.evidence) {
    matrix[e.id] = {};
    for (const h of snapshot.hypotheses) {
      matrix[e.id][h.id] = overrides[`${e.id}|${h.id}`] || snapshot.base_matrix[e.id][h.id];
    }
  }
  const weights = {};
  for (const e of snapshot.evidence) weights[e.id] = diagWeight(e, matrix[e.id], discount);
  const ranking = snapshot.hypotheses.map((h) => {
    let inc = 0, sup = 0;
    for (const e of snapshot.evidence) {
      const v = VALUE[matrix[e.id][h.id]], w = weights[e.id];
      if (v < 0) inc += v * w; else if (v > 0) sup += v * w;
    }
    return { ...h, inconsistency: inc, support: sup };
  });
  ranking.sort((a, b) => (Math.round(b.inconsistency * 1e9) - Math.round(a.inconsistency * 1e9))
    || (ORDER[a.kind] - ORDER[b.kind]) || (b.support - a.support));
  return { matrix, weights, ranking };
}
