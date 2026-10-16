"""G10b Phase 1 (detection) + Phase 2 (complementarity), analysis only, from the cached predictions of g10b_cache.py (no model is re-run here).
DEV/VAL only: det_v3 val (402 = 295 LVIS/HF-val + 57 OIV7 + 50 neg) and negdev (110 no-produce = 50 det_v3 neg val + 60 G3 devneg).
Labels: det_v3 dataset / agent-curated (EXPLORATORY, 0 human-verified). LVIS is federated: 'background FP' on LVIS images includes
unlabelled real produce, so FPs are overstated there.

Operating point = rubric detectorMinScore 0.35 (as g10_guard_whatif.py), single-label NMS 0.7, scene_guard maxSameClass 0.
Matching: greedy by score, class-aware IoU >= 0.5. Unmatched predictions are split into
  duplicate  (IoU >= 0.5 with an already-matched GT of the same class),
  wrong-class (IoU >= 0.5 with a supported GT of ANOTHER class),
  unsupported (IoU >= 0.5 with an ORIGINAL LVIS annotation of one of the 49 dropped, unsupported produce classes; g1data/lvis/labels),
  background (everything else).
mAP uses the same functions as g10_ext_bench.py (BaseValidator.match_predictions + ap_per_class).
Fusion (Phase 2, the one documented deployable method): class-wise Weighted Boxes Fusion (Solovyev et al. 2021; ZFTurbo conf_type='avg')
over the 9 classes BOTH models predict, iou_thr 0.55, weights 1:1, inputs conf >= 0.01; for a cluster with T boxes the score is
mean(score) * min(T, 2) / 2. Classes only G3 predicts (mango, guava, pomegranate) pass through unchanged. The 49 unsupported v8m classes are dropped.
Sensitivity row (not the proposed method): union + class-wise NMS 0.7.
  python g10b_analyze.py OUT.json
"""
import json, os, pickle, sys, collections
import numpy as np, torch
sys.path.insert(0, "/workspace/work/nutrisole/ml/eval")
from size_buckets import gt_of  # noqa
from g10_ext_bench import NS, MAPS, match, box_iou  # noqa
from scene_guard import scene_guard  # noqa
from ultralytics.utils.metrics import ap_per_class
C = "/workspace/work/cv/g10b/cache"; G = "/workspace/work/cv/g10"
VAL = [l.strip() for l in open(f"{G}/val.txt") if l.strip()]; NEG = [l.strip() for l in open(f"{G}/negdev.txt") if l.strip()]
OIV = set(l.strip() for l in open(f"{G}/val_oiv7.txt") if l.strip()); LVIS = set(l.strip() for l in open(f"{G}/val_lvis.txt") if l.strip())
G3 = pickle.load(open(f"{C}/g3_480.pkl", "rb")); V8 = pickle.load(open(f"{C}/v8m_640.pkl", "rb"))
LV_NAMES = [l.split(":", 1)[1].strip() for l in open("/workspace/work/cv/g1data/lvis/data.yaml") if l.strip()[:1].isdigit() and ":" in l]
LMAP = MAPS["lvis63"]; SUP_LVIS = {i for i, n in enumerate(LV_NAMES) if n in LMAP}
GUARDS = [0.0, 0.0025, 0.005, 0.01]; TH = 0.35; SHARED = sorted(set(LMAP.values()))
AREA_BINS = [0, 0.001, 0.0025, 0.005, 0.01, 0.02, 0.05, 1.01]; SIDE_BINS = [0, 6, 12, 24, 48, 96, 1e9]

def g3_preds(f):
    p = G3["preds"][f]; return p["xyxy"], p["conf"], p["cls"].astype(int), p["W"], p["H"]
def v8_preds(f, keep_unsup=False):
    p = V8["preds"][f]; nm = [V8["names"][int(c)] for c in p["cls"]]
    k = np.array([n in LMAP for n in nm], bool) if len(nm) else np.zeros(0, bool)
    cl = np.array([LMAP[n] for n, kk in zip(nm, k) if kk], int)
    return p["xyxy"][k], p["conf"][k], cl, p["W"], p["H"]
