"""Device parity bundle for the Android H2 check (I4): 12 close-up crops (from the Stage H audit set, Commons-licensed, downscaled to
<= 320 px) with expected H2 probabilities for BOTH input paths: sandbox cv2 (Stage H) and camera_io.h2_input (the device path), plus
tensor checksums. -> ml/runs/G9/stageI/device_parity/{*.png, expected.json}"""
import json, os, sys, cv2, numpy as np
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, os.path.dirname(__file__))
from ml.eval import camera_io as C
from i_audit import stageh_tensor, onx
D = "/workspace/work/nutrisole/ml/runs/G9/stageI/device_parity"; os.makedirs(D, exist_ok=True)
R = [json.loads(l) for l in open("/workspace/work/nutrisole/ml/runs/G9/stageH/out/ident_items.jsonl")]
pick = [r for r in R if r["group"] == "item"][::7][:8] + [r for r in R if r["group"] in ("unsupported", "printed")][::9][:4]
exp = {}
for i, r in enumerate(pick):
    im = cv2.imread(r["crop"]); h, w = im.shape[:2]; s = min(1.0, 320 / max(h, w)); im = cv2.resize(im, (max(1, round(w * s)), max(1, round(h * s))), interpolation=cv2.INTER_AREA)
    fn = f"p{i:02d}.png"; cv2.imwrite(f"{D}/{fn}", im); im = cv2.imread(f"{D}/{fn}")
    x = C.h2_input(im[:, :, ::-1].copy())
    exp[fn] = dict(key=r["key"], truth_source_label=r["truth"], hw=list(im.shape[:2]), probs_device_path=[round(float(v), 6) for v in onx(x)],
                   probs_stageH_cv2=[round(float(v), 6) for v in onx(stageh_tensor(im))], input_sum=float(x.astype(np.float64).sum()), input_first8=[float(v) for v in x.reshape(-1)[:8]])
json.dump(dict(model="h2_mnv3s.onnx (Stage H v2, unchanged)", tolerance_abs_prob=0.02, input="camera.ts h2Input(rgb, w, h, 'stageH')", items=exp), open(f"{D}/expected.json", "w"), indent=1)
print(len(exp), "items", sum(os.path.getsize(f"{D}/{f}") for f in os.listdir(D)) // 1024, "KB")
