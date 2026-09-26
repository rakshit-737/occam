import React, { useEffect, useMemo, useState } from "react";
import { RATINGS, score } from "./ach.js";

async function tryLive() {
  try {
    const r = await fetch("/scenarios", { headers: { Accept: "application/json" } });
    if (!r.ok || !(r.headers.get("content-type") || "").includes("json")) return null;
    return await r.json();
  } catch {
    return null;
  }
}

async function postAch(scenario, overrides) {
  const body = {
    scenario,
    overrides: Object.entries(overrides).map(([k, rating]) => {
      const [evidence, hypothesis] = k.split("|");
      return { evidence, hypothesis, rating };
    }),
  };
  const r = await fetch("/ach", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
}

function List({ title, items }) {
  return (
    <>
      <h3>{title}</h3>
      <ul>{(items.length ? items : ["none"]).map((x, i) => <li key={i}>{x}</li>)}</ul>
    </>
  );
}

export default function App() {
  const [mode, setMode] = useState("loading");
  const [names, setNames] = useState([]);
  const [demo, setDemo] = useState(null);
  const [scenario, setScenario] = useState("");
  const [overrides, setOverrides] = useState({});
  const [live, setLive] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      const liveNames = await tryLive();
      if (liveNames) {
        setMode("live");
        setNames(liveNames);
        setScenario(liveNames.includes("false_flag_games") ? "false_flag_games" : liveNames[0]);
        return;
      }
      const d = await (await fetch("demo-data.json")).json();
      setDemo(d);
      const n = Object.keys(d.scenarios);
      setNames(n);
      setScenario(n.includes("false_flag_games") ? "false_flag_games" : n[0]);
      setMode("static");
    })().catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (mode !== "live" || !scenario) return;
    postAch(scenario, overrides).then((a) => { setLive(a); setError(""); }).catch((e) => setError(e.message));
  }, [mode, scenario, overrides]);

  const view = useMemo(() => {
    if (mode === "live") return live;
    if (mode !== "static" || !demo || !scenario) return null;
    const s = demo.scenarios[scenario];
    const r = score({ ...s, base_matrix: s.matrix }, overrides, demo.spoofable_discount);
    return {
      ...s,
      matrix: r.matrix,
      diagnostic_weights: r.weights,
      ranking: r.ranking,
      leading_hypothesis: r.ranking[0].label,
      edited: Object.keys(overrides).length > 0,
    };
  }, [mode, live, demo, scenario, overrides]);

  const cycle = (eid, hid, cur) => {
    const next = RATINGS[(RATINGS.indexOf(cur) + 1) % RATINGS.length];
    setOverrides((o) => ({ ...o, [`${eid}|${hid}`]: next }));
  };

  return (
    <>
      <header>
        <h1>OCCAM analyst workbench</h1>
        <span className={`badge ${mode}`}>
          {mode === "live" ? "live API" : mode === "static" ? "static demo (no server)" : "loading"}
        </span>
        <p className="muted">
          Click any ACH cell to cycle its rating (CC, C, N, I, II).{" "}
          {mode === "static"
            ? "The ranking is recomputed in your browser; confidence grading needs the Python API."
            : "The assessment is recomputed by the API."}
        </p>
      </header>
      <main>
        <section>
          <div className="row">
            <label>
              Scenario{" "}
              <select value={scenario} onChange={(e) => { setScenario(e.target.value); setOverrides({}); }}>
                {names.map((n) => <option key={n}>{n}</option>)}
              </select>
            </label>
            <button onClick={() => setOverrides({})}>Reset overrides</button>
            {error && <span className="error">error: {error}</span>}
          </div>
          {view && (
            <>
              <p className="verdict">
                Leading hypothesis: <b>{view.leading_hypothesis}</b>
                {!view.edited && <> &middot; it is <b>{view.likelihood_phrase}</b> &middot; confidence <b className="conf">{view.confidence}</b></>}
                {view.edited && <> &middot; <span className="muted">confidence is not recomputed for edited matrices in the static demo</span></>}
              </p>
              <div className="scroll">
                <table>
                  <thead>
                    <tr>
                      <th className="ev">evidence</th><th>weight</th>
                      {view.ranking.map((h) => <th key={h.id} title={h.label}>{h.id}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {view.evidence.map((e) => (
                      <tr key={e.id}>
                        <td className="ev" title={e.description}>
                          {e.id}{e.spoofable ? "*" : ""} {e.description} <span className="muted">({e.grade})</span>
                        </td>
                        <td>{Number(view.diagnostic_weights[e.id]).toFixed(2)}</td>
                        {view.ranking.map((h) => {
                          const r = view.matrix[e.id][h.id];
                          const k = `${e.id}|${h.id}`;
                          return (
                            <td key={h.id} className={`cell ${r}${k in overrides ? " over" : ""}`}
                                onClick={() => cycle(e.id, h.id, r)} title="click to cycle rating">{r}</td>
                          );
                        })}
                      </tr>
                    ))}
                    <tr>
                      <th className="ev">weighted inconsistency</th><td />
                      {view.ranking.map((h) => <th key={h.id}>{h.inconsistency.toFixed(2)}</th>)}
                    </tr>
                  </tbody>
                </table>
              </div>
              {!view.edited && (
                <>
                  <List title="Rationale" items={view.rationale} />
                  <List title="False-flag indicators considered" items={view.false_flag_indicators} />
                  <List title="What would change this conclusion" items={view.what_would_change} />
                </>
              )}
              <p className="muted">* spoofable evidence (down-weighted). Synthetic scenarios. Decision support only; attribution requires human review.</p>
            </>
          )}
        </section>
      </main>
    </>
  );
}
