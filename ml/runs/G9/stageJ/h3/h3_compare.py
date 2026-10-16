"""G9 H3 baseline comparison (frozen plan v2, section 6). Computes the E1-E8 table for every arm (G3, H2, H3) on EXACTLY the same
human-verified J-eval items, using j_gates (Wilson PASS / FAIL / UNCERTAIN). Grades are not computed: any graded=1 row is a
grading-safety violation (A/B/C grades stay blocked; hard-coded UI demo values such as "97% / Grade A" are never inputs).

Inputs
  --truth   verified_manifest_pilot*.csv (one or more; rows with status verified_* only; columns item_id, class13, role)
  --pred    predictions CSV: item_id, arm, pred_class13, accepted (0/1), graded (0/1), latency_ms (full pipeline: detector + crop + classifier)
  --occ-suite JSON {arm: {"overall": rate, "per_type_max": rate, "n": int}}  (Stage H synthetic occlusion suite, n >= 900)
Usage: h3_compare.py --truth M.csv [--truth M2.csv] --pred P.csv [--occ-suite occ.json] --out table.md [--dry-run]"""
from __future__ import annotations
import argparse, csv, json, random, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import j_gates as G  # noqa: E402

PRIORITY = ("apple", "banana", "citrus", "tomato", "carrot")
NONSUP = ("unsupported", "printed", "supported_packaged", "cut")


