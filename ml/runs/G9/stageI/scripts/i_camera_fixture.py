"""Writes ml/eval/fixtures/camera_parity.json (TS parity for camera.ts) and out/camera_h2_agreement.json: H2 decisions with the
device-side preprocessing (camera_io.h2_input, pure bilinear) vs the Stage H cv2 path on the 378 audit crops."""
import base64, json, os, sys, random, numpy as np, cv2, onnx
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, os.path.dirname(__file__))
from ml.eval import camera_io as C
from ml.eval.verify import h2_decision, FROZEN_VERIFY
random.seed(3); rng = np.random.default_rng(3); F = dict(taps=[], plans=[], crops=[], h2=[], io={})
views = [(1080, 1920), (1920, 1080), (393, 852), (1000, 1000)]; frames = [(1280, 720), (1920, 1080), (640, 480), (720, 1280)]; stills = [(4000, 3000), (4032, 3024), (3840, 2160)]
for _ in range(60):
    v = random.choice(views); f = random.choice(frames); rot = random.choice([0, 90, 180, 270]); mir = random.random() < 0.3; mode = random.choice(["cover", "letterbox"])
    tap = (round(random.uniform(-20, v[0] + 20), 2), round(random.uniform(-20, v[1] + 20), 2)); out = C.tap_to_frame(tap, *v, *f, rot, mir, mode)
    F["taps"].append(dict(tap=tap, view=v, frame=f, rotation=rot, mirrored=mir, mode=mode, out=None if out is None else [float(x) for x in out]))
for _ in range(40):
    v = random.choice(views); f = random.choice(frames); s = random.choice(stills); rot = random.choice([0, 90, 180, 270]); mir = random.random() < 0.2
    boxes = []
    for _ in range(random.randint(0, 3)):
        x1, y1 = random.uniform(0, f[0] * 0.8), random.uniform(0, f[1] * 0.8); boxes.append([round(x1, 2), round(y1, 2), round(min(f[0], x1 + random.uniform(20, f[0] * 0.5)), 2), round(min(f[1], y1 + random.uniform(20, f[1] * 0.5)), 2)])
    tap = (round(random.uniform(0, v[0]), 2), round(random.uniform(0, v[1]), 2)); cm = random.choice(["stageH", "square"])
    F["plans"].append(dict(tap=tap, view=v, frame=f, still=s, boxes=boxes, rotation=rot, mirrored=mir, mode="cover", cropMode=cm,
                           out=C.still_crop_plan(tap, v, f, s, boxes, rot, mir, "cover", cm)))
for _ in range(40):
    W, H = random.choice(stills); x1, y1 = random.uniform(-50, W), random.uniform(-50, H); box = [x1, y1, x1 + random.uniform(5, W / 2), y1 + random.uniform(5, H / 2)]
    for m in ("stageH", "square"): F["crops"].append(dict(box=box, W=W, H=H, mode=m, out=C.identity_crop(box, W, H, m)))
for (w, h, m) in [(37, 53, "stageH"), (300, 200, "stageH"), (90, 90, "square"), (130, 70, "square"), (700, 560, "stageH"), (640, 640, "square")]:
    img = rng.integers(0, 256, (h, w, 3), np.uint8); x = C.h2_input(img, m).reshape(-1); idx = sorted(rng.choice(len(x), 400, replace=False).tolist())
    F["h2"].append(dict(w=w, h=h, mode=m, rgb=base64.b64encode(img.tobytes()).decode(), idx=idx, vals=[float(x[i]) for i in idx], sum=float(x.astype(np.float64).sum())))
for nm, p in (("h2", "/workspace/work/g9h/h2/h2_mnv3s.onnx"), ("g3_det", "/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx"), ("condition", "/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx")):
    g = onnx.load(p).graph; ini = {i.name for i in g.initializer}
    sh = lambda vi: [d.dim_param or d.dim_value for d in vi.type.tensor_type.shape.dim]
    F["io"][nm] = dict(inputs=[dict(name=i.name, shape=sh(i), type="tensor(float)") for i in g.input if i.name not in ini], outputs=[dict(name=o.name, shape=sh(o), type="tensor(float)") for o in g.output])
    F["io"][nm]["python_check"] = C.check_model_io(nm, F["io"][nm])
json.dump(F, open("/workspace/work/nutrisole/ml/eval/fixtures/camera_parity.json", "w"))
print("io checks", {k: v["python_check"] for k, v in F["io"].items()})
# device preprocessing vs Stage H cv2 path on the audit crops
from i_audit import stageh_tensor, onx
R = [json.loads(l) for l in open("/workspace/work/nutrisole/ml/runs/G9/stageH/out/ident_items.jsonl")]; a = dict(n=0, top1_same=0, decision_same=0, max_abs_prob=0.0)
for r in R:
    crop = cv2.imread(r["crop"]); p0 = onx(stageh_tensor(crop)); p1 = onx(C.h2_input(crop[:, :, ::-1].copy()))
    d0, d1 = h2_decision(p0, FROZEN_VERIFY), h2_decision(p1, FROZEN_VERIFY); a["n"] += 1; a["top1_same"] += int(np.argmax(p0) == np.argmax(p1))
    a["decision_same"] += (d0["accept"], d0.get("classId")) == (d1["accept"], d1.get("classId")); a["max_abs_prob"] = max(a["max_abs_prob"], float(np.abs(p0 - p1).max()))
json.dump(a, open("/workspace/work/nutrisole/ml/runs/G9/stageI/out/camera_h2_agreement.json", "w"), indent=1); print(a)
