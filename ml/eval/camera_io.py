"""G9 Stage I (I4) camera integration reference: preview tap -> analysis frame -> full-resolution still, identity crop on the still, and
the H2 model input tensor. EXACT mirror of native/src/cv/pipeline/camera.ts (parity: native/tests/cvCamera.test.ts replays
ml/eval/fixtures/camera_parity.json, written by ml/runs/G9/stageI/scripts/i_camera_fixture.py).

Pure arithmetic (no OpenCV), so the phone and the sandbox compute the same pixels. Rounding is half-up (floor(x + 0.5)) on both sides.
Assumptions to be confirmed on a device (see G9_stageI_android_test.md):
  - preview drawn with resizeMode 'cover' (or 'contain' = letterbox) over the analysis frame, after rotating the sensor buffer clockwise
    by `rotation` degrees and mirroring horizontally for the front camera;
  - analysis frame and still are centre crops of the same sensor field of view (sensor aspect = still aspect unless given).
"""
from __future__ import annotations
import math
import numpy as np

H2_INPUT = 224
H2_RESIZE_SHORT = 256
IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
MODEL_IO = {
    "h2": dict(file="h2_mnv3s.onnx", inputs=[("images", ["n", 3, 224, 224], "float32")], outputs=[("probs", ["n", 13], "float32")],
               colour="RGB", norm="imagenet", output="softmax (13 = 12 classes + unknown at index 12)"),
    "g3_det": dict(file="det_yolo11n_640_raw.onnx", inputs=[(None, [1, 3, 480, 480], "float32")], outputs=[(None, [1, 16, 4725], "float32")],
                   colour="RGB", norm="/255 letterbox 114", output="raw YOLO (4 box + 12 class)"),
    "condition": dict(file="E_224_e15_b64_sgd01.onnx", inputs=[(None, [1, 3, 224, 224], "float32")], outputs=[(None, [1, 2], "float32")],
                      colour="RGB", norm="see Stage G", output="fresh/rotten (grades not displayed)"),
}


def rh(x: float) -> int:
    return int(math.floor(x + 0.5))


def rotate_point(p, deg):
    """Clockwise rotation of a normalised point (same convention as preprocess.ts rotateBoxNormalized)."""
    x, y = p
    if deg == 0: return (x, y)
    if deg == 90: return (1 - y, x)
    if deg == 180: return (1 - x, 1 - y)
    if deg == 270: return (y, 1 - x)
    raise ValueError("rotation must be 0/90/180/270")


def tap_to_frame(tap, view_w, view_h, frame_w, frame_h, rotation=0, mirrored=False, mode="cover"):
    """Tap in preview points -> normalised point in the analysis frame (sensor orientation). None if the tap is outside the image
    (letterbox bars)."""
    dw, dh = (frame_h, frame_w) if rotation in (90, 270) else (frame_w, frame_h)
    s = max(view_w / dw, view_h / dh) if mode == "cover" else min(view_w / dw, view_h / dh)
    px, py = (view_w - dw * s) / 2, (view_h - dh * s) / 2
    x, y = (tap[0] - px) / s / dw, (tap[1] - py) / s / dh
    if not (0 <= x <= 1 and 0 <= y <= 1): return None
    if mirrored: x = 1 - x
    return rotate_point((x, y), (360 - rotation) % 360)


def frame_to_still_box(box, frame_w, frame_h, still_w, still_h, sensor_aspect=None):
    """Analysis-frame pixel box -> still pixel box. Both images are centre crops of the sensor FOV with aspect sensor_aspect
    (default: the still's aspect, i.e. the still is the full sensor)."""
    a = sensor_aspect or still_w / still_h
    def fov(w, h):  # fraction of the sensor width / height this image covers
        r = w / h
        return (1.0, a / r) if r >= a else (r / a, 1.0)
    fw, fh = fov(frame_w, frame_h); sw, sh = fov(still_w, still_h)
    out = []
    for i, v in enumerate(box):
        if i % 2 == 0:
            u = 0.5 + (v / frame_w - 0.5) * fw  # sensor-normalised x
            out.append(((u - 0.5) / sw + 0.5) * still_w)
        else:
            u = 0.5 + (v / frame_h - 0.5) * fh
            out.append(((u - 0.5) / sh + 0.5) * still_h)
    return out


