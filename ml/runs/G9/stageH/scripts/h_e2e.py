"""Stage H P3 DEV end-to-end evaluation with FROZEN configs (identity pick from out/identity.json, occlusion pick from out/occlusion.json).
Per eval item (CU-check items, CU-neg check, H-eval) the full close-up path runs on the full-res crop (analysis copy <= 256 px):
wide ID -> H2 verify (+H1 if P-b) -> occlusion (mask cues + H2 half-crop agreement) -> Stage G quality checks (single still, 96 px gate on
native side) -> internal 'graded'. H0 = Stage G path (wide ID -> checks -> graded). Reports identity / grading / safety separately, the
occluded-crop leakage through the FULL pipeline, e2e latency, and fresh/rotten agreement where agent labels exist. Writes out/e2e_h.json.
Usage: h_e2e.py"""
import json, sys, time, collections, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageG/scripts"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageH/scripts")
from g_models import assess
from ml.eval.closeup import quality_reasons, FROZEN_GATE, blockiness, ANALYSIS_MAX_SIDE
from ml.eval.verify import verify_identity, stageh_decision
from ml.eval.occlusion import cues, occlusion_reasons
from ml.grading.measure import object_mask
from h_ident import h2_probs, halves
from ml.eval.verify import part_agreement
B = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
ID = json.load(open(f"{B}/identity.json")); OC = json.load(open(f"{B}/occlusion.json")); PV = ID["pick"]; PO = OC["pick"]; MINP = OC.get("part_minP", 0.3)
R = [json.loads(l) for l in open(f"{B}/ident_items.jsonl")]; GR = {"A", "B", "C", "Reject"}
def cap(c):
    h, w = c.shape[:2]; s = ANALYSIS_MAX_SIDE / max(h, w)
    return cv2.resize(c, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA) if s < 1 else c
def wide(r): return dict(status="identified", classId=r["wide"]["classId"]) if r["wide"]["status"] == "identified" else dict(status="unable")
def h1(r): return dict(classId=r["h1"]["classId"], score=r["h1"]["score"], hasWide=r["h1"]["hasWide"]) if r["h1"]["classId"] is not None else None
def stage_g(crop, cls, side):
    a = assess(crop, cls); q = dict(sidePx=side, blurVar=a["blurVar"], meanV=a["meanV"], touchesEdge=False, visibleFrac=a["visibleFrac"], maxProb=a["maxProb"], margin=a["margin"],
                                    blockiness=blockiness(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)))
    rs = quality_reasons(q, FROZEN_GATE); ok = a["grade"] in GR and not rs
    return ok, a, rs
rows = []; lat = collections.defaultdict(list)
for r in R:
    if r["split"] != "eval": continue
    crop = cap(cv2.imread(r["crop"])); w = wide(r)
    t0 = time.perf_counter(); p, _ = h2_probs(crop); t1 = time.perf_counter()
    v = verify_identity(w, h1(r), p, PV); t2 = time.perf_counter()
    hp = [h2_probs(c)[0] for c in halves(crop)]; t3 = time.perf_counter()
    m, _ = object_mask(crop[:, :, ::-1].copy()); cu = cues(crop, m)
    if v["status"] == "verified": cu["partAgree"] = part_agreement(hp, v["classId"], MINP)
    occ = occlusion_reasons(cu, PO) if v["status"] == "verified" else []; t4 = time.perf_counter()
    cls_h0 = N[w["classId"]] if w["status"] == "identified" else None
    g_ok, a, rs = stage_g(crop, cls_h0 or (N[v["classId"]] if v["status"] == "verified" else "apple"), r["side"]); t5 = time.perf_counter()
    lat["h2"].append((t1 - t0) * 1e3); lat["parts"].append((t3 - t2) * 1e3); lat["occlusion_cues"].append((t4 - t3) * 1e3); lat["stageG_assess"].append((t5 - t4) * 1e3)
    lat["closeup_total"].append((t5 - t0) * 1e3 + r["h1"]["ms"] * (PV["policy"] == "P-b"))
    h0_graded = cls_h0 is not None and g_ok
    d = stageh_decision(v, occ, "graded" if g_ok else "not_graded", rs, True)
    rows.append(dict(key=r["key"], set=r["set"], group=r["group"], truth=r["truth"], label=r.get("label"), wide=cls_h0, verified=N[v["classId"]] if v["status"] == "verified" else None,
                     reason=v.get("reason"), suggestions=[N[i] if i < 12 else "unknown" for i in v.get("suggestions", [])], occ=occ, gate_ok=g_ok, gate_reasons=rs,
                     h0_graded=h0_graded, h_graded=d["outcome"] == "graded", outcome=d["outcome"], cond=a["cond"], grade=a["grade"], side=r["side"]))
def summ(name, graded_key, id_key):
    g = [x for x in rows if x[graded_key]]; sup = [x for x in rows if x["group"] in ("item", "crowd") and x["truth"] in N]
    neg = [x for x in rows if x["group"] in ("unsupported", "printed", "cut")]
    wrong_g = [x for x in g if x["truth"] not in N or x[id_key] != x["truth"]]
    lab = [x for x in g if x["label"] in ("f", "r") and x[id_key] == x["truth"]]
    return dict(graded=len(g), graded_wrong_identity=len(wrong_g), wrong_identity_grading_rate=round(len(wrong_g) / max(len(g), 1), 4),
                graded_unsupported=sum(1 for x in g if x["group"] in ("unsupported", "printed", "cut")), n_supported=len(sup),
                supported_graded_correct_id=sum(1 for x in sup if x[graded_key] and x[id_key] == x["truth"]),
                supported_graded_rate=round(sum(1 for x in sup if x[graded_key] and x[id_key] == x["truth"]) / max(len(sup), 1), 4),
                cu_items_graded_rate=round(sum(1 for x in sup if x["set"] == "cu" and x[graded_key] and x[id_key] == x["truth"]) / max(sum(1 for x in sup if x["set"] == "cu"), 1), 4),
                fresh_rotten_agree=sum(1 for x in lab if (x["cond"] == "fresh") == (x["label"] == "f")), fresh_rotten_n=len(lab),
                n_negatives=len(neg), negatives_graded=sum(1 for x in neg if x[graded_key]))
pct = lambda v: dict(p50=round(float(np.percentile(v, 50)), 1), p95=round(float(np.percentile(v, 95)), 1)) if v else None
out = dict(frozen=dict(verify=PV, occlusion=PO), n=len(rows), H0=summ("H0", "h0_graded", "wide"), H_final=summ("H", "h_graded", "verified"),
           outcomes=dict(collections.Counter(x["outcome"] for x in rows)), latency_ms={k: pct(v) for k, v in lat.items()}, rows=rows)
json.dump(out, open(f"{B}/e2e_h.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("H0", "H_final", "outcomes", "latency_ms")}, indent=0))