def unsup_gt(f, W, H):
    lp = f"/workspace/work/cv/g1data/lvis/labels/val/{os.path.basename(f).rsplit('.', 1)[0]}.txt"; out = []
    if f in LVIS and os.path.exists(lp):
        for l in open(lp):
            v = l.split()
            if len(v) == 5 and int(v[0]) not in SUP_LVIS:
                x, y, w, h = map(float, v[1:]); out.append((LV_NAMES[int(v[0])], [(x - w / 2) * W, (y - h / 2) * H, (x + w / 2) * W, (y + h / 2) * H]))
    return out

def apply_guard(bx, sc, cl, W, H, g):
    D = [dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], score=float(s), classId=int(c), i=i) for i, (b, s, c) in enumerate(zip(bx, sc, cl))]
    idx = np.array([d["i"] for d in scene_guard(D, maxSameClass=0, minAreaFrac=g)], int)
    return bx[idx] if len(idx) else bx[:0], sc[idx] if len(idx) else sc[:0], cl[idx] if len(idx) else cl[:0]

def wbf(lists, iou_thr=0.55, nmod=2):
    """lists: [(bx, sc, cl)] per model (pixel xyxy). Class-wise WBF; returns fused bx, sc, cl."""
    ob, os_, oc = [], [], []
    allc = set(int(c) for _, _, cl in lists for c in cl)
    for c in allc:
        B = [(b, s, m) for m, (bx, sc, cl) in enumerate(lists) for b, s, k in zip(bx, sc, cl) if k == c]
        B.sort(key=lambda t: -t[1]); clusters = []; fused = []
        for b, s, m in B:
            if fused:
                fb = np.array([f[0] for f in fused]); io = box_iou(np.array([b]), fb)[0]; j = int(io.argmax())
                if io[j] > iou_thr:
                    clusters[j].append((b, s, m)); bb = np.array([x[0] for x in clusters[j]]); ss = np.array([x[1] for x in clusters[j]])
                    fused[j] = ((bb * ss[:, None]).sum(0) / ss.sum(), ss); continue
            clusters.append([(b, s, m)]); fused.append((np.array(b, float), np.array([s])))
        for (fb, ss), cl_ in zip(fused, clusters):
            if c not in SHARED: score = float(ss.max())
            else: score = float(ss.mean()) * min(len(ss), nmod) / nmod
            ob.append(fb); os_.append(score); oc.append(c)
    if not ob: return np.zeros((0, 4)), np.zeros(0), np.zeros(0, int)
    return np.array(ob), np.array(os_), np.array(oc, int)

def union_nms(lists, iou=0.7):
    bx = np.concatenate([l[0] for l in lists]); sc = np.concatenate([l[1] for l in lists]); cl = np.concatenate([l[2] for l in lists])
    keep = []
    for i in np.argsort(-sc):
        if any(cl[j] == cl[i] and box_iou(bx[i:i + 1], bx[j:j + 1])[0, 0] > iou for j in keep): continue
        keep.append(i)
    keep = np.array(keep, int); return bx[keep], sc[keep], cl[keep]

def model_preds(name, f, conf_min=0.0):
    if name == "G3": r = g3_preds(f)
    elif name == "v8m": r = v8_preds(f)
    else:
        a, b = g3_preds(f), v8_preds(f); W, H = a[3], a[4]
        la = [(x[0][x[1] >= 0.01], x[1][x[1] >= 0.01], x[2][x[1] >= 0.01]) for x in (a, b)]
        bx, sc, cl = wbf(la) if name == "WBF" else union_nms(la)
        r = (bx, sc, cl, W, H)
    bx, sc, cl, W, H = r; k = sc >= conf_min; return bx[k], sc[k], cl[k], W, H

