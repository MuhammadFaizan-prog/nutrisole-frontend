"""G9 Stage J6 HOST-SIDE checks for the Android debug pipeline (sandbox CPU; NOT a phone; no accuracy claim).

1. ONNX init: loads the two debug-build models (h2_mnv3s.onnx, det_yolo11n_640_raw.onnx, sha256-checked against device/models.ts)
   with onnxruntime (Python), reads input/output names/shapes/types and compares them with MODEL_IO in native/src/cv/pipeline/camera.ts;
   records host init ms, host RSS growth and host per-inference ms (all labelled host-side estimates).
2. Preprocessing parity references, written for the TS side (native/scripts/g9j6_host_pipeline.ts) to compare against:
   - detector: the Ultralytics LetterBox (480, pad 114, centre) the G3 detector was trained/evaluated with, BGR->RGB, /255, NCHW;
   - H2: ml/eval/camera_io.h2_input (the Python mirror the Stage H/I evaluation used) on a fixed centre crop.
   Plus ONNX outputs of both models on the Python tensors, so the TS run can compare model outputs, not just tensors.
3. A tiny synthetic fixture (deterministic, no third-party pixels) is committed for the unit test.

Inputs: sample images = the first N (sorted) unverified J5 training candidates (/workspace/work/g9j5/cands/img; Commons CC/PD; never
eval items, never M-TEST). Outputs (pixels stay outside Git): /workspace/work/g9j6/parity/. Committed: out/j6/host/onnx_check.json,
native/tests/fixtures/g9j6_preproc_parity.json.
  python j6_host_parity.py --n 12
"""
from __future__ import annotations
import argparse, base64, hashlib, json, os, re, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent; J = HERE.parent; REPO = J.parents[3]
sys.path.insert(0, str(REPO / "ml" / "eval"))
import camera_io as CIO  # noqa: E402

MODELS = Path("/workspace/work/g9j6/models"); IMG = Path("/workspace/work/g9j5/cands/img"); OUTD = Path("/workspace/work/g9j6/parity")
REPORT = J / "out" / "j6" / "host" / "onnx_check.json"; FIX = REPO / "native" / "tests" / "fixtures" / "g9j6_preproc_parity.json"
MAX_SIDE = 1280; DET = 480


def sha(p):
    h = hashlib.sha256(); h.update(Path(p).read_bytes()); return h.hexdigest()


def device_models():
    s = (REPO / "native/src/cv/device/models.ts").read_text()
    return {k: dict(file=f, sha256=h) for k, f, h in re.findall(r"(\w+): \{ file: '([^']+)', bytes: \d+, sha256: '([0-9a-f]{64})'", s)}


def model_io_spec():
    s = (REPO / "native/src/cv/pipeline/camera.ts").read_text()
    out = {}
    for k in ("h2", "g3_det"):
        m = re.search(rf"  {k}: \{{ file: '[^']+', inputs: \[\{{ name: ([^,]+), shape: \[([^\]]+)\][^}}]*\}}\], outputs: \[\{{ name: ([^,]+), shape: \[([^\]]+)\]", s)
        dims = lambda t: [int(x) if x.strip().isdigit() else x.strip().strip("'") for x in t.split(",")]
        nm = lambda t: None if t.strip() == "null" else t.strip().strip("'")
        out[k] = dict(input=dict(name=nm(m.group(1)), shape=dims(m.group(2))), output=dict(name=nm(m.group(3)), shape=dims(m.group(4))))
    return out


def rss():
    with open("/proc/self/statm") as f: return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")


def onnx_check():
    import onnxruntime as ort
    dm = device_models(); spec = model_io_spec(); res = dict(label="HOST-SIDE (sandbox CPU, onnxruntime Python %s; device uses onnxruntime-react-native 1.24.3). Not a phone measurement." % ort.__version__, models={})
    sessions = {}
    for k in ("h2", "g3_det"):
        p = MODELS / dm[k]["file"]; ok_sha = sha(p) == dm[k]["sha256"]
        r0 = rss(); t0 = time.perf_counter(); s = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"]); init_ms = (time.perf_counter() - t0) * 1000; r1 = rss()
        i, o = s.get_inputs()[0], s.get_outputs()[0]
        errs = []
        for kind, got, want in (("input", i, spec[k]["input"]), ("output", o, spec[k]["output"])):
            if want["name"] and got.name != want["name"]: errs.append(f"{kind} name {got.name} != {want['name']}")
            if got.type != "tensor(float)": errs.append(f"{kind} type {got.type}")
            if len(got.shape) != len(want["shape"]): errs.append(f"{kind} rank"); continue
            for a, b in zip(got.shape, want["shape"]):
                if isinstance(b, int) and isinstance(a, int) and a != b: errs.append(f"{kind} dim {a} != {b}")
        shape = [1 if not isinstance(d, int) else d for d in i.shape]; x = np.random.default_rng(0).standard_normal(shape).astype(np.float32)
        s.run(None, {i.name: x}); ts = []
        for _ in range(10):
            t = time.perf_counter(); y = s.run(None, {i.name: x})[0]; ts.append((time.perf_counter() - t) * 1000)
        res["models"][k] = dict(file=dm[k]["file"], sha256_matches_device_models_ts=ok_sha, input=dict(name=i.name, shape=i.shape, type=i.type),
                                output=dict(name=o.name, shape=o.shape, type=o.type, run_shape=list(y.shape)), app_spec=spec[k], io_errors=errs,
                                host_init_ms=round(init_ms, 1), host_rss_growth_mb=round((r1 - r0) / 2**20, 1),
                                host_infer_ms_median_of_10=round(float(np.median(ts)), 1), host_threads=os.cpu_count(),
                                weights_mb=round(p.stat().st_size / 2**20, 2))
        sessions[k] = s
    return res, sessions