def identity_crop(box, W, H, mode="stageH", pad=0.08, grow=0.15):
    """Close-up identity crop rectangle {x, y, w, h} on the full-res image.
    stageH: box padded by pad*side per axis (closeup.crop_rect semantics; the Stage H frozen behaviour, default).
    square: square context crop, side = max(w, h) * (1 + 2*grow) (<= min(W, H)), shifted inside the image - nothing of the item is cut
            by a centre crop afterwards. Stage I candidate only (post-hoc diagnostic; NOT frozen, needs the human set)."""
    if mode == "stageH":
        w, h = box[2] - box[0], box[3] - box[1]; px, py = pad * w, pad * h
        x1, y1 = max(0, math.floor(box[0] - px)), max(0, math.floor(box[1] - py))
        x2, y2 = min(W, math.ceil(box[2] + px)), min(H, math.ceil(box[3] + py))
        return dict(x=x1, y=y1, w=max(0, x2 - x1), h=max(0, y2 - y1))
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    s = min(max(box[2] - box[0], box[3] - box[1]) * (1 + 2 * grow), W, H); si = rh(s)
    x1 = rh(min(max(0.0, cx - s / 2), W - s)); y1 = rh(min(max(0.0, cy - s / 2), H - s))
    x1, y1 = min(max(0, x1), W - si), min(max(0, y1), H - si)
    return dict(x=x1, y=y1, w=si, h=si)


def resize_bilinear(img: np.ndarray, ow: int, oh: int) -> np.ndarray:
    """HWC uint8 -> HWC float32, bilinear with half-pixel centres and edge clamping (no antialias). Mirror: camera.ts resizeBilinear."""
    h, w = img.shape[:2]
    ys = np.clip((np.arange(oh) + 0.5) * h / oh - 0.5, 0, h - 1); xs = np.clip((np.arange(ow) + 0.5) * w / ow - 0.5, 0, w - 1)
    y0 = np.floor(ys).astype(int); x0 = np.floor(xs).astype(int); y1 = np.minimum(y0 + 1, h - 1); x1 = np.minimum(x0 + 1, w - 1)
    wy = (ys - y0)[:, None, None]; wx = (xs - x0)[None, :, None]; f = img.astype(np.float64)
    top = f[y0][:, x0] * (1 - wx) + f[y0][:, x1] * wx; bot = f[y1][:, x0] * (1 - wx) + f[y1][:, x1] * wx
    return (top * (1 - wy) + bot * wy).astype(np.float32)


