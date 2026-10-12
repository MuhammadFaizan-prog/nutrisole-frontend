"""Export champion candidates and write the model manifest (rule 8.12).

  python ml/export/export_models.py --det runs/.../best.pt:e2e:320 --cls runs/.../best.pt:192:<T> --out ml/models/G1
Formats tried for each model: onnx (static square input), executorch (.pte), litert (.tflite).
A format that fails is recorded with its error instead of aborting.
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil
import time
import traceback


def sha(p):
    h = hashlib.sha256()
    if os.path.isdir(p):
        for f in sorted(glob.glob(f"{p}/**/*", recursive=True)):
            if os.path.isfile(f):
                h.update(open(f, "rb").read())
    else:
        h.update(open(p, "rb").read())
    return h.hexdigest()


def size(p):
    if os.path.isdir(p):
        return sum(os.path.getsize(f) for f in glob.glob(f"{p}/**/*", recursive=True) if os.path.isfile(f))
    return os.path.getsize(p)


def onnx_io(p):
    import onnx
    m = onnx.load(p)
    f = lambda v: dict(name=v.name, shape=[d.dim_value or d.dim_param for d in v.type.tensor_type.shape.dim], dtype=onnx.TensorProto.DataType.Name(v.type.tensor_type.elem_type))
    return dict(inputs=[f(i) for i in m.graph.input], outputs=[f(o) for o in m.graph.output], opset=m.opset_import[0].version)


def export_one(pt, imgsz, out_dir, tag, kind=None):
    from ultralytics import YOLO
    res = {}
    for fmt in ["onnx", "executorch", "litert"]:
        t0 = time.time()
        if kind == "e2e" and fmt != "onnx":
            res[fmt] = dict(status="skipped", reason="Ultralytics 8.4.175 disables the end2end branch for executorch (and litert INT8); the .pte would be byte-identical in behaviour to the :raw export, see the *_raw entry")
            continue
        try:
            m = YOLO(pt)
            kw = dict(format=fmt, imgsz=imgsz, device="cpu")
            if fmt == "onnx":
                kw.update(dynamic=False, simplify=True)
            if kind == "e2e":
                kw["nms"] = False  # NMS-free one-to-one head (YOLO26); Ultralytics disables it for executorch/litert-int8
            p = m.export(**kw)
            dst = os.path.join(out_dir, f"{tag}{os.path.splitext(p)[1]}" if os.path.isfile(p) else f"{tag}_{fmt}_model")  # *_executorch_model loads in Ultralytics AutoBackend
            if os.path.isdir(p):
                shutil.rmtree(dst, ignore_errors=True)
                shutil.copytree(p, dst)
            else:
                shutil.copyfile(p, dst)
            r = dict(status="ok", path=os.path.relpath(dst, out_dir), bytes=size(dst), sha256=sha(dst), seconds=round(time.time() - t0, 1))
            if fmt == "onnx":
                r["io"] = onnx_io(dst)
            res[fmt] = r
        except Exception as e:
            res[fmt] = dict(status="failed", error=f"{type(e).__name__}: {str(e)[:400]}", seconds=round(time.time() - t0, 1),
                            trace_tail=traceback.format_exc()[-600:])
        print(tag, fmt, res[fmt].get("status"), res[fmt].get("error", ""), flush=True)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--det", action="append", default=[], help="pt:kind:imgsz")
    ap.add_argument("--cls", action="append", default=[], help="pt:imgsz:temperature:names")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    man_path = os.path.join(a.out, "model_manifest.json")
    man = json.load(open(man_path)) if os.path.exists(man_path) else dict(models={})
    from ultralytics import YOLO
    for spec in a.det:
        pt, kind, sz = spec.split(":")
        tag = os.path.basename(os.path.dirname(os.path.dirname(pt))) + f"_{kind}"
        names = YOLO(pt).names
        man["models"][tag] = dict(task="detect", source_pt=pt, source_pt_sha256=sha(pt), imgsz=int(sz),
                                  preprocess=dict(resize="letterbox (Ultralytics LetterBox auto=False, centre, pad 114)", colour="RGB", layout="NCHW", dtype="float32", normalise="x/255"),
                                  output=("(1,300,6) x1,y1,x2,y2,score,class in model-input pixels; NMS-free" if kind == "e2e" else "(1,4+nc,N) cx,cy,w,h + per-class sigmoid scores in model-input pixels; class-wise NMS iou 0.7 required"),
                                  output_kind=kind, labels=[names[i] for i in range(len(names))], thresholds=dict(detector_min_score=0.35),
                                  quantisation="none (FP32)", exports=export_one(pt, int(sz), a.out, tag, kind))
    for spec in a.cls:
        pt, sz, T, nm = spec.split(":")
        tag = os.path.basename(os.path.dirname(os.path.dirname(pt)))
        man["models"][tag] = dict(task="classify", source_pt=pt, source_pt_sha256=sha(pt), imgsz=int(sz),
                                  preprocess=dict(resize="shorter side -> imgsz, centre crop (Ultralytics classify eval)", colour="RGB", layout="NCHW", dtype="float32", normalise="x/255"),
                                  output="(1,K) softmax probabilities", labels=nm.split(","), temperature=float(T),
                                  calibration="p_i ∝ p_i^(1/T) (temperature fitted on val)", thresholds=dict(quality_min_max_prob=0.5),
                                  rubric="rubric-v0.1-g1", quantisation="none (FP32)", exports=export_one(pt, int(sz), a.out, tag))
    man["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    json.dump(man, open(man_path, "w"), indent=1, ensure_ascii=False)
    print("wrote", man_path)


if __name__ == "__main__":
    main()