def op_eval(name, files, g, neg=False, detail=False):
    """Operating point 0.35 + guard g. Returns counts, per-class and the list of matched GT ids + FP records."""
    m = collections.Counter(); pc = collections.defaultdict(collections.Counter); hits = set(); fps = []; tps = []
    for f in files:
        bx, sc, cl, W, H = model_preds(name, f, TH); bx, sc, cl = apply_guard(bx, sc, cl, W, H, g)
        if neg:
            m["imgs"] += 1; m["imgs_with_box"] += len(sc) > 0; m["boxes"] += len(sc)
            for c in cl: pc[NS[c]]["neg_boxes"] += 1
            for b, s, c in zip(bx, sc, cl): fps.append(dict(f=f, kind="negative_image", cls=int(c), area=float((b[2] - b[0]) * (b[3] - b[1]) / (W * H)), side480=float(min(b[2] - b[0], b[3] - b[1]) * 480 / max(W, H)), sidefull=float(np.sqrt((b[2] - b[0]) * (b[3] - b[1])))))
            continue
        gt = gt_of(f, W, H); tc = np.array([x[0] for x in gt], int); tb = np.array([x[1] for x in gt]).reshape(-1, 4); ug = unsup_gt(f, W, H)
        ub = np.array([u[1] for u in ug]).reshape(-1, 4); used = set(); m["gt"] += len(gt)
        for c in tc: pc[NS[c]]["gt"] += 1
        io = box_iou(bx, tb) if len(gt) and len(bx) else np.zeros((len(bx), len(gt)))
        iu = box_iou(bx, ub) if len(ug) and len(bx) else np.zeros((len(bx), len(ug)))
        for i in np.argsort(-sc):
            best, bi = 0.5, -1
            for gi in range(len(gt)):
                if gi in used or tc[gi] != cl[i]: continue
                if io[i, gi] >= best: best, bi = io[i, gi], gi
            b = bx[i]; rec = dict(f=f, cls=int(cl[i]), score=float(sc[i]), area=float((b[2] - b[0]) * (b[3] - b[1]) / (W * H)),
                                 side480=float(min(b[2] - b[0], b[3] - b[1]) * 480 / max(W, H)), sidefull=float(np.sqrt((b[2] - b[0]) * (b[3] - b[1]))), dom="oiv7" if f in OIV else "lvis" if f in LVIS else "neg")
            if bi >= 0:
                used.add(bi); m["tp"] += 1; pc[NS[cl[i]]]["tp"] += 1; hits.add((f, bi)); rec.update(kind="tp", gt=bi); tps.append(rec); continue
            same_dup = any(io[i, gi] >= 0.5 and tc[gi] == cl[i] for gi in range(len(gt)))
            other = [gi for gi in range(len(gt)) if io[i, gi] >= 0.5 and tc[gi] != cl[i]]
            if same_dup: k = "duplicate"
            elif other: k = "wrong_class"; rec["true"] = NS[tc[other[int(np.argmax(io[i, other]))]]]
            elif len(ug) and iu[i].max() >= 0.5: k = "unsupported"; rec["true"] = ug[int(iu[i].argmax())][0]
            else: k = "background"
            m["fp"] += 1; m[k] += 1; pc[NS[cl[i]]]["fp"] += 1; pc[NS[cl[i]]][k] += 1; rec["kind"] = k; fps.append(rec)
    out = dict(counts=dict(m), per_class={k: dict(v) for k, v in pc.items()})
    if not neg: out["recall"] = round(m["tp"] / max(1, m["gt"]), 4); out["precision"] = round(m["tp"] / max(1, m["tp"] + m["fp"]), 4)
    else: out["neg_image_rate"] = round(m["imgs_with_box"] / max(1, m["imgs"]), 4)
    return out, hits, fps, tps

def hist(vals, bins): return [int(((np.array(vals) >= lo) & (np.array(vals) < hi)).sum()) if vals else 0 for lo, hi in zip(bins[:-1], bins[1:])]

def map_eval(name, files):
    st = dict(tp=[], conf=[], pred_cls=[], target_cls=[])
    for f in files:
        bx, sc, cl, W, H = model_preds(name, f); gt = gt_of(f, W, H)
        tc = np.array([g[0] for g in gt], int); tb = np.array([g[1] for g in gt]).reshape(-1, 4); iou = box_iou(tb, bx)
        st["tp"].append(match(cl, tc, iou) if len(cl) else np.zeros((0, 10), bool)); st["conf"].append(sc); st["pred_cls"].append(cl); st["target_cls"].append(tc)
    cat = {k: np.concatenate(v, 0) for k, v in st.items()}
    r = ap_per_class(cat["tp"], cat["conf"], cat["pred_cls"], cat["target_cls"], plot=False, names={i: n for i, n in enumerate(NS)})
    ap_, unique = r[5], r[6]
    return dict(mAP50=round(float(ap_[:, 0].mean()), 4), mAP50_95=round(float(ap_.mean()), 4),
                per_class_AP50={NS[int(c)]: round(float(ap_[j, 0]), 4) for j, c in enumerate(unique)},
                mAP50_shared9=round(float(np.mean([ap_[j, 0] for j, c in enumerate(unique) if int(c) in SHARED])), 4))