def box_reduce(img: np.ndarray, ow: int, oh: int) -> np.ndarray:
    """Integer box pre-reduction before bilinear when downscaling by >= 2x (approximates cv2.INTER_AREA / an antialiased GPU resize):
    k = floor(src / dst) per axis, mean over k x k blocks (trailing rows / cols dropped). Mirror: camera.ts boxReduce."""
    h, w = img.shape[:2]; kx, ky = max(1, w // ow), max(1, h // oh)
    if kx == 1 and ky == 1: return img
    H2, W2 = (h // ky) * ky, (w // kx) * kx; f = img[:H2, :W2].astype(np.float64)
    return f.reshape(H2 // ky, ky, W2 // kx, kx, -1).mean((1, 3)).astype(np.float32)


def h2_input(rgb: np.ndarray, mode="stageH") -> np.ndarray:
    """RGB uint8 crop (HWC) -> float32 NCHW (1, 3, 224, 224), ImageNet mean/std. stageH: short side -> 256, centre 224 (Stage H);
    square: direct resize to 224 (for the square identity crop)."""
    h, w = rgb.shape[:2]
    if mode == "stageH":
        sc = H2_RESIZE_SHORT / min(h, w); ow, oh = max(H2_RESIZE_SHORT, rh(w * sc)), max(H2_RESIZE_SHORT, rh(h * sc))
        r = resize_bilinear(box_reduce(rgb, ow, oh), ow, oh); y0, x0 = (oh - H2_INPUT) // 2, (ow - H2_INPUT) // 2; r = r[y0:y0 + H2_INPUT, x0:x0 + H2_INPUT]
    else:
        r = resize_bilinear(box_reduce(rgb, H2_INPUT, H2_INPUT), H2_INPUT, H2_INPUT)
    x = (r / 255.0 - np.array(IMAGENET_MEAN, np.float32)) / np.array(IMAGENET_STD, np.float32)
    return x.transpose(2, 0, 1)[None].astype(np.float32)


def check_model_io(name: str, meta: dict) -> list[str]:
    """meta: {inputs: [{name, shape, type}], outputs: [...]} as read from the runtime (ONNX Runtime / ExecuTorch). Dynamic dims may be
    a string, -1 or None. Returns a list of mismatches (empty = compatible)."""
    spec = MODEL_IO[name]; errs = []
    for kind in ("inputs", "outputs"):
        got = meta.get(kind) or []
        if len(got) != len(spec[kind]): errs.append(f"{kind}: expected {len(spec[kind])}, got {len(got)}"); continue
        for (nm, shp, ty), g in zip(spec[kind], got):
            if nm and g.get("name") != nm: errs.append(f"{kind} name {g.get('name')} != {nm}")
            if g.get("type", "float32") not in ("float32", "tensor(float)", "float"): errs.append(f"{kind} type {g.get('type')}")
            gs = g.get("shape") or []
            if len(gs) != len(shp): errs.append(f"{kind} rank {len(gs)} != {len(shp)}"); continue
            for i, (a, b) in enumerate(zip(gs, shp)):
                dyn_a = a is None or isinstance(a, str) or a == -1
                if isinstance(b, str):
                    if not dyn_a and not (isinstance(a, int) and a >= 1): errs.append(f"{kind} dim {i} {a}")
                elif not dyn_a and a != b: errs.append(f"{kind} dim {i} {a} != {b}")
                elif dyn_a and not isinstance(b, str): pass  # dynamic where fixed expected: allowed (runtime feeds the fixed size)
    return errs


def still_crop_plan(tap, view, frame, still, frame_boxes, rotation=0, mirrored=False, mode="cover", crop_mode="stageH", roi_frac=0.35):
    """Preview tap -> full-resolution still crop. view/frame/still = (w, h). frame_boxes: tracked boxes in analysis-frame pixels
    (sensor orientation). Returns None (tap outside the image) or {source, frameBox, stillBox, crop, sidePx}."""
    from ml.eval.closeup import roi_from_tap
    p = tap_to_frame(tap, view[0], view[1], frame[0], frame[1], rotation, mirrored, mode)
    if p is None: return None
    r = roi_from_tap(list(p), frame[0], frame[1], frame_boxes, roi_frac)
    sb = frame_to_still_box(r["box"], frame[0], frame[1], still[0], still[1])
    sb = [min(max(sb[0], 0.0), still[0]), min(max(sb[1], 0.0), still[1]), min(max(sb[2], 0.0), still[0]), min(max(sb[3], 0.0), still[1])]
    c = identity_crop(sb, still[0], still[1], crop_mode)
    return dict(source=r["source"], framePoint=[round(p[0], 9), round(p[1], 9)], frameBox=[float(v) for v in r["box"]], stillBox=sb, crop=c,
                sidePx=round(math.sqrt(max(0.0, sb[2] - sb[0]) * max(0.0, sb[3] - sb[1])), 4))
