"""G5.1a safety filter for mined hard-negative crops: two-model disagreement.
A crop mined from an ISOLATED A1 detection is kept as a background (hard negative) only if a second, independently
trained detector (G3 control yolo11n@480) finds NOTHING in the crop at score >= --conf. Crops where the second model
also sees produce of our 12 classes are dropped (they are likely real items, e.g. bananas / yellow capsicum in a stall),
so the hard negatives do not teach the model to suppress real targets. Writes OUT json with kept/dropped lists."""
import argparse, glob, json, os, sys
import cv2, onnxruntime as ort
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "eval"))
from geometry import letterbox, decode  # noqa: E402
ap = argparse.ArgumentParser(); ap.add_argument("--det", required=True); ap.add_argument("--crops", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--conf", type=float, default=0.25); ap.add_argument("--imgsz", type=int, default=480)
a = ap.parse_args()
so = ort.SessionOptions(); so.intra_op_num_threads = 2
s = ort.InferenceSession(a.det, so, providers=["CPUExecutionProvider"]); i = s.get_inputs()[0].name
keep, drop = [], []
for f in sorted(glob.glob(f"{a.crops}/*.jpg")):
    x, _ = letterbox(cv2.imread(f), a.imgsz)
    d = decode(s.run(None, {i: x})[0], "raw", a.conf)
    (drop if d else keep).append(os.path.basename(f))
json.dump(dict(second_model=a.det, conf=a.conf, kept=keep, dropped=drop), open(a.out, "w"), indent=1)
print(len(keep), "kept", len(drop), "dropped")