if __name__ == "__main__":
    out = dict(label_status="det_v3 dataset / agent-curated labels; EXPLORATORY; 0 human-verified", score=TH, maxSameClass=0,
               names_check=dict(v8m_names_equal_lvis_yaml=[V8["names"][i] for i in range(len(V8["names"]))] == LV_NAMES, n_v8m=len(V8["names"]),
                                mapped={n: NS[i] for n, i in LMAP.items()}, unsupported_lvis_classes=[n for n in LV_NAMES if n not in LMAP]))
    POS = [f for f in VAL if f in LVIS or f in OIV]; NEGALL = sorted(set(NEG) | (set(VAL) - set(POS)))
    # ---------------- Phase 1: guard sweep, G3 only ----------------
    P1 = {}; base_hits = None; per_g = {}
    for g in GUARDS:
        r, hits, fps, tps = op_eval("G3", VAL, g); rn, _, nfp, _ = op_eval("G3", NEG, g, neg=True); per_g[g] = (r, hits, fps, tps, rn, nfp)
    b = per_g[0.01]
    for g in GUARDS:
        r, hits, fps, tps, rn, nfp = per_g[g]
        rec_ = [t for t in tps if (t["f"], t["gt"]) not in b[1]]; newfp = [x for x in fps if x["area"] < 0.01]; newneg = [x for x in nfp if x["area"] < 0.01]
        dom = {d: dict(tp=sum(1 for t in tps if t["dom"] == d), fp=sum(1 for x in fps if x["dom"] == d)) for d in ("lvis", "oiv7", "neg")}
        P1[str(g)] = dict(val=r, negdev=rn, by_domain=dom,
            vs_1pct=dict(tp_recovered=len(rec_), tp_lost=len(b[1] - hits), fp_added=r["counts"].get("fp", 0) - b[0]["counts"].get("fp", 0),
                         fp_added_by_kind={k: r["counts"].get(k, 0) - b[0]["counts"].get(k, 0) for k in ("background", "wrong_class", "duplicate", "unsupported")},
                         neg_boxes_added=rn["counts"].get("boxes", 0) - b[4]["counts"].get("boxes", 0), neg_imgs_added=rn["counts"].get("imgs_with_box", 0) - b[4]["counts"].get("imgs_with_box", 0),
                         recovered_per_class=dict(collections.Counter(NS[t["cls"]] for t in rec_)),
                         added_fp_per_class=dict(collections.Counter(NS[x["cls"]] + ":" + x["kind"] for x in newfp)),
                         recovered_by_domain=dict(collections.Counter(t["dom"] for t in rec_)), added_fp_by_domain=dict(collections.Counter(x["dom"] for x in newfp)),
                         recovered_area_hist=hist([t["area"] for t in rec_], AREA_BINS), added_fp_area_hist=hist([x["area"] for x in newfp], AREA_BINS),
                         recovered_side480_hist=hist([t["side480"] for t in rec_], SIDE_BINS), added_fp_side480_hist=hist([x["side480"] for x in newfp], SIDE_BINS),
                         recovered_sidefull_ge96=sum(t["sidefull"] >= 96 for t in rec_), recovered_sidefull_median=round(float(np.median([t["sidefull"] for t in rec_])), 1) if rec_ else None,
                         recovered_score_median=round(float(np.median([t["score"] for t in rec_])), 3) if rec_ else None, added_fp_score_median=round(float(np.median([x["score"] for x in newfp])), 3) if newfp else None,
                         recovered_score_ge05=sum(t["score"] >= 0.5 for t in rec_), added_fp_score_ge05=sum(x["score"] >= 0.5 for x in newfp),
                         wrong_class_pairs=dict(collections.Counter(f"{NS[x['cls']]}<-{x['true']}" for x in newfp if x["kind"] == "wrong_class")),
                         unsupported_pairs=dict(collections.Counter(f"{NS[x['cls']]}<-{x['true']}" for x in newfp if x["kind"] == "unsupported")),
                         neg_added_per_class=dict(collections.Counter(NS[x["cls"]] for x in newneg))))
    out["area_bins"] = AREA_BINS; out["side_bins_480"] = SIDE_BINS; out["phase1_guard"] = P1
    # all-GT size distribution (what share of GT each guard can reach at all)
    allgt = []
    for f in VAL:
        W, H = G3["preds"][f]["W"], G3["preds"][f]["H"]
        for c, bb in gt_of(f, W, H): allgt.append(((bb[2] - bb[0]) * (bb[3] - bb[1]) / (W * H), c))
    out["gt_area_hist"] = hist([a for a, _ in allgt], AREA_BINS); out["gt_below"] = {str(g): round(sum(a < g for a, _ in allgt) / len(allgt), 4) for g in GUARDS}
    out["gt_below_per_class_1pct"] = {NS[c]: round(sum(1 for a, cc in allgt if cc == c and a < 0.01) / max(1, sum(1 for a, cc in allgt if cc == c)), 3) for c in range(12) if any(cc == c for _, cc in allgt)}
    # ---------------- Phase 2: complementarity ----------------
    P2 = {}
    for name in ("G3", "v8m", "WBF", "UNION_NMS"):
        e = dict(mAP_val=map_eval(name, VAL), mAP_lvis=map_eval(name, [f for f in VAL if f in LVIS]), mAP_oiv7=map_eval(name, [f for f in VAL if f in OIV]))
        for g in (0.01, 0.0):
            r, hits, fps, tps = op_eval(name, VAL, g); rn, _, _, _ = op_eval(name, NEG, g, neg=True)
            e[f"op_guard_{g}"] = dict(val=r, negdev=rn, by_domain={d: dict(tp=sum(1 for t in tps if t["dom"] == d), fp=sum(1 for x in fps if x["dom"] == d)) for d in ("lvis", "oiv7", "neg")},
                                       wrong_class_pairs=dict(collections.Counter(f"{NS[x['cls']]}<-{x['true']}" for x in fps if x["kind"] == "wrong_class").most_common(8)))
            e[f"_hits_{g}"] = hits
        P2[name] = e
    for g in (0.01, 0.0):
        hg, hv = P2["G3"][f"_hits_{g}"], P2["v8m"][f"_hits_{g}"]; ngt = P2["G3"][f"op_guard_{g}"]["val"]["counts"]["gt"]
        only_v = hv - hg; only_g = hg - hv
        def cls_of(s):
            c = collections.Counter()
            for f, gi in s:
                W, H = G3["preds"][f]["W"], G3["preds"][f]["H"]; c[NS[gt_of(f, W, H)[gi][0]]] += 1
            return dict(c)
        P2[f"oracle_guard_{g}"] = dict(note="UPPER BOUND, not deployable: a GT counts if EITHER model hits it at 0.35 (class-aware IoU 0.5); FPs of both ignored",
            g3_tp=len(hg), v8m_tp=len(hv), both=len(hg & hv), v8m_only=len(only_v), g3_only=len(only_g), oracle_tp=len(hg | hv), gt=ngt,
            g3_recall=round(len(hg) / ngt, 4), oracle_recall=round(len(hg | hv) / ngt, 4),
            v8m_only_per_class=cls_of(only_v), g3_only_per_class=cls_of(only_g),
            v8m_only_by_domain=dict(collections.Counter("oiv7" if f in OIV else "lvis" for f, _ in only_v)), g3_only_by_domain=dict(collections.Counter("oiv7" if f in OIV else "lvis" for f, _ in only_g)))
    for name in P2:
        if isinstance(P2[name], dict):
            for k in [k for k in P2[name] if k.startswith("_hits")]: del P2[name][k]
    out["phase2"] = P2
    json.dump(out, open(sys.argv[1], "w"), indent=1); print("wrote", sys.argv[1])
