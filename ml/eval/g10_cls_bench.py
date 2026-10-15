"""G10: inference-only comparison of an EXTERNAL close-up classifier (HF sharktide/fruitbot-expanded, Keras ResNet-50, 36 classes)
with the frozen H2 verifier (h2_mnv3s.onnx, sha256 20898d7c) on the Stage H DEV split H-val (agent-triaged: I = single whole item,
W = pile / bunch, N = cut / printed / unsupported negatives; /workspace/work/g9h/sheets/val_order.json + hval_triage.json).
H-val was used to pick H2's epoch, so H2 has a selection advantage on it. Labels are AGENT-verified, NOT human-verified: exploratory.
No training; H2 and its thresholds are only read.

Two-step because TensorFlow lives in a separate venv (g10/tfenv) so the cvenv stack is not disturbed:
  tfenv/bin/python ml/eval/g10_cls_bench.py --fruitbot-probs OUT_fb.json        # writes fruitbot softmax per image (2 preprocessings)
  cvenv/bin/python ml/eval/g10_cls_bench.py --report OUT_fb.json --out OUT.json  # H2 + tables
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HV = "/workspace/work/g9h"
TRIAGE = "/workspace/projects/9399e4e3-d6d0-4c6b-a760-12b4c7c9c514/files/g9/stageH/hval_triage.json"
FB_DIR = "/workspace/work/cv/g10/ext/fruitbot"
H2_ONNX = "/workspace/work/g9h/h2v2/h2_mnv3s.onnx"
NS = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
FB_MAP = {"apple": "apple", "banana": "banana", "mango": "mango", "orange": "citrus", "lemon": "lemon_lime", "tomato": "tomato",
          "potato": "potato", "cucumber": "cucumber", "carrot": "carrot", "capsicum": "capsicum", "bell pepper": "capsicum",
          "paprika": "capsicum", "pomegranate": "pomegranate"}  # every other fruitbot label = unsupported (a rejection)


def items():
    order = json.load(open(f"{HV}/sheets/val_order.json")); t = json.load(open(TRIAGE)); out = []
    for kind in ("I", "W", "N"):
        for k, lab in t[kind].items():
            out.append(dict(id=order[int(k)], kind=kind, label=lab, path=f"{HV}/hset/img/{order[int(k)]}.jpg"))
    return out


def fruitbot_probs(out):
    os.environ["TF_USE_LEGACY_KERAS"] = "1"  # the HF file is a Keras-2 h5; Keras 3 fails to rebuild its graph ("dense expects 1 input")
    import tensorflow as tf
    import tf_keras
    from PIL import Image
    cfg = json.load(open(f"{FB_DIR}/config.json")); m = tf_keras.models.load_model(f"{FB_DIR}/tf_model.h5", compile=False)
    S = cfg["input_shape"][0]; res = dict(labels=cfg["labels"], input=S, probs={}, ms=[])
    for it in items():
        im = np.asarray(Image.open(it["path"]).convert("RGB").resize((S, S), Image.BILINEAR), np.float32)[None]
        row = {}
        for pp, x in (("raw255", im), ("div255", im / 255.0), ("resnet50", tf_keras.applications.resnet50.preprocess_input(im.copy()))):
            t0 = time.perf_counter(); y = m.predict(x, verbose=0)[0]; res["ms"].append((time.perf_counter() - t0) * 1e3)
            y = np.asarray(y, np.float64)
            if y.min() < 0 or abs(y.sum() - 1) > 1e-3: y = np.exp(y - y.max()); y /= y.sum()  # logits -> softmax
            row[pp] = y.round(6).tolist()
        res["probs"][it["id"]] = row
    res["params_m"] = round(m.count_params() / 1e6, 2); res["n_outputs"] = int(m.output_shape[-1])
    res["note"] = "config.json lists %d labels but the h5 has %d outputs; indices >= %d have no published name (reported as idxN)" % (len(res["labels"]), res["n_outputs"], len(res["labels"]))
    json.dump(res, open(out, "w"))


def report(fb_json, out):
    import onnxruntime as ort
    from PIL import Image
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from camera_io import h2_input
    from verify import h2_decision, FROZEN_VERIFY
    fb = json.load(open(fb_json)); L = fb["labels"]
    s = ort.InferenceSession(H2_ONNX, providers=["CPUExecutionProvider"]); n = s.get_inputs()[0].name
    its = items(); rep = dict(split="H-val (Stage H DEV; agent-triaged, NOT human-verified)", n=len(its),
                             counts={k: sum(i["kind"] == k for i in its) for k in "IWN"}, h2={}, fruitbot={})
    h2rows, fbrows = [], {pp: [] for pp in ("raw255", "div255", "resnet50")}; lat = []; raw_hist = {}
    for it in its:
        rgb = np.asarray(Image.open(it["path"]).convert("RGB"))
        t0 = time.perf_counter(); p = s.run(None, {n: h2_input(rgb)})[0][0]; lat.append((time.perf_counter() - t0) * 1e3)
        p = np.exp(p - p.max()) / np.exp(p - p.max()).sum() if (p.min() < 0 or abs(p.sum() - 1) > 1e-3) else p
        d = h2_decision(p.tolist(), FROZEN_VERIFY)
        h2rows.append(dict(it, top1=NS[int(np.argmax(p[:12]))], unknown_p=float(p[12]), accept=d["accept"], acc_cls=NS[d["classId"]] if d["accept"] else None))
        for pp in fbrows:
            q = np.array(fb["probs"][it["id"]][pp]); k = int(q.argmax()); lab = L[k] if k < len(L) else f"idx{k}"
            fbrows[pp].append(dict(it, top1=FB_MAP.get(lab), raw=lab, p=float(q[k])))
            raw_hist.setdefault(pp, {}).setdefault(it["label"], {}); raw_hist[pp][it["label"]][lab] = raw_hist[pp][it["label"]].get(lab, 0) + 1

    def table(rows, accept_key):
        sup = [r for r in rows if r["kind"] in "IW" and r["label"] in NS]; neg = [r for r in rows if r["kind"] == "N"]
        per = {}
        for c in NS:
            rc = [r for r in sup if r["label"] == c]
            if rc: per[c] = dict(n=len(rc), top1_correct=sum(r["top1"] == c for r in rc))
        conf = {}
        for r in sup: conf.setdefault(r["label"], {}); conf[r["label"]][str(r["top1"])] = conf[r["label"]].get(str(r["top1"]), 0) + 1
        cls_ok = [per[c]["top1_correct"] / per[c]["n"] for c in per]
        t = dict(supported_n=len(sup), top1_correct=sum(r["top1"] == r["label"] for r in sup),
                 top1_acc=round(sum(r["top1"] == r["label"] for r in sup) / max(1, len(sup)), 4),
                 mean_per_class_top1=round(float(np.mean(cls_ok)), 4), per_class=per, confusion=conf,
                 negatives_n=len(neg), negatives_named_supported_top1=sum(r["top1"] in NS for r in neg))
        if accept_key:
            t.update(accepted_correct=sum(r["accept"] and r["acc_cls"] == r["label"] for r in sup),
                     accepted_wrong=sum(r["accept"] and r["acc_cls"] != r["label"] for r in sup),
                     negatives_accepted=sum(r["accept"] for r in neg))
        else:  # a 0.5 top-probability floor as the only possible rejection (the model has no unknown class)
            t.update(at_p050_correct=sum(r["top1"] == r["label"] and r["p"] >= 0.5 for r in sup),
                     at_p050_wrong=sum(r["top1"] != r["label"] and r["top1"] in NS and r["p"] >= 0.5 for r in sup),
                     at_p050_negatives_named=sum(r["top1"] in NS and r["p"] >= 0.5 for r in neg))
        return t
    rep["h2"] = table(h2rows, True); rep["h2"]["onnx_ms_p50"] = round(float(np.percentile(lat, 50)), 2); rep["h2"]["onnx_ms_p95"] = round(float(np.percentile(lat, 95)), 2)
    for pp, rows in fbrows.items(): rep["fruitbot"][pp] = table(rows, False)
    rep["fruitbot_keras_predict_ms_p50"] = round(float(np.percentile(fb["ms"], 50)), 1)
    rep["fruitbot_params_m"] = fb.get("params_m"); rep["fruitbot_n_outputs"] = fb.get("n_outputs"); rep["fruitbot_note"] = fb.get("note")
    rep["fruitbot_raw_argmax_by_true_label"] = raw_hist
    json.dump(rep, open(out, "w"), indent=1)
    print(json.dumps({"h2": {k: rep["h2"][k] for k in ("top1_acc", "mean_per_class_top1", "accepted_correct", "accepted_wrong", "negatives_accepted")},
                      **{f"fb_{pp}": {k: rep["fruitbot"][pp][k] for k in ("top1_acc", "mean_per_class_top1", "negatives_named_supported_top1")} for pp in rep["fruitbot"]}}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--fruitbot-probs"); ap.add_argument("--report"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.fruitbot_probs: fruitbot_probs(a.fruitbot_probs)
    if a.report: report(a.report, a.out)
