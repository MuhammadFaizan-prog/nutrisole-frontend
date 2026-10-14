"""G9 Stage B DEV on independent real material (never trained on): HN-dev (31 agent-verified produce-free images / crops) and the 6 M-dev
clips (10 fps fixed-frame like the holdout kernel). For a detector ONNX (+ optional verifier ONNX) caches per-frame boxes (floor 0.35,
area guard) and each box's verifier p(produce); arms are then replayed offline with the stock IouTracker or the VerifiedTracker logic
(verification at display birth, then every 10 processed frames; verdict = mean p of the matched raw box).
Usage: stageb_mdev.py cache DET.onnx TAG [VERIFIER.onnx]   |   stageb_mdev.py score TAG [TAU]"""
import json, os, sys, csv, time, collections
import numpy as np
R = "/workspace/work/nutrisole"; sys.path.insert(0, f"{R}/ml/eval"); sys.path.insert(0, f"{R}/ml"); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tracker import IouTracker, iou
G = "/workspace/work/cv/g9b"; O = f"{G}/mdev"; os.makedirs(O, exist_ok=True)
split = {r["clip_id"]: r for r in csv.DictReader(open(f"{R}/ml/runs/G9/stageB/mining_split.csv"))}
MDEV = [c for c, r in split.items() if r["stageB_role"] == "M-dev"]
man = list(csv.DictReader(open(f"{R}/ml/runs/G9/stageB/hn_manifest.csv")))
HNDEV = [r for r in man if r["split"] == "dev" and r["review"] == "agent_verified_negative" and r["dedup"] == "kept"]
def vpath(c):
    for d in ("g6src", "g7src"):
        for e in ("webm", "ogv"):
            p = f"/workspace/work/cv/{d}/raw/{c}.{e}"
            if os.path.exists(p): return p
if sys.argv[1] == "cache":
    import cv2, onnxruntime as ort
    from geometry import letterbox, dst_to_src, decode
    from scene_guard import scene_guard
    from stageb_pipe import Verifier, crop128
    DET, TAG = sys.argv[2], sys.argv[3]; V = Verifier(sys.argv[4], 2) if len(sys.argv) > 4 else None
    so = ort.SessionOptions(); so.intra_op_num_threads = 2; s = ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"]); di = s.get_inputs()[0].name
    def det(fr):
        H, W = fr.shape[:2]; x, tf = letterbox(fr, 480); o = s.run(None, {di: x})[0]; ds = []
        for d in decode(o, "raw", 0.35):
            b = dst_to_src(d["box"], tf)
            if b[2] - b[0] < 2 or b[3] - b[1] < 2: continue
            ds.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=int(d["classId"]), score=float(d["score"])))
        ds = scene_guard(ds, maxSameClass=0, minAreaFrac=0.01)
        ps = V([crop128(fr, d["box"]) for d in ds]) if (V and ds) else [None] * len(ds)
        return [[round(v, 5) for v in d["box"]] + [d["classId"], round(d["score"], 4), None if p is None else round(float(p), 5)] for d, p in zip(ds, ps)]
    fo = f"{O}/{TAG}.json"; out = json.load(open(fo)) if os.path.exists(fo) else {}; t0 = time.time()
    if "hndev" not in out:
        out["hndev"] = {}
        for r in HNDEV:
            p = f"{G}/hn_local/{r['id']}.jpg" if r["kind"] == "video_crop" else f"{G}/commons/img/cm{r['id'][3:]}.jpg"
            out["hndev"][r["id"]] = det(cv2.imread(p))
    pos = {x["id"]: x for x in json.load(open(f"{G}/vsheets/vd_cands.json"))}
    for c in MDEV:
        if c in out: continue
        cap = cv2.VideoCapture(vpath(c)); fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        if not (1 <= fps <= 120): fps = 25.0
        stride = max(1, int(round(fps / 10))); fi = 0; rec = []
        want = collections.defaultdict(list); posd = {}
        for k, x in pos.items():
            if x["clip"] == c: want[x["fi"]].append(k)
        while True:
            ok, fr = cap.read()
            if not ok: break
            if fi % stride == 0: rec.append([round(1000 * fi / fps, 1), det(fr)])
            if fi in want:
                dd = det(fr) if fi % stride else rec[-1][1]
                for k in want[fi]: posd[k] = dd
            fi += 1
        out[c] = dict(fps=fps, stride=stride, dur_s=fi / fps, rec=rec, pos_frames=posd)
        json.dump(out, open(fo, "w")); print(c, round(time.time() - t0), flush=True)
        if time.time() - t0 > 80: print("budget stop"); sys.exit(0)
    json.dump(out, open(fo, "w")); print("ALL DONE", TAG)
