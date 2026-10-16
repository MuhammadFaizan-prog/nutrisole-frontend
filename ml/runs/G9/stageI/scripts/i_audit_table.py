"""Summarise h2_audit_raw.jsonl -> ml/runs/G9/stageI/out/h2_audit.json (post-hoc diagnostic; Stage H results untouched)."""
import json, sys, collections, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.verify import h2_decision, verify_identity, FROZEN_VERIFY, H2_CLASSES
O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; C = H2_CLASSES; N = C[:12]; P5 = ["apple", "banana", "citrus", "tomato", "carrot"]
R = [json.loads(l) for l in open(f"{O}/h2_audit_raw.jsonl")]
SUP = lambda r: r["group"] in ("item", "crowd") and r["truth"] in N
NEG = lambda r: r["group"] in ("unsupported", "printed", "cut")
A = dict()
st = np.array([r["stored"] for r in R]); on = np.array([r["onnx"] for r in R]); pt = np.array([r["pt"] for r in R])
A["reproduction"] = dict(n=len(R), max_abs_stored_vs_onnx=float(np.abs(st - on).max()), top1_agree_stored_onnx=int((st.argmax(1) == on.argmax(1)).sum()))
A["onnx_vs_pytorch"] = dict(max_abs_prob=float(np.abs(on - pt).max()), mean_abs_prob=float(np.abs(on - pt).mean()), top1_agree=int((on.argmax(1) == pt.argmax(1)).sum()), n=len(R))
lg = np.array([r["logits"] for r in R]); A["softmax_check"] = dict(onnx_rows_sum_to_1=float(np.abs(on.sum(1) - 1).max()), softmax_of_pt_logits_vs_onnx=float(np.abs(np.exp(lg) / np.exp(lg).sum(1, keepdims=True) - on).max()),
    note="ONNX graph ends in Softmax (Wrap module); verify.py/ts read index 12 as a probability. A sigmoid or second softmax would change rank only for double softmax; none is applied.")
def score(rows, var, P=FROZEN_VERIFY):
    c = collections.Counter()
    for r in rows:
        p = r[var]; d = h2_decision(p, P); top = int(np.argmax(p[:12])); top13 = int(np.argmax(p))
        if SUP(r):
            t = N.index(r["truth"]); c["sup"] += 1; c["top1_correct"] += top == t; c["top13_correct"] += top13 == t; c["top13_unknown"] += top13 == 12
            c["h2only_correct"] += d["accept"] and d["classId"] == t; c["h2only_wrong"] += d["accept"] and d["classId"] != t; c["h2only_abstain"] += not d["accept"]
            c["top2_has_truth"] += t in list(np.argsort(-np.array(p[:12]))[:2])
            w = dict(status="identified", classId=r["wide"]) if r["wide"] is not None else dict(status="unable")
            v = verify_identity(w, None, p, P); c["pa_correct"] += v["status"] == "verified" and v["classId"] == t; c["pa_wrong"] += v["status"] == "verified" and v["classId"] != t
            if r["truth"] in P5: c["p5_sup"] += 1; c["p5_top1"] += top == t; c["p5_h2only_correct"] += d["accept"] and d["classId"] == t
        elif NEG(r):
            c["neg"] += 1; c["neg_h2_accept"] += d["accept"]; c["neg_top13_unknown"] += top13 == 12
            w = dict(status="identified", classId=r["wide"]) if r["wide"] is not None else dict(status="unable")
            c["neg_pa_accept"] += verify_identity(w, None, p, P)["status"] == "verified"
    return dict(c)
ev = [r for r in R if r["split"] == "eval"]; tu = [r for r in R if r["split"] == "tune"]
A["variants_eval"] = {v: score(ev, v) for v in ("onnx", "pt", "pil", "bgr", "letterbox")}
A["variants_tune"] = {v: score(tu, v) for v in ("onnx", "pt", "pil", "bgr", "letterbox")}
A["by_set_eval_onnx"] = {s: score([r for r in ev if r["set"] == s], "onnx") for s in ("cu", "cuneg", "heval")}
A["by_set_tune_onnx"] = {s: score([r for r in tu if r["set"] == s], "onnx") for s in ("cu", "cuneg", "hval")}
A["by_roi_eval_onnx"] = {s: score([r for r in ev if r["roi"] == s], "onnx") for s in ("track", "tap_roi")}
A["by_group_eval_onnx"] = {s: score([r for r in ev if r["group"] == s], "onnx") for s in ("item", "crowd")}
# confusion on supported (eval and tune+eval), top over 13 incl unknown
def conf(rows, var="onnx"):
    M = collections.defaultdict(collections.Counter)
    for r in rows:
        if SUP(r): M[r["truth"]][C[int(np.argmax(r[var]))]] += 1
    return {k: dict(v.most_common()) for k, v in sorted(M.items())}
