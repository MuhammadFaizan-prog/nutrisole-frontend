"""G7 (GPT review item 1): bootstrap 95% CIs for detector mAP over INDEPENDENT units.

Step 1 (collect): run the same Ultralytics val as ml/eval/eval_det.py (CPU, imgsz 480, conf 0.001, iou 0.7) and capture the
per-image matching stats (tp at 10 IoU thresholds, conf, pred_cls, target_cls) via DetMetrics.update_stats.
  python ml/eval/bootstrap_det.py collect --model best.pt --tag G3 --out /workspace/work/cv/g7models/boot
Step 2 (ci): percentile bootstrap (B=1000, seed 0) of mAP50 / mAP50-95 per split and pooled, and the PAIRED difference
(candidate - reference) on identical resamples.
  python ml/eval/bootstrap_det.py ci --ref G3 --cands G7sA G7sB --stats /workspace/work/cv/g7models/boot --out ml/runs/G7/bootstrap_det.json
Units: test / test_oiv7 / test_oiv7c images are independent web photos -> resample images; test_rf is resampled by its
capture UUID (file name <date>_<uuid>_<n>_png.rf.*; 22 UUIDs); pooled (n=829) = stratified resample of those units.
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys

import numpy as np

SPLITS = {"test": "/workspace/work/cv/g4data/det_v4_eval.yaml", "test_rf": "/workspace/work/cv/g4data/det_v4_eval.yaml",
          "test_oiv7": "/workspace/work/cv/g4data/det_v4_eval.yaml", "test_oiv7c": "/workspace/work/cv/g4data/det_v4_eval.yaml",
          "pooled": "/workspace/work/cv/g3data/det_v3/det_v3_pooled.yaml"}


def unit_of(im_name: str) -> tuple[str, str]:
    b = os.path.basename(im_name)
    if "/test_rf/" in im_name or ".rf." in b:
        parts = b.split("_")
        return ("test_rf", parts[1] if len(parts) > 1 else b)
    if "/test_oiv7c/" in im_name:
        return ("test_oiv7c", b)
    if "/test_oiv7/" in im_name:
        return ("test_oiv7", b)
    return ("test", b)


def collect(model_path, tag, out, imgsz=480):
    from ultralytics import YOLO
    from ultralytics.utils import metrics as M
    rec = []
    orig = M.DetMetrics.update_stats

    def patched(self, stat):
        rec.append({k: np.array(stat[k]).copy() for k in ("tp", "conf", "pred_cls", "target_cls")} | {"im_name": str(stat["im_name"])})
        return orig(self, stat)
    M.DetMetrics.update_stats = patched
    model = YOLO(model_path)
    res = {}
    for sp, y in SPLITS.items():
        rec.clear()
        r = model.val(data=y, split=sp, imgsz=imgsz, batch=16, device="cpu", conf=0.001, iou=0.7, plots=False, verbose=False,
                      project="/tmp/boot_val", name=f"{tag}_{sp}", exist_ok=True)
        res[sp] = dict(official_mAP50=float(r.box.map50), official_mAP50_95=float(r.box.map), images=list(rec))
        print(tag, sp, len(rec), round(float(r.box.map50), 4), flush=True)
    os.makedirs(out, exist_ok=True)
    pickle.dump(res, open(os.path.join(out, f"stats_{tag}.pkl"), "wb"))


def map_of(imgs):
    from ultralytics.utils.metrics import ap_per_class
    if not imgs:
        return float("nan"), float("nan")
    tp = np.concatenate([i["tp"].reshape(-1, 10) for i in imgs]); conf = np.concatenate([i["conf"].reshape(-1) for i in imgs])
    pc = np.concatenate([i["pred_cls"].reshape(-1) for i in imgs]); tc = np.concatenate([i["target_cls"].reshape(-1) for i in imgs])
    if tc.size == 0:
        return float("nan"), float("nan")
    out = ap_per_class(tp, conf, pc, tc, plot=False)
    ap = out[5]
    return float(ap[:, 0].mean()), float(ap.mean())


def ci(ref, cands, stats_dir, out, B=1000, seed=0):
    S = {t: pickle.load(open(os.path.join(stats_dir, f"stats_{t}.pkl"), "rb")) for t in [ref] + cands}
    res = dict(method="percentile bootstrap, B=%d, seed %d; units: images (test, test_oiv7, test_oiv7c), capture UUID (test_rf); pooled stratified" % (B, seed),
               device="sandbox CPU (PyTorch val, imgsz 480, conf 0.001, iou 0.7)", ref=ref, splits={})
    for sp in SPLITS:
        if any(sp not in S[t] for t in S):
            continue
        # units are defined on the reference's image list (identical file lists for every model)
        names = [i["im_name"] for i in S[ref][sp]["images"]]
        idx = {t: {i["im_name"]: i for i in S[t][sp]["images"]} for t in S}
        units = {}
        for n in names:
            st, u = unit_of(n)
            units.setdefault(st, {}).setdefault(u, []).append(n)
        strata = {st: list(v.values()) for st, v in units.items()}
        rng = np.random.default_rng(seed)
        boots = {t: [] for t in S}
        for _ in range(B):
            pick = []
            for st, groups in strata.items():
                k = rng.integers(0, len(groups), len(groups))
                for j in k:
                    pick.extend(groups[j])
            for t in S:
                boots[t].append(map_of([idx[t][n] for n in pick]))
        row = dict(n_images=len(names), units={st: len(g) for st, g in strata.items()}, models={})
        for t in S:
            pt = map_of([idx[t][n] for n in names]); b = np.array(boots[t])
            row["models"][t] = dict(official_mAP50=round(S[t][sp]["official_mAP50"], 4), mAP50=round(pt[0], 4), mAP50_95=round(pt[1], 4),
                                    mAP50_ci95=[round(float(np.nanpercentile(b[:, 0], 2.5)), 4), round(float(np.nanpercentile(b[:, 0], 97.5)), 4)],
                                    mAP50_95_ci95=[round(float(np.nanpercentile(b[:, 1], 2.5)), 4), round(float(np.nanpercentile(b[:, 1], 97.5)), 4)])
            if t != ref:
                d = b[:, 0] - np.array(boots[ref])[:, 0]
                row["models"][t]["diff_vs_ref_mAP50"] = dict(point=round(pt[0] - map_of([idx[ref][n] for n in names])[0], 4),
                                                             ci95=[round(float(np.nanpercentile(d, 2.5)), 4), round(float(np.nanpercentile(d, 97.5)), 4)],
                                                             p_le_0=round(float(np.mean(d <= 0)), 4))
        res["splits"][sp] = row
        print(sp, json.dumps(row["models"])[:400], flush=True)
        json.dump(res, open(out, "w"), indent=1)
    json.dump(res, open(out, "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "ci"])
    ap.add_argument("--model"); ap.add_argument("--tag"); ap.add_argument("--out"); ap.add_argument("--ref"); ap.add_argument("--cands", nargs="*", default=[])
    ap.add_argument("--stats", default="/workspace/work/cv/g7models/boot"); ap.add_argument("-B", type=int, default=1000)
    a = ap.parse_args()
    if a.cmd == "collect":
        collect(a.model, a.tag, a.out)
    else:
        ci(a.ref, a.cands, a.stats, a.out, B=a.B)
