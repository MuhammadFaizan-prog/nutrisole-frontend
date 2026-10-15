"""G9 H3 launch guard (Stage J3). Refuses to launch H3 unless BOTH hold:
  (1) the verified HUMAN manifests pass the frozen readiness gates (G9_stageJ_readiness.md R1-R4, T1-T5), recomputed here from the
      frozen j_agree outputs (hash-checked), with j_agree.readiness_counts and j_gates; and
  (2) a user-written training-go file exists (h3/USER_TRAINING_GO.json) that names THIS frozen plan (sha256 of
      docs/cv/gauntlet/G9_stageJ3_H3_frozen_plan_v2.md) and the exact verified-manifest hashes.
The agent never writes USER_TRAINING_GO.json. Nothing here trains; a pass only allows h3_launch.py to push the Kaggle kernel.

Inputs: h3/h3_inputs.json (written by the lead after `j_agree.py verify`):
  {"batches": {"pilot":  {"verify_dir": "...", "agree_dir": "..."}, "pilot2": {...}, "train": {...}, "train2": {...},
               "team_eval": {... optional ...}, "team_train": {... optional ...}}}
Usage: h3_guard.py [--inputs h3_inputs.json] [--go USER_TRAINING_GO.json] [--report out.json]   exit 0 = PASS, 2 = REFUSED
"""
from __future__ import annotations
import argparse, csv, hashlib, json, sys
from collections import Counter
from datetime import datetime
from pathlib import Path

H3 = Path(__file__).resolve().parent; J = H3.parent; ROOT = J.parents[3]
sys.path.insert(0, str(J / "scripts"))
import j_agree as JA  # noqa: E402
import j_gates as G   # noqa: E402

PLAN = ROOT / "docs/cv/gauntlet/G9_stageJ3_H3_frozen_plan_v2.md"
EVAL_BATCHES = ("pilot", "pilot2", "team_eval"); TRAIN_BATCHES = ("train", "train2", "team_train")
PRIORITY13 = ("apple", "banana", "citrus", "tomato", "carrot")
EVAL_ONLY_SOURCES = {"fruitnet", "carrot_m", "tomato_m"}
NEG_ROLES = ("unsupported", "other_class", "printed", "occluded", "cut", "supported_packaged")


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_batch(name, spec, problems):
    vd, ad = Path(spec["verify_dir"]), Path(spec["agree_dir"])
    sp, mp = vd / f"verified_summary_{name}.json", vd / f"verified_manifest_{name}.csv"
    ap = ad / "agreement.json"
    for p in (sp, mp, Path(str(mp) + ".sha256"), ap, Path(str(ap) + ".sha256")):
        if not p.exists(): problems.append(f"{name}: missing {p}"); return None
    if sha(mp) != Path(str(mp) + ".sha256").read_text().split()[0]: problems.append(f"{name}: manifest hash mismatch"); return None
    if sha(ap) != Path(str(ap) + ".sha256").read_text().split()[0]: problems.append(f"{name}: agreement hash mismatch"); return None
    S = json.loads(sp.read_text()); A = json.loads(ap.read_text())
    if S.get("provenance") != "HUMAN_INDEPENDENT" or A.get("provenance") != "HUMAN_INDEPENDENT": problems.append(f"{name}: not HUMAN_INDEPENDENT"); return None
    if S.get("sha256") != sha(mp) or S.get("agreement_sha256") != sha(ap): problems.append(f"{name}: summary does not bind manifest/agreement"); return None
    if not S.get("complete"): problems.append(f"{name}: R3/T4 adjudication or coverage incomplete")
    rows = list(csv.DictReader(open(mp, newline="", encoding="utf-8")))
    if any(r.get("provenance") != "HUMAN_INDEPENDENT" for r in rows): problems.append(f"{name}: non-human rows in manifest")
    return dict(rows=rows, summary=S, agreement=A, manifest_sha256=sha(mp))