A["confusion_eval_top13"] = conf(ev); A["confusion_all_top13"] = conf(R)
A["predicted_class_histogram_all_supported"] = dict(collections.Counter(C[int(np.argmax(r["onnx"]))] for r in R if SUP(r)).most_common())
A["predicted_class_histogram_neg"] = dict(collections.Counter(C[int(np.argmax(r["onnx"]))] for r in R if NEG(r)).most_common())
# crop size buckets
def bucket(r): s = min(r["hw"]); return "<128" if s < 128 else "128-255" if s < 256 else "256-511" if s < 512 else ">=512"
A["by_crop_side_eval_onnx"] = {b: score([r for r in ev if bucket(r) == b], "onnx") for b in ("<128", "128-255", "256-511", ">=512")}
A["aspect"] = dict(median_long_over_short=float(np.median([max(r["hw"]) / min(r["hw"]) for r in R])), frac_gt_1_5=float(np.mean([max(r["hw"]) / min(r["hw"]) > 1.5 for r in R])))
# confidence calibration on supported eval: mean max prob for correct vs wrong top-1
cs = [(max(r["onnx"][:12]), int(np.argmax(r["onnx"][:12])) == N.index(r["truth"])) for r in ev if SUP(r)]
A["confidence_eval"] = dict(mean_top_p_correct=float(np.mean([p for p, k in cs if k])), mean_top_p_wrong=float(np.mean([p for p, k in cs if not k])),
                           n_wrong_top_p_ge_0_6=sum(1 for p, k in cs if not k and p >= 0.6), n_correct=sum(k for _, k in cs), n=len(cs))
json.dump(A, open(f"{O}/h2_audit.json", "w"), indent=1)
print(json.dumps({k: A[k] for k in ("reproduction", "onnx_vs_pytorch", "softmax_check")}, indent=0))
for k in ("variants_eval", "variants_tune", "by_set_eval_onnx", "by_roi_eval_onnx", "by_group_eval_onnx", "by_crop_side_eval_onnx"):
    print(k); [print("  ", n, v) for n, v in A[k].items()]
print("confusion eval", json.dumps(A["confusion_eval_top13"])); print("hist sup", A["predicted_class_histogram_all_supported"]); print("hist neg", A["predicted_class_histogram_neg"]); print(A["aspect"], A["confidence_eval"])
# crop-context variants (i_audit_ctx.py)
import os
if os.path.exists(f"{O}/h2_audit_ctx.jsonl"):
    X = {json.loads(l)["key"] + json.loads(l)["set"]: json.loads(l) for l in open(f"{O}/h2_audit_ctx.jsonl")}
    for r in R: x = X[r["key"] + r["set"]]; r["full"] = x["full"]; r["pad25"] = x["pad25"]; r["crop_area_frac"] = x["crop_area_frac"]; r["match"] = x["match"]
    ev = [r for r in R if r["split"] == "eval"]; tu = [r for r in R if r["split"] == "tune"]
    A["context_eval"] = {v: score(ev, v) for v in ("onnx", "pad25", "full")}; A["context_tune"] = {v: score(tu, v) for v in ("onnx", "pad25", "full")}
    A["context_eval_by_set"] = {s: {v: score([r for r in ev if r["set"] == s], v) for v in ("onnx", "pad25", "full")} for s in ("cu", "heval")}
    A["crop_area_frac_median_by_roi"] = {s: float(np.median([r["crop_area_frac"] for r in R if r["roi"] == s])) for s in ("track", "tap_roi")}
    A["template_match_min"] = float(min(r["match"] for r in R))
    json.dump(A, open(f"{O}/h2_audit.json", "w"), indent=1)
    for k in ("context_eval", "context_tune", "context_eval_by_set"): print(k, json.dumps(A[k]))
    print(A["crop_area_frac_median_by_roi"], A["template_match_min"])
