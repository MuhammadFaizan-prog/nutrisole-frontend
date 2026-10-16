"""G10b: wall time of the fusion step alone (class-wise WBF in g10b_analyze.py, pure Python/NumPy, not optimised) on cached predictions,
at the deployable input (both models' boxes >= 0.35, i.e. what an app would fuse) and at the mAP input (>= 0.01). Sandbox CPU.
  python g10b_fusion_time.py OUT.json"""
import sys, time, json, numpy as np
sys.argv, out = sys.argv[:1] + ["/dev/null"], sys.argv[1]
import g10b_analyze as A
r = {}
for th in (0.35, 0.01):
    ts = []
    for f in A.VAL[:200]:
        a, b = A.g3_preds(f), A.v8_preds(f); la = [(x[0][x[1] >= th], x[1][x[1] >= th], x[2][x[1] >= th]) for x in (a, b)]
        t0 = time.perf_counter(); A.wbf(la); ts.append((time.perf_counter() - t0) * 1e3)
    r[f"wbf_input_ge_{th}"] = dict(p50_ms=round(float(np.percentile(ts, 50)), 2), p95_ms=round(float(np.percentile(ts, 95)), 2), n=len(ts))
json.dump(r, open(out, "w"), indent=1); print(r)
