"""OCCAM command-line interface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .ach import ACHEngine, render_matrix
from .attack import convert_stix_bundle, load
from .cluster import cluster
from .extract import extract, navigator_layer
from .scenario import load_scenario
from .stix import export

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "fixtures"


def _dump(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _classifier(path: str | None):
    if not path:
        return None
    from .classifier import TechniqueClassifier

    return TechniqueClassifier.load(path)


def cmd_extract(a) -> int:
    kb = load(a.kb)
    p = Path(a.file)
    r = extract(p.read_text(encoding="utf-8"), p.name, kb, classifier=_classifier(a.classifier))
    if a.navigator:
        _dump(navigator_layer(r))
    elif a.stix:
        _dump(export(extraction=r))
    else:
        _dump(r.to_dict())
    return 0


def cmd_cluster(a) -> int:
    kb = load(a.kb)
    files = sorted(Path(a.dir).glob("*.txt"))
    results = [extract(f.read_text(encoding="utf-8"), f.name, kb) for f in files]
    clusters = cluster(results, a.threshold, kb)
    for c in clusters:
        print(f"{c.id}: {', '.join(c.members)}")
        if c.shared_features:
            print(f"    shared: {', '.join(c.shared_features)}")
    if getattr(a, "cypher", None):
        from .neo4j import to_cypher

        events = {r.source_id: {"capability": sorted(r.technique_ids() | {h.technique_id for h in r.tools}),
                                "infrastructure": sorted({i.value.lower() for i in r.indicators})} for r in results}
        camp = {m: c.id for c in clusters for m in c.members}
        Path(a.cypher).write_text(to_cypher(events, camp), encoding="utf-8")
        print(f"wrote Neo4j Cypher script -> {a.cypher}")
    return 0


def _run_ach(path: str, overrides: list[str], kb_path: str | None):
    q, actors, evidence, _ = load_scenario(path)
    eng = ACHEngine(actors, evidence, q, kb=load(kb_path))
    for o in overrides or []:
        cell, rating = o.split("=", 1)
        eid, hid = cell.split(":", 1)
        eng.override(eid, hid, rating)
    return eng, evidence, eng.assess()


def _print_assessment(a, evidence) -> None:
    print(f"QUESTION: {a.question}\n")
    print(render_matrix(a, evidence))
    print(f"\nASSESSMENT: It is {a.likelihood_phrase} that: {a.leading.hypothesis.label}")
    print(f"CONFIDENCE: {a.confidence.upper()}")
    print("\nRationale:")
    for r in a.rationale:
        print(f"  - {r}")
    print("\nFalse-flag indicators considered:")
    for r in a.false_flag_indicators or ["none detected"]:
        print(f"  - {r}")
    print("\nWhat would change this conclusion:")
    for r in a.what_would_change:
        print(f"  - {r}")
    print("\nNOTE: decision-support output, not a finding; attribution requires human analytic review.")


def cmd_ach(a) -> int:
    _, evidence, assessment = _run_ach(a.scenario, a.override, a.kb)
    if a.json:
        _dump(assessment.to_dict())
    elif a.stix:
        _dump(export(assessment=assessment))
    else:
        _print_assessment(assessment, evidence)
    return 0


def cmd_load_attack(a) -> int:
    bundle = json.loads(Path(a.bundle).read_text(encoding="utf-8"))
    out = convert_stix_bundle(bundle)
    Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"wrote {len(out['techniques'])} techniques, {len(out['tools'])} tools -> {a.out}")
    return 0


def cmd_attribute(a) -> int:
    """Report text -> span-anchored TTPs/software -> ACH over real ATT&CK group profiles."""
    from .attribution import ACHAttributor, evidence_from_items
    from .knowledge import AttackData

    data = AttackData.load(a.attack)
    kb = data.to_kb()
    p = Path(a.file)
    text = p.read_text(encoding="utf-8", errors="replace")
    r = extract(text, p.name, kb, classifier=_classifier(a.classifier))
    items = sorted(r.technique_ids() | {h.technique_id for h in r.tools})
    if not items:
        print("no ATT&CK techniques or software found in the report; nothing to attribute")
        return 1
    ev = evidence_from_items(items, kb)
    spans = {h.technique_id: h.span for h in r.techniques + r.tools}
    for e in ev:
        s = spans.get(e.value)
        if s:
            e.description += f"  <- {s.text!r} @{s.start}"
    candidates = ACHAttributor(data.actor_profiles(), kb, shortlist=a.shortlist).candidates(ev)
    eng = ACHEngine(candidates, ev, f"Which ATT&CK group conducted the activity in {p.name}?", kb=kb)
    asmt = eng.assess()
    if getattr(a, "calibration", None):
        from .calibration import GradeCalibrator

        p_cal = GradeCalibrator.load(a.calibration)[asmt.confidence]
        asmt.rationale.append(f"Calibrated probability for a {asmt.confidence.upper()} grade: {p_cal:.2f} "
                              f"(learned map {a.calibration}).")
    if a.json:
        _dump(asmt.to_dict())
    else:
        print(f"{len(items)} evidence items from {p.name}; {len(candidates)} candidate groups "
              f"(top-{a.shortlist} by TTP similarity) + unknown / false-flag hypotheses\n")
        print("EVIDENCE (each linked to its source span):")
        for e in ev:
            print(f"  {e.id:<5} {e.description}")
        print()
        _print_assessment(asmt, ev)
    return 0


def cmd_train_classifier(a) -> int:
    """Train the sentence-level technique classifier on ATT&CK procedures (+ TRAM2)."""
    from .classifier import TechniqueClassifier, training_corpus
    from .knowledge import AttackData

    data = AttackData.load(a.attack)
    texts, labels = training_corpus(data)
    if a.tram:
        rows = json.loads(Path(a.tram).read_text(encoding="utf-8"))
        texts += [r["sentence"] for r in rows]
        labels += [set(r["labels"]) for r in rows]
    clf = TechniqueClassifier(threshold=a.threshold, names={t: v.name for t, v in data.techniques.items()})
    clf.fit(texts, labels)
    clf.save(a.out)
    print(f"trained on {len(texts)} sentences, {len(clf.classes)} techniques -> {a.out}")
    return 0


def cmd_demo(a) -> int:
    print("=" * 70 + "\n[1] TTP extraction (span-anchored)\n" + "=" * 70)
    rep = FIXTURES / "reports" / "r3_tide_energy.txt"
    r = extract(rep.read_text(encoding="utf-8"), rep.name)
    for h in r.techniques:
        print(f"  {h.technique_id:<10} {h.name:<38} <- {h.span.text!r} @{h.span.start}")
    for i in r.indicators:
        print(f"  IOC {i.type:<7} {i.value}")
    print("\n" + "=" * 70 + "\n[2] Campaign clustering\n" + "=" * 70)
    ns = argparse.Namespace(dir=str(FIXTURES / "reports"), threshold=0.3, kb=None)
    cmd_cluster(ns)
    for name in ("clean_attribution", "false_flag_games", "thin_evidence"):
        print("\n" + "=" * 70 + f"\n[ACH] scenario: {name}\n" + "=" * 70)
        _, ev, asmt = _run_ach(str(FIXTURES / "scenarios" / f"{name}.json"), [], None)
        _print_assessment(asmt, ev)
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="occam", description=__doc__)
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--kb", help="alternate ATT&CK KB JSON (from `occam load-attack`)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("extract", help="extract IOCs + ATT&CK techniques from a text report")
    s.add_argument("file")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--navigator", action="store_true", help="emit ATT&CK Navigator layer")
    g.add_argument("--stix", action="store_true", help="emit STIX 2.1 bundle")
    s.add_argument("--classifier", help="trained model from `occam train-classifier` (adds ML technique hits)")
    s.set_defaults(func=cmd_extract)

    s = sub.add_parser("cluster", help="cluster *.txt reports in a directory into campaigns")
    s.add_argument("dir")
    s.add_argument("--threshold", type=float, default=0.3)
    s.add_argument("--cypher", metavar="FILE", help="also write the Diamond graph + campaigns as a Neo4j Cypher script")
    s.set_defaults(func=cmd_cluster)

    s = sub.add_parser("ach", help="run ACH attribution on a scenario JSON")
    s.add_argument("scenario")
    s.add_argument("--override", action="append", metavar="EID:HID=RATING", help="analyst cell override, e.g. E5:H-TIDE=II")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--json", action="store_true")
    g.add_argument("--stix", action="store_true")
    s.set_defaults(func=cmd_ach)

    s = sub.add_parser("load-attack", help="convert a local enterprise-attack.json STIX bundle to OCCAM KB format")
    s.add_argument("bundle")
    s.add_argument("--out", default="attack_kb.json")
    s.set_defaults(func=cmd_load_attack)

    s = sub.add_parser("attribute", help="attribute a report to ATT&CK groups with ACH (needs enterprise-attack.json)")
    s.add_argument("file")
    s.add_argument("--attack", required=True, help="path to MITRE ATT&CK enterprise-attack STIX bundle")
    s.add_argument("--calibration", help="learned grade->probability map (results/grade_calibration.json)")
    s.add_argument("--shortlist", type=int, default=8, help="candidate groups kept by TTP similarity (default 8)")
    s.add_argument("--classifier", help="trained model from `occam train-classifier` (adds ML technique hits)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_attribute)

    s = sub.add_parser("train-classifier", help="train the text->technique classifier (needs the `ml` extra)")
    s.add_argument("--attack", required=True, help="path to enterprise-attack STIX bundle")
    s.add_argument("--tram", help="optional TRAM2 multi_label.json for extra training sentences")
    s.add_argument("--threshold", type=float, default=0.8, help="decision threshold stored with the model")
    s.add_argument("--out", default="occam_classifier.pkl")
    s.set_defaults(func=cmd_train_classifier)

    s = sub.add_parser("demo", help="run all demo scenarios on bundled synthetic fixtures")
    s.set_defaults(func=cmd_demo)

    a = p.parse_args(argv)
    try:
        return a.func(a)
    except (ValueError, KeyError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