def evaluate(inputs: dict) -> dict:
    problems, B = [], {}
    for name, spec in (inputs.get("batches") or {}).items():
        b = load_batch(name, spec, problems)
        if b: B[name] = b
    for need in ("pilot", "pilot2", "train", "train2"):
        if need not in B and not any(need in p for p in problems): problems.append(f"{need}: no verified human manifest")
    gates = {}
    # R1 / T4 agreement floors
    for n, b in B.items():
        k, ks = b["agreement"].get("kappa_class"), b["agreement"].get("kappa_supported")
        if n in EVAL_BATCHES:
            gates[f"R1_{n}"] = bool(k is not None and k >= 0.85 and ks is not None and ks >= 0.80)
        else:
            gates[f"T4_{n}"] = bool(k is not None and k >= 0.85)
    ver = lambda names: [r for n in names if n in B for r in B[n]["rows"] if r["status"].startswith("verified")]
    ev, trn = ver(EVAL_BATCHES), ver(TRAIN_BATCHES)
    sup = Counter(r["class13"] for r in ev if r["role"] == "supported" and r["split"] == "J-eval")
    neg = Counter(r["role"] for r in ev if r["split"] == "J-eval" and r["role"] in NEG_ROLES)
    pend = Counter(r["status"] for n in EVAL_BATCHES if n in B for r in B[n]["rows"])
    r2 = JA.readiness_counts("pilot", sup, neg, pend)
    gates["R2_counts_pilot_plus_pilot2"] = bool(r2["R2_met"]); gates["R2_subquotas"] = bool(r2["R2_subquotas_met"])
    gates["R3_complete"] = all(B[n]["summary"].get("complete") for n in EVAL_BATCHES if n in B) and all(n in B for n in ("pilot", "pilot2"))
    gates["R4_frozen"] = all((Path(inputs["batches"][n]["verify_dir"]) / f"verified_manifest_{n}.csv.sha256").exists() for n in EVAL_BATCHES if n in B)
    tsup = Counter(r["class13"] for r in trn if r["role"] == "supported" and r["split"] == "J-train")
    tsrc = {c: {r["source"] for r in trn if r["role"] == "supported" and r["split"] == "J-train" and r["class13"] == c} for c in PRIORITY13}
    gates["T1_volume_ge150_per_class"] = all(tsup.get(c, 0) >= 150 for c in PRIORITY13)
    gates["T1_ge2_sources_per_class"] = all(len(tsrc[c]) >= 2 for c in PRIORITY13)
    gates["T2_real_negatives_ge150"] = sum(1 for r in trn if r["split"] == "J-train" and r["role"] in NEG_ROLES) >= 150
    dev = Counter(r["class13"] for r in trn if r["split"] == "J-dev" and r["role"] == "supported")
    gates["T3_dev_ge10_per_class"] = all(dev.get(c, 0) >= 10 for c in PRIORITY13)
    ev_keys = {r["cand_key"] for r in ev}; bad_src = [r["cand_key"] for r in trn if r["source"].lower() in EVAL_ONLY_SOURCES]
    overlap = sorted(ev_keys & {r["cand_key"] for r in trn})
    gates["T5_separation"] = not overlap and not bad_src and all(r["split"] in ("J-train", "J-dev") for r in trn)
    # statistical sanity on the eval set size (j_gates): with the frozen eval counts, can E1 even be decided?
    n_sup = sum(sup.values())
    gates["E1_decidable_with_current_eval"] = n_sup >= 100 and G.wilson(int(0.6 * n_sup), n_sup)[0] >= 0.50 if n_sup else False
    for k, v in gates.items():
        if not v: problems.append(f"gate {k} not met")
    return dict(ready=not problems, gates=gates, problems=problems, eval_supported_by_class=dict(sup), eval_negatives=dict(neg),
                train_supported_by_class=dict(tsup), manifests={n: b["manifest_sha256"] for n, b in B.items()})


def check_go(go_path: Path, manifests: dict) -> list:
    if not go_path.exists(): return [f"no user training-go file at {go_path} (the user must write it; the agent never does)"]
    g = json.loads(go_path.read_text(encoding="utf-8"))
    p = []
    if g.get("go") is not True or g.get("experiment") != "H3": p.append("go file must contain go=true and experiment=H3")
    if not str(g.get("given_by", "")).strip() or JA.V.NONHUMAN.search(str(g.get("given_by", ""))): p.append("go file needs the user's name in given_by")
    try:
        t = datetime.fromisoformat(str(g.get("given_at", "")).replace("Z", "+00:00"))
        if t.tzinfo is None: p.append("given_at needs a timezone")
    except ValueError: p.append("given_at must be an ISO time")
    if g.get("plan_sha256") != (sha(PLAN) if PLAN.exists() else None): p.append("go file does not name the current frozen H3 plan (plan_sha256)")
    if g.get("manifest_sha256") != manifests: p.append("go file manifest hashes differ from the verified manifests")
    return p


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--inputs", default=str(H3 / "h3_inputs.json")); a.add_argument("--go", default=str(H3 / "USER_TRAINING_GO.json"))
    a.add_argument("--report")
    x = a.parse_args(argv)
    ip = Path(x.inputs)
    res = evaluate(json.loads(ip.read_text())) if ip.exists() else dict(ready=False, gates={}, problems=[f"no {ip.name}: no verified human manifests yet"], manifests={})
    go_problems = check_go(Path(x.go), res["manifests"])
    res["training_go_problems"] = go_problems
    res["verdict"] = "PASS" if res["ready"] and not go_problems else "REFUSED"
    txt = json.dumps(res, indent=1)
    if x.report: Path(x.report).write_text(txt)
    print(txt)
    return 0 if res["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