else:
    TAG = sys.argv[2]; TAU = float(sys.argv[3]) if len(sys.argv) > 3 else None; d = json.load(open(f"{O}/{TAG}.json"))
    keep = lambda b: TAU is None or b[6] is None or b[6] >= TAU
    hn = {k: [b for b in v if keep(b)] for k, v in d["hndev"].items()}
    res = dict(tag=TAG, tau=TAU, hndev=dict(n=len(hn), images_with_false_box=sum(1 for v in hn.values() if v), false_boxes=sum(len(v) for v in hn.values()),
                                          high_conf_ge_075=sum(1 for v in hn.values() for b in v if b[5] >= 0.75)))
    # M-dev video: displayed track births/min (all classes; truth is clip-level-unverified -> report only)
    births = 0; minutes = 0; per = {}; vcalls = 0; frames = 0
    pos = {x["id"]: x for x in json.load(open(f"{G}/vsheets/vd_cands.json"))}
    VD_POS = {**{f"vd{i:03d}": "banana" for i in list(range(3, 11)) + [12]}, "vd014": "carrot", "vd021": "carrot", **{f"vd{i:03d}": "tomato" for i in range(22, 52)}}
    for c in MDEV:
        x = d[c]; trk = IouTracker(); ids = set(); cache = {}; last = {}; fidx = 0
        for t, ds in x["rec"]:
            dd = [dict(box=b[:4], classId=b[4], score=b[5], p=b[6]) for b in ds]
            sh = trk.update(dd, t); fidx += 1; frames += 1
            live = {tr.id: tr for tr in trk.tracks}
            for s_ in sh:
                if TAU is not None and (s_["id"] not in cache or fidx - last[s_["id"]] >= 10):
                    rb = live[s_["id"]].rawBox; m = [e["p"] for e in dd if e["box"] == rb]
                    if m and m[0] is not None: cache.setdefault(s_["id"], []).append(m[0]); last[s_["id"]] = fidx; vcalls += 1
                if TAU is None or not cache.get(s_["id"]) or np.mean(cache[s_["id"]]) >= TAU: ids.add(s_["id"])
        per[c] = len(ids); births += len(ids); minutes += x["dur_s"] / 60
    res["mdev_video"] = dict(clips=len(MDEV), minutes=round(minutes, 2), displayed_tracks=births, births_per_min=round(births / minutes, 3), per_clip=per,
                             verifier_calls_per_frame=round(vcalls / frames, 4) if TAU is not None else 0)
    # retention of agent-verified real produce boxes in M-dev frames (any supported class, IoU >= 0.3 with the verified box)
    kept = collections.Counter(); tot = collections.Counter()
    for k, cls in VD_POS.items():
        x = pos[k]; ds = [b for b in d[x["clip"]]["pos_frames"].get(k, []) if keep(b)]; tot[cls] += 1
        if any(iou(b[:4], x["box"]) >= 0.3 for b in ds): kept[cls] += 1
    res["mdev_real_produce_retained"] = {c: f"{kept[c]}/{tot[c]}" for c in tot}; res["mdev_real_produce_retained_total"] = f"{sum(kept.values())}/{sum(tot.values())}"
    json.dump(res, open(f"{O}/score_{TAG}_{TAU}.json", "w"), indent=1); print(json.dumps(res))
