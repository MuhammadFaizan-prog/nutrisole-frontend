"""G9 Stage B shared pipeline pieces (used by the DEV replay and the holdout kernel; identical code in both).
Verifier = MobileNetV3-Small produce-vs-non-produce on a 128x128 crop of the box expanded 1.2x (ImageNet normalisation, RGB).
VerifiedTracker = stock IouTracker (app defaults) + selective verification with cached per-track results:
  - a track is verified the first time the IouTracker would display it (its display birth), then again at most every K processed
    frames (K = 10, ~1 s at 10 fps) while it is matched; verdict = mean of its cached p(produce);
  - a displayed track is shown only if verdict >= tau. Tracks never displayed by the IouTracker are never verified (no extra cost).
Nothing else changes (detector, floor 0.35, area guard, IouTracker parameters, label hysteresis)."""
import numpy as np, cv2, time
from tracker import IouTracker

MEAN = np.array([0.485, 0.456, 0.406], np.float32).reshape(1, 3, 1, 1); STD = np.array([0.229, 0.224, 0.225], np.float32).reshape(1, 3, 1, 1)


def crop128(frame, box, e=1.2, s=128):
    H, W = frame.shape[:2]; cx, cy = (box[0] + box[2]) / 2 * W, (box[1] + box[3]) / 2 * H; w, h = (box[2] - box[0]) * W * e, (box[3] - box[1]) * H * e
    x0, y0, x1, y1 = int(max(0, cx - w / 2)), int(max(0, cy - h / 2)), int(min(W, cx + w / 2)), int(min(H, cy + h / 2))
    if x1 - x0 < 4 or y1 - y0 < 4: return None
    return cv2.resize(frame[y0:y1, x0:x1], (s, s))


class Verifier:
    def __init__(self, onnx_path, threads=1):
        import onnxruntime as ort
        so = ort.SessionOptions(); so.intra_op_num_threads = threads; so.inter_op_num_threads = 1
        self.s = ort.InferenceSession(onnx_path, so, providers=["CPUExecutionProvider"]); self.i = self.s.get_inputs()[0].name
        self.calls = 0; self.ms = []

    def __call__(self, crops):
        if not crops: return []
        a = time.perf_counter()
        x = np.stack([c[:, :, ::-1] for c in crops]).astype(np.float32).transpose(0, 3, 1, 2) / 255.0
        x = (x - MEAN) / STD
        z = self.s.run(None, {self.i: x.astype(np.float32)})[0].reshape(-1)
        self.calls += len(crops); self.ms.append(1000 * (time.perf_counter() - a))
        return list(1 / (1 + np.exp(-z)))


class VerifiedTracker(IouTracker):
    def __init__(self, verifier, tau, K=10, **p):
        super().__init__(**p); self.v, self.tau, self.K = verifier, tau, K
        self.cache = {}; self.last = {}; self.fidx = 0; self.frame = None; self.calls_this = 0

    def reset(self):
        super().reset(); self.cache = {}; self.last = {}

    def update(self, dets, t_ms, frame=None):
        shown = super().update(dets, t_ms); self.fidx += 1; self.calls_this = 0
        live = {t.id: t for t in self.tracks}; need = []
        for s in shown:
            i = s["id"]
            if i not in self.cache or (self.fidx - self.last[i] >= self.K):
                need.append(i)
        if need and frame is not None:
            crops, ids = [], []
            for i in need:
                c = crop128(frame, live[i].rawBox)
                if c is not None: crops.append(c); ids.append(i)
            for i, p in zip(ids, self.v(crops)):
                self.cache.setdefault(i, []).append(float(p)); self.last[i] = self.fidx
            self.calls_this = len(crops)
        out = []
        for s in shown:
            ps = self.cache.get(s["id"])
            s["verdict"] = float(np.mean(ps)) if ps else None
            if ps is None or s["verdict"] >= self.tau: out.append(s)
        for i in list(self.cache):
            if i not in live: self.cache.pop(i, None); self.last.pop(i, None)
        return out