def metrics(truth: dict, preds: list) -> dict:
    by = defaultdict(dict)
    for p in preds: by[p["arm"]][p["item_id"]] = p
    arms = sorted(by)
    common = set(truth)
    for a in arms: common &= set(by[a])
    out = {}
    for a in arms:
        P = by[a]; I = sorted(common)
        sup = [i for i in I if truth[i]["role"] == "supported"]
        acc = lambda i: str(P[i]["accepted"]) == "1"; grd = lambda i: str(P[i]["graded"]) == "1"; pc = lambda i: P[i]["pred_class13"]
        k_rec = sum(pc(i) == truth[i]["class13"] for i in sup)
        k_gen = sum(acc(i) and pc(i) == truth[i]["class13"] for i in sup)
        k_wrong = sum(acc(i) and pc(i) != truth[i]["class13"] and pc(i) != "unknown" for i in sup)
        per = {c: (sum(acc(i) and pc(i) == c for i in sup if truth[i]["class13"] == c), sum(1 for i in sup if truth[i]["class13"] == c)) for c in PRIORITY}
        ns = [i for i in I if truth[i]["role"] in NONSUP]; k_ns = sum(acc(i) and pc(i) in PRIORITY for i in ns)
        oc = [i for i in I if truth[i]["role"] == "other_class"]; k_oc = sum(acc(i) and pc(i) in PRIORITY for i in oc)
        occ = [i for i in I if truth[i]["role"] == "occluded"]; k_occ = sum(acc(i) for i in occ)
        lat = sorted(float(P[i].get("latency_ms") or 0) for i in I)
        p95 = lat[min(len(lat) - 1, int(round(0.95 * (len(lat) - 1))))] if lat else None
        out[a] = dict(n_items=len(I), n_supported=len(sup), recognition=(k_rec, len(sup)), genuine_acceptance=(k_gen, len(sup)),
                      genuine_by_class=per, wrong_id=(k_wrong, len(sup)), wrong_id_graded=sum(grd(i) and acc(i) and pc(i) != truth[i]["class13"] for i in sup),
                      nonsupported_accept=(k_ns, len(ns)), nonsupported_graded=sum(grd(i) for i in ns), other_class_accept=(k_oc, len(oc)),
                      occluded_accept=(k_occ, len(occ)), occluded_graded=sum(grd(i) for i in occ), any_graded=sum(grd(i) for i in I),
                      latency_p95_ms=p95, latency_p50_ms=lat[len(lat) // 2] if lat else None)
    return out


def gates(m: dict, occ_suite: dict | None) -> dict:
    g = {}
    for a, x in m.items():
        e1 = G.at_least(*x["genuine_acceptance"], 0.60)
        e1c = {c: G.at_least(k, n, 0.40) for c, (k, n) in x["genuine_by_class"].items()}
        e2 = G.at_most(*x["wrong_id"], 0.02, 0.06); e2z = G.zero_required(x["wrong_id_graded"])
        e3 = G.at_most(*x["nonsupported_accept"], 0.02, 0.06); e3z = G.zero_required(x["nonsupported_graded"])
        e4 = G.at_most(*x["other_class_accept"], 0.03, 0.08)
        s = (occ_suite or {}).get(a)
        e5 = ("PASS" if s and s["n"] >= 900 and s["overall"] <= 0.03 and s["per_type_max"] <= 0.05 else "FAIL" if s else "NOT_MEASURED")
        e5z = G.zero_required(x["occluded_graded"])
        e6 = "PASS" if x["latency_p95_ms"] is not None and x["latency_p95_ms"] <= 60 else "FAIL"
        safety = G.zero_required(x["any_graded"])
        g[a] = dict(E1=e1, E1_per_class=e1c, E2=e2, E2_zero_graded=e2z, E3=e3, E3_zero_graded=e3z, E4=e4, E5_suite=e5, E5_real_zero_graded=e5z,
                    E6_latency=e6, grading_safety_zero_graded=safety)
    if "H3" in m:
        h = m["H3"]; rate = lambda t: t[0] / t[1] if t[1] else 0
        better = all(rate(h["genuine_acceptance"]) > rate(m[b]["genuine_acceptance"]) and rate(h["wrong_id"]) <= rate(m[b]["wrong_id"]) for b in m if b != "H3")
        g["H3"]["E7_better_than_G3_and_H2"] = "PASS" if better else "FAIL"
    return g


def table(m: dict, g: dict) -> str:
    f = lambda t: f"{t[0]}/{t[1]} ({t[0] / t[1]:.1%})" if t[1] else "0/0"
    arms = list(m)
    L = ["| Metric (same items) | " + " | ".join(arms) + " |", "|---" * (len(arms) + 1) + "|"]
    rows = [("Recognition (top-1 on clean supported)", lambda a: f(m[a]["recognition"])),
            ("E1 genuine acceptance (>= 0.60)", lambda a: f"{f(m[a]['genuine_acceptance'])} {g[a]['E1']}"),
            ("E1 per class (>= 0.40)", lambda a: ", ".join(f"{c} {g[a]['E1_per_class'][c]}" for c in PRIORITY)),
            ("E2 wrong ID (<= 2%; 0 graded)", lambda a: f"{f(m[a]['wrong_id'])} {g[a]['E2']}; graded {m[a]['wrong_id_graded']}"),
            ("E3 unsupported/printed/packaged/cut accepted (<= 2%; 0 graded)", lambda a: f"{f(m[a]['nonsupported_accept'])} {g[a]['E3']}"),
            ("E4 other produce accepted as priority (<= 3%)", lambda a: f"{f(m[a]['other_class_accept'])} {g[a]['E4']}"),
            ("E5 occlusion leakage: suite / real occluded accepted", lambda a: f"{g[a]['E5_suite']} / {f(m[a]['occluded_accept'])}, graded {m[a]['occluded_graded']}"),
            ("Grading safety (any grade shown = FAIL)", lambda a: f"{m[a]['any_graded']} graded {g[a]['grading_safety_zero_graded']}"),
            ("E6 full-pipeline latency p50 / p95 (<= 60 ms)", lambda a: f"{m[a]['latency_p50_ms']} / {m[a]['latency_p95_ms']} ms {g[a]['E6_latency']}"),
            ("E7 better than G3 and H2", lambda a: g[a].get("E7_better_than_G3_and_H2", "-"))]
    L += [f"| {name} | " + " | ".join(fn(a) for a in arms) + " |" for name, fn in rows]
    return "\n".join(L) + "\n\nUNCERTAIN is reported as uncertain, never as a pass. Grades stay blocked regardless of this table.\n"


def synthetic(seed=0):
    r = random.Random(seed); truth = {}; preds = []
    roles = ["supported"] * 120 + ["unsupported"] * 25 + ["printed"] * 10 + ["supported_packaged"] * 10 + ["occluded"] * 10 + ["other_class"] * 10
    for n, role in enumerate(roles):
        c = PRIORITY[n % 5] if role in ("supported", "supported_packaged") else "unknown"
        truth[f"Q{n:03d}"] = dict(class13=c, role=role)
    for arm, p_acc in (("G3", 0.30), ("H2", 0.14), ("H3", 0.70)):
        for i, t in truth.items():
            ok = r.random() < p_acc
            pred = t["class13"] if ok and t["role"] == "supported" else "unknown"
            preds.append(dict(item_id=i, arm=arm, pred_class13=pred, accepted=int(pred != "unknown"), graded=0, latency_ms=round(r.uniform(20, 55), 1)))
    return truth, preds


def main(argv=None):
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--truth", action="append", default=[]); a.add_argument("--pred"); a.add_argument("--occ-suite"); a.add_argument("--out")
    a.add_argument("--dry-run", action="store_true")
    x = a.parse_args(argv)
    if x.dry_run:
        truth, preds = synthetic()
    else:
        truth = {r["item_id"]: r for p in x.truth for r in csv.DictReader(open(p)) if r["status"].startswith("verified")}
        preds = list(csv.DictReader(open(x.pred)))
    m = metrics(truth, preds); g = gates(m, json.load(open(x.occ_suite)) if x.occ_suite else None)
    md = ("# SYNTHETIC DRY RUN - not results\n\n" if x.dry_run else "") + table(m, g)
    if x.out: Path(x.out).write_text(md)
    print(md); return m, g


if __name__ == "__main__":
    main()
