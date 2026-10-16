"""G9 Stage I H2 audit (I1), existing Stage H v2 weights, NO retraining. Post-hoc diagnostic on the frozen Stage H items
(ml/runs/G9/stageH/out/ident_items.jsonl, read-only). Checks: reproduction of the stored H2 probs, ONNX vs PyTorch (.pt state_dict),
ONNX graph output op, class maps, channel order, normalisation, train-eval transform (torchvision PIL) vs sandbox/cv2 transform,
letterbox vs centre-crop, crop context. Writes ml/runs/G9/stageI/out/h2_audit_raw.jsonl (+ summary in h2_audit.json via i_audit_table.py).
Usage: i_audit.py"""
import json, sys, time, numpy as np, cv2, onnx, onnxruntime as ort, torch, timm
from PIL import Image
import torchvision.transforms as T
S = "/workspace/work/nutrisole/ml/runs/G9/stageH"; O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"
ONNX = "/workspace/work/g9h/h2/h2_mnv3s.onnx"; PT = "/workspace/work/g9h/h2v2/h2_mnv3s.pt"
MEAN, STD = np.array([0.485, 0.456, 0.406], np.float32), np.array([0.229, 0.224, 0.225], np.float32)
so = ort.SessionOptions(); so.intra_op_num_threads = 2; sess = ort.InferenceSession(ONNX, so, providers=["CPUExecutionProvider"])
m = timm.create_model("mobilenetv3_small_100", pretrained=False, num_classes=13); m.load_state_dict(torch.load(PT, map_location="cpu")); m.eval()
g = onnx.load(ONNX).graph; last = g.node[-1].op_type
va_tf = T.Compose([T.Resize(256), T.CenterCrop(224), T.ToTensor(), T.Normalize(MEAN.tolist(), STD.tolist())])

def stageh_tensor(crop):  # exact copy of h_ident.h2_probs preprocessing (cv2)
    h, w = crop.shape[:2]; sc = 256 / min(h, w); im = cv2.resize(crop, (max(256, round(w * sc)), max(256, round(h * sc))), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_LINEAR)
    y0, x0 = (im.shape[0] - 224) // 2, (im.shape[1] - 224) // 2; im = im[y0:y0 + 224, x0:x0 + 224][:, :, ::-1].astype(np.float32) / 255
    return ((im - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
def letterbox_tensor(crop, fill=None):  # whole crop kept: pad to square with edge-median colour, resize 224
    h, w = crop.shape[:2]; s = max(h, w); col = np.median(np.concatenate([crop[0], crop[-1], crop[:, 0], crop[:, -1]]), 0) if fill is None else fill
    can = np.empty((s, s, 3), np.uint8); can[:] = col; y0, x0 = (s - h) // 2, (s - w) // 2; can[y0:y0 + h, x0:x0 + w] = crop
    im = cv2.resize(can, (224, 224), interpolation=cv2.INTER_AREA)[:, :, ::-1].astype(np.float32) / 255
    return ((im - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
def onx(x): return sess.run(None, {"images": x})[0][0]
def pt(x):
    with torch.no_grad(): lg = m(torch.from_numpy(x))[0]
    return lg.numpy(), torch.softmax(lg, 0).numpy()
if __name__ == "__main__":
    R = [json.loads(l) for l in open(f"{S}/out/ident_items.jsonl")]
    out = open(f"{O}/h2_audit_raw.jsonl", "w"); t0 = time.time()
    for r in R:
        crop = cv2.imread(r["crop"]); x = stageh_tensor(crop)
        p_onnx = onx(x); lg, p_pt = pt(x)
        xb = x[:, ::-1].copy()  # BGR fed instead of RGB
        p_pil = onx(va_tf(Image.fromarray(crop[:, :, ::-1])).numpy()[None].astype(np.float32))
        p_lb = onx(letterbox_tensor(crop))
        rec = dict(key=r["key"], set=r["set"], split=r["split"], group=r["group"], truth=r["truth"], roi=r["roi"], side=r["side"], hw=list(crop.shape[:2]),
                   wide=r["wide"].get("classId") if r["wide"]["status"] == "identified" else None,
                   stored=r["h2"], onnx=[float(v) for v in p_onnx], pt=[float(v) for v in p_pt], logits=[float(v) for v in lg],
                   bgr=[float(v) for v in onx(xb)], pil=[float(v) for v in p_pil], letterbox=[float(v) for v in p_lb])
        out.write(json.dumps(rec) + "\n")
    out.close(); print(len(R), "items", round(time.time() - t0), "s; onnx last op", last, [o.name for o in g.output], [(i.name, [d.dim_param or d.dim_value for d in i.type.tensor_type.shape.dim]) for i in g.input])
