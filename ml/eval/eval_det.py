"""Detector evaluation on locked test splits + robustness sweep.

  python ml/eval/eval_det.py --model .../best.pt --out ml/runs/G1/eval_det_yolo26n --imgsz 320 [--robust]
Writes eval_det.json: mAP50, mAP50-95, per-class P/R/mAP50/mAP50-95 with instance counts,
for split 'test' (LVIS domain) and 'test_rf' (180 manually labelled photos), plus the
robustness sweep (each corruption applied to every test image; same labels).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import shutil
import sys

import cv2
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corruptions import CORRUPTIONS  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_val(model, data_yaml, split, imgsz, out, name, e2e=False):
    kw = dict(nms=False) if e2e else {}  # nms=False -> NMS-free one2one head (what the e2e ONNX runs)
    r = model.val(**kw, data=data_yaml, split=split, imgsz=imgsz, batch=16, device="cpu", conf=0.001, iou=0.7, plots=True,
                  project=out, name=name, exist_ok=True, verbose=False)
    names = r.names
    per = {}
    nt = getattr(r, "nt_per_class", None)
    for i, c in enumerate(r.ap_class_index):
        p, rc, ap50, ap = r.box.class_result(i)
        per[names[int(c)]] = dict(P=round(float(p), 4), R=round(float(rc), 4), mAP50=round(float(ap50), 4), mAP50_95=round(float(ap), 4),
                                  instances=int(nt[int(c)]) if nt is not None else None)
    return dict(split=split, imgsz=imgsz, mAP50=round(float(r.box.map50), 4), mAP50_95=round(float(r.box.map), 4),
                P=round(float(r.box.mp), 4), R=round(float(r.box.mr), 4), per_class=per,
                speed_ms=dict(r.speed), save_dir=str(r.save_dir))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", default=os.path.join(REPO, "ml/configs/det_v1.yaml"))
    ap.add_argument("--imgsz", type=int, nargs="+", default=[320])
    ap.add_argument("--out", required=True)
    ap.add_argument("--robust", action="store_true")
    ap.add_argument("--splits", nargs="+", default=["test", "test_rf"])
    ap.add_argument("--e2e", action="store_true", help="evaluate the NMS-free one2one head (YOLO26) instead of one2many+NMS")
    a = ap.parse_args()
    from ultralytics import YOLO
    os.makedirs(a.out, exist_ok=True)
    cfg = yaml.safe_load(open(a.data))
    root = cfg["path"]
    # temp yaml exposing test_rf as a split
    tmp_yaml = os.path.join(a.out, "_data.yaml")
    c2 = dict(cfg)
    if not (isinstance(cfg.get("test_rf"), str) and os.path.isabs(cfg["test_rf"])):  # det-v3 yamls give absolute split lists
        c2["test_rf"] = os.path.join(root, "images/test_rf")  # Ultralytics resolves only train/val/test against `path`
    yaml.safe_dump(c2, open(tmp_yaml, "w"))
    model = YOLO(a.model)
    rep = dict(model=a.model, device="cpu", head="one2one (NMS-free, nms=False)" if a.e2e else "default (one2many + NMS iou 0.7)", results=[])
    for sz in a.imgsz:
        for sp in a.splits:
            rep["results"].append(run_val(model, tmp_yaml, sp, sz, a.out, f"{sp}_{sz}", a.e2e))
            print(sp, sz, rep["results"][-1]["mAP50"], rep["results"][-1]["mAP50_95"], flush=True)
    if a.robust:
        rob = {}
        sz = a.imgsz[0]
        for cname, fn in CORRUPTIONS.items():
            d = f"/tmp/nutrisole_rob/{cname}"
            shutil.rmtree(d, ignore_errors=True)
            os.makedirs(f"{d}/images/test", exist_ok=True)
            os.makedirs(f"{d}/labels/test", exist_ok=True)
            for ip in glob.glob(f"{root}/images/test/*.jpg"):
                cv2.imwrite(f"{d}/images/test/{os.path.basename(ip)}", fn(cv2.imread(ip)), [cv2.IMWRITE_JPEG_QUALITY, 95])
                lp = ip.replace("/images/", "/labels/").replace(".jpg", ".txt")
                shutil.copyfile(lp, f"{d}/labels/test/{os.path.basename(lp)}")
            y = dict(path=d, train="images/test", val="images/test", test="images/test", names=cfg["names"])
            yp = f"{d}/data.yaml"
            yaml.safe_dump(y, open(yp, "w"))
            r = run_val(model, yp, "test", sz, a.out, f"rob_{cname}", a.e2e)
            rob[cname] = dict(mAP50=r["mAP50"], mAP50_95=r["mAP50_95"])
            print("robust", cname, r["mAP50"], flush=True)
        rep["robustness"] = rob
    json.dump(rep, open(f"{a.out}/eval_det.json", "w"), indent=1)


if __name__ == "__main__":
    main()