def det_ref(rgb: np.ndarray) -> np.ndarray:
    from ultralytics.data.augment import LetterBox
    bgr = rgb[:, :, ::-1].copy()
    lb = LetterBox(new_shape=(DET, DET), auto=False, scale_fill=False, scaleup=True, center=True, stride=32)(image=bgr)
    return (lb[:, :, ::-1].astype(np.float32) / 255.0).transpose(2, 0, 1)[None].copy()


def centre_crop_rect(w, h):
    s = int(round(0.5 * min(w, h))); return dict(x=(w - s) // 2, y=(h - s) // 2, w=s, h=s)


def h2_ref(rgb, r):
    return CIO.h2_input(rgb[r["y"]:r["y"] + r["h"], r["x"]:r["x"] + r["w"]], "stageH")


def load_still(p: Path) -> np.ndarray:
    with Image.open(p) as im:
        im = ImageOps.exif_transpose(im).convert("RGB")
        s = min(1.0, MAX_SIDE / max(im.size))
        if s < 1: im = im.resize((round(im.width * s), round(im.height * s)), Image.BILINEAR)
        return np.asarray(im, dtype=np.uint8)


def synth():
    g = np.random.default_rng(6)
    a = np.zeros((61, 97, 3), np.uint8); a[..., 0] = np.linspace(0, 255, 97)[None]; a[..., 1] = np.linspace(255, 0, 61)[:, None]; a[..., 2] = 77
    b = g.integers(0, 256, (120, 160, 3), dtype=np.uint8)
    c = ((np.indices((100, 150)).sum(0) // 25) % 2 * 200 + 30).astype(np.uint8)[..., None].repeat(3, 2); c[..., 1] //= 2
    return dict(gradient_97x61=a, noise_160x120=b, checker_150x100=c)


def sample_idx(n_total, k=800):
    return np.unique(np.linspace(0, n_total - 1, k).astype(int))


def main(n):
    OUTD.mkdir(parents=True, exist_ok=True)
    rep, S = onnx_check()
    # real sample images -> raw stills + reference tensors + reference model outputs
    files = sorted(IMG.glob("*.jpg"))[:n]; items = []
    for p in files:
        rgb = load_still(p); h, w = rgb.shape[:2]; r = centre_crop_rect(w, h)
        d = det_ref(rgb); x2 = h2_ref(rgb, r)
        yd = S["g3_det"].run(None, {"images": d})[0]; y2 = S["h2"].run(None, {"images": x2})[0]
        stem = p.stem
        (OUTD / f"{stem}.rgb").write_bytes(rgb.tobytes()); d.astype("<f4").tofile(OUTD / f"{stem}.det.f32"); x2.astype("<f4").tofile(OUTD / f"{stem}.h2.f32")
        yd.astype("<f4").tofile(OUTD / f"{stem}.detout.f32"); y2.astype("<f4").tofile(OUTD / f"{stem}.h2out.f32")
        items.append(dict(id=stem, w=w, h=h, crop=r, h2_top1=int(y2[0].argmax())))
    (OUTD / "index.json").write_text(json.dumps(dict(items=items, max_side=MAX_SIDE, det=DET, note="host-side parity data; pixels not committed"), indent=1))
    rep["sample_images"] = dict(source="unverified J5 training candidates (Commons CC/PD), first %d sorted; not eval, not M-TEST" % len(items), ids=[i["id"] for i in items])
    REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps(rep, indent=1))
    # committed synthetic fixture
    fx = dict(note="G9 J6 synthetic preprocessing parity fixture (deterministic, no third-party pixels). det = Ultralytics LetterBox reference; h2 = camera_io.h2_input on crop.", cases=[])
    for name, a in synth().items():
        h, w = a.shape[:2]; r = centre_crop_rect(w, h); d = det_ref(a).ravel(); x2 = h2_ref(a, r).ravel()
        di = sample_idx(d.size); hi = sample_idx(x2.size)
        fx["cases"].append(dict(name=name, w=w, h=h, rgb_b64=base64.b64encode(a.tobytes()).decode(), crop=r,
                                det=dict(n=int(d.size), idx=di.tolist(), val=[round(float(v), 6) for v in d[di]], mean=float(d.mean())),
                                h2=dict(n=int(x2.size), idx=hi.tolist(), val=[round(float(v), 6) for v in x2[hi]], mean=float(x2.mean()))))
    FIX.parent.mkdir(parents=True, exist_ok=True); FIX.write_text(json.dumps(fx))
    print(json.dumps(dict(models={k: dict(io_errors=v["io_errors"], sha_ok=v["sha256_matches_device_models_ts"], init_ms=v["host_init_ms"], infer_ms=v["host_infer_ms_median_of_10"]) for k, v in rep["models"].items()}, n=len(items)), indent=1))


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--n", type=int, default=12); main(a.parse_args().n)
