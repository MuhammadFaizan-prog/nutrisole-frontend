"""Stage G end-to-end harness (DEV only; M-TEST never opened). Modes (each resumable, <= ~100 s per call):
  detcache CLIP      cache G3 detections (frame px) for a DEV clip: det_clip | quality_clip | neg_clip | devneg_clip
  wide               DEV clips: tracker + identification policy vs G3-alone labels: ID accuracy, time to ID, false IDs, FP/min
  mdev               M-DEV v2 stills: identified boxes vs labels (IoU .5; crowd/ignore excluded), box-free FPs, policy vs G3
  closeup_clip       quality_clip: track -> tap ROI -> frozen gate on frame px -> assess every 3rd frame (5 Hz) -> grade / Not graded
  approach           CU-check stills as a simulated move-closer sequence (20 frames, scale 0.2 -> 1.0, 15 fps)
  negatives          CU unsupported / printed / grayscale / processed / crowd stills: ID policy + single-frame gate (abstention)
  summary            aggregate everything into out/e2e.json"""
import json, os, sys, time, collections, cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from g_models import detect, assess, N, VERSIONS
from ml.eval.closeup import ANALYSIS_MAX_SIDE, roi_from_tap, crop_rect, id_policy, quality_reasons, GradeGate, FROZEN_GATE, touches_edge, blockiness
from ml.eval.tracker import IouTracker
from ml.prices.display import category_price, graded_price
B = "/workspace/work/nutrisole/ml/runs/G9/stageG"; C = "/workspace/work/g9g/cache"; os.makedirs(C, exist_ok=True)
CLIPS = {"det_clip": "/workspace/work/cv/g3clips_dev/det_clip", "quality_clip": "/workspace/work/cv/g3clips_dev/quality_clip",
         "neg_clip": "/workspace/work/cv/g3clips_dev/neg_clip", "devneg_clip": "/workspace/work/cv/g3clips_devneg/neg_clip"}
PRICES = [json.load(open(f"/workspace/work/nutrisole/ml/prices/fixtures/parsed_{k}_2026-10-12.json")) for k in ("fruit", "vegetable")]; TODAY = "2026-10-14"
T0 = time.time(); LIM = 95

def frames(path):
    cap = cv2.VideoCapture(path + ".mp4")
    while True:
        ok, f = cap.read()
        if not ok: return
        yield f

def detcache(name):
    p = f"{C}/{name}.json"; d = json.load(open(p)) if os.path.exists(p) else {"dets": [], "ms": []}
    for i, f in enumerate(frames(CLIPS[name])):
        if i < len(d["dets"]): continue
        if time.time() - T0 > LIM: break
        t = time.perf_counter(); dd = detect(f); d["ms"].append((time.perf_counter() - t) * 1e3)
        d["dets"].append([[list(map(float, b)), c, s] for b, c, s in dd])
    json.dump(d, open(p, "w")); print(name, len(d["dets"]))

def run_tracks(name, policy=True):
    meta = json.load(open(CLIPS[name] + ".json")); d = json.load(open(f"{C}/{name}.json"))["dets"]; tr = IouTracker(); hits = collections.Counter(); out = []
    for i, dets in enumerate(d):
        t_ms = i * 1000 / meta["fps"]
        ts = tr.update([dict(box=b, classId=c, score=s) for b, c, s in dets], t_ms); fr = []
        for t in ts:
            hits[t["id"]] += 1; idr = id_policy(t["label"], t["score"], hits[t["id"]])
            fr.append(dict(id=t["id"], box=t["box"], label=t["label"], score=t["score"], idr=idr["status"]))
        out.append(fr)
    return meta, out

def _iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u > 0 else 0

def wide():
    """Per frame, a shown track is a correct ID if it overlaps (IoU >= 0.3, boxes smoothed by the tracker) a ground-truth object of the
    same class in that frame's clip annotation; otherwise it is a false ID. Time to ID = first correct ID of the segment's object."""
    res = {}
    for name in ("det_clip", "quality_clip", "neg_clip", "devneg_clip"):
        if not os.path.exists(f"{C}/{name}.json"): continue
        meta, out = run_tracks(name); fps = meta["fps"]; nfr = len(out); W, H = meta["w"], meta["h"]; segs = meta.get("segments", [])
        st = {m: dict(correct=0, false=0) for m in ("g3", "policy")}; st["policy"]["unable_frames"] = 0; false_ids = {"g3": set(), "policy": set()}
        gt_frames = {"g3": 0, "policy": 0}; ngt = 0
        for i, fr in enumerate(out):
            gts = [[o["box_norm"][0] * W, o["box_norm"][1] * H, o["box_norm"][2] * W, o["box_norm"][3] * H, o["cls"]] for o in meta["frames"][i]["objects"]]; ngt += len(gts)
            hit = {"g3": set(), "policy": set()}
            for t in fr:
                for m in ("g3", "policy"):
                    if m == "policy" and t["idr"] != "identified":
                        st[m]["unable_frames"] += t["idr"] == "unable"; continue
                    j = [k for k, g in enumerate(gts) if g[4] == t["label"] and _iou(t["box"], g) >= 0.3]
                    if j: st[m]["correct"] += 1; hit[m].update(j)
                    else: st[m]["false"] += 1; false_ids[m].add(t["id"])
            for m in hit: gt_frames[m] += len(hit[m])
        tti = {"g3": [], "policy": []}; segid = {"g3": 0, "policy": 0}
        for s in segs:
            if s.get("cls") is None or s["cls"] < 0: continue
            for m in ("g3", "policy"):
                first = None
                for i in range(s["start"], min(s["end"] + 1, nfr)):
                    gts = [[o["box_norm"][0] * W, o["box_norm"][1] * H, o["box_norm"][2] * W, o["box_norm"][3] * H, o["cls"]] for o in meta["frames"][i]["objects"] if o["cls"] == s["cls"]]
                    if any((m == "g3" or t["idr"] == "identified") and t["label"] == s["cls"] and any(_iou(t["box"], g) >= 0.3 for g in gts) for t in out[i]): first = i; break
                if first is not None: segid[m] += 1; tti[m].append((first - s["start"]) * 1000 / fps)
        npos = sum(1 for s in segs if s.get("cls") is not None and s["cls"] >= 0); mins = nfr / fps / 60; ms = json.load(open(f"{C}/{name}.json"))["ms"]
        res[name] = dict(frames=nfr, minutes=round(mins, 2), positive_segments=npos, gt_object_frames=ngt, frame_level=st,
                         gt_recall_frames={m: (round(v / ngt, 3) if ngt else None) for m, v in gt_frames.items()},
                         id_precision_frames={m: (round(st[m]["correct"] / (st[m]["correct"] + st[m]["false"]), 3) if st[m]["correct"] + st[m]["false"] else None) for m in st},
                         segments_identified={m: (round(v / npos, 3) if npos else None) for m, v in segid.items()},
                         time_to_id_ms={m: (dict(p50=round(float(np.percentile(v, 50))), p95=round(float(np.percentile(v, 95))), n=len(v)) if v else None) for m, v in tti.items()},
                         false_id_tracks={m: len(v) for m, v in false_ids.items()}, false_id_tracks_per_min={m: round(len(v) / mins, 2) for m, v in false_ids.items()},
                         det_ms=dict(p50=round(float(np.percentile(ms, 50)), 1), p95=round(float(np.percentile(ms, 95)), 1), n=len(ms)))
    json.dump(res, open(f"{B}/out/e2e_wide.json", "w"), indent=1); print(json.dumps(res)[:3000])

def mdev():
    L = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageF/m_labels_v2.json")); p = f"{C}/mdev.json"; d = json.load(open(p)) if os.path.exists(p) else {}
    for k, v in L.items():
        if k in d or v["status"] != "ok": continue
        if time.time() - T0 > LIM: break
        im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{k}.jpg"); H, W = im.shape[:2]
        d[k] = dict(W=W, H=H, dets=[[list(map(float, b)), c, s] for b, c, s in detect(im)])
    json.dump(d, open(p, "w")); print("mdev cached", len(d))
    if len(d) < sum(v["status"] == "ok" for v in L.values()): return
    def iou(a, b):
        ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
        u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i; return i / u if u else 0
    r = {m: dict(tp=0, fp=0, fp_boxfree=0, ignored=0) for m in ("g3", "policy")}; ngt = 0
    for k, v in d.items():
        lab = L[k]; W, H = v["W"], v["H"]; gt = [[b[0] * W, b[1] * H, b[2] * W, b[3] * H, b[4]] for b in lab["boxes"]]; ngt += len(gt)
        cr = [[b[0] * W, b[1] * H, b[2] * W, b[3] * H, b[4]] for b in lab["crowd"]]
        for m in ("g3", "policy"):
            used = set()
            for b, c, s in sorted(v["dets"], key=lambda x: -x[2]):
                if m == "policy" and id_policy(c, s, 3)["status"] != "identified": continue
                j = max(range(len(gt)), key=lambda j: iou(b, gt[j]) if gt[j][4] == c and j not in used else -1, default=None)
                if j is not None and gt[j][4] == c and j not in used and iou(b, gt[j]) >= 0.5: used.add(j); r[m]["tp"] += 1; continue
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                if any(z[0] <= cx <= z[2] and z[1] <= cy <= z[3] and (len(z) < 5 or z[4] in (c, -1)) for z in cr): r[m]["ignored"] += 1; continue
                r[m]["fp"] += 1; r[m]["fp_boxfree"] += lab["negative"]
    out = dict(images=len(d), gt_boxes=ngt, **r, note="stills: tracker hits assumed (policy = score >= 0.5); crowd/ignore matches excluded; same-class only")
    json.dump(out, open(f"{B}/out/e2e_mdev.json", "w"), indent=1); print(out)

def assess_crop(frame, box, cls, P, timings):
    H, W = frame.shape[:2]; t = time.perf_counter(); cr = crop_rect(box, W, H); crop = frame[cr["y"]:cr["y"] + cr["h"], cr["x"]:cr["x"] + cr["w"]]
    timings["crop"] = (time.perf_counter() - t) * 1e3
    if cr["sidePx"] < P["minSidePx"] or min(crop.shape[:2]) < 8:
        return dict(ok=False, grade=None, pFresh=None, reasons=["too_small: move closer"], side=cr["sidePx"], skipped_models=True)
    if max(crop.shape[:2]) > ANALYSIS_MAX_SIDE:  # analysis copy capped at 256 px (INTER_AREA); gate size stays in native frame px
        sc = ANALYSIS_MAX_SIDE / max(crop.shape[:2]); crop = cv2.resize(crop, (max(8, round(crop.shape[1] * sc)), max(8, round(crop.shape[0] * sc))), interpolation=cv2.INTER_AREA)
    timings["crop"] = (time.perf_counter() - t) * 1e3
    a = assess(crop, cls, timings); t = time.perf_counter()
    q = dict(sidePx=cr["sidePx"], blurVar=a["blurVar"], meanV=a["meanV"], touchesEdge=touches_edge(box, W, H, P["edgeMarginFrac"]), visibleFrac=a["visibleFrac"],
             maxProb=a["maxProb"], margin=a["margin"], blockiness=blockiness(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)))
    rs = quality_reasons(q, P) + ([] if a["grade"] in ("A", "B", "C", "Reject") else ["rubric_ungradable"]); timings["checks"] = (time.perf_counter() - t) * 1e3
    return dict(ok=not rs, grade=a["grade"], pFresh=a["probs"]["fresh"], cond=a["cond"], reasons=rs, side=cr["sidePx"], ripeness=a["ripeness"])

def closeup_clip():
    """quality_clip: the user taps the item once it is tracked (first identified frame); assessments at 5 Hz (every 3rd frame)."""
    meta, out = run_tracks("quality_clip"); fr_all = list(frames(CLIPS["quality_clip"])); p = f"{B}/out/e2e_closeup_clip.json"
    res = json.load(open(p)) if os.path.exists(p) else {"segments": []}; done = len(res["segments"]); P = FROZEN_GATE
    for k, s in enumerate(meta["segments"]):
        if k < done: continue
        if time.time() - T0 > LIM: break
        g = GradeGate(P); tap_frame = None; tid = None; ev = []; first_grade = None; grades = []; lat = []
        for i in range(s["start"], min(s["end"] + 1, len(out))):
            tr = [t for t in out[i] if t["idr"] == "identified"]
            if tid is None and tr: tid = tr[0]["id"]; tap_frame = i
            if tid is None or (i - tap_frame) % 3: continue
            t = next((t for t in out[i] if t["id"] == tid), None)
            if t is None: ev.append("lost"); continue
            tm = {}; t1 = time.perf_counter(); a = assess_crop(fr_all[i], t["box"], N[t["label"]], P, tm); dec = g.push(a)
            pr = graded_price(True, N[t["label"]], dec.get("grade") if dec["status"] == "graded" else None, PRICES, TODAY); tm["price"] = 0.0
            tm["total"] = (time.perf_counter() - t1) * 1e3; lat.append(tm)
            ev.append(dec["status"])
            if dec["status"] == "graded":
                grades.append(dec["grade"]); first_grade = first_grade if first_grade is not None else i
        res["segments"].append(dict(k=k, cls=N[s["cls"]], label=s["quality"], tap_frame=tap_frame, id_frame_ms=None if tap_frame is None else round((tap_frame - s["start"]) * 1000 / meta["fps"]),
                                    grade_ms=None if first_grade is None else round((first_grade - s["start"]) * 1000 / meta["fps"]), events=ev, grades=grades,
                                    last_cond=a.get("cond") if tid is not None and 'a' in dir() else None, lat=lat))
        json.dump(res, open(p, "w"))
    print("closeup segments", len(res["segments"]), "/", len(meta["segments"]))

def approach():
    """CU-check items as a simulated approach: frame = the still scaled by f (0.2 -> 1.0, 20 frames) on a canvas of the original size
    whose surround is a blurred, darkened copy (no new detail is invented: the item never exceeds its native pixels)."""
    T = json.load(open(f"{B}/cu_triage.json")); L = json.load(open(f"{B}/out/cu_leak_split.json")); p = f"{B}/out/e2e_approach.json"
    res = json.load(open(p)) if os.path.exists(p) else {}; P = FROZEN_GATE
    for k, (cls, lab, tap) in T["item"].items():
        if k in res or ("cu" + k) in L["dropped"] or L["split"][k] != "check": continue
        if time.time() - T0 > LIM: break
        im = cv2.imread(f"/workspace/work/g9g/cu/img/cu{k}.jpg"); H, W = im.shape[:2]; bg = (cv2.GaussianBlur(im, (0, 0), 25) * 0.5).astype(np.uint8)
        tr = IouTracker(); hits = collections.Counter(); g = GradeGate(P); ev = []; t_id = t_gr = None; grade = None; lat = []; idc = None
        for f in range(20):
            s = 0.2 + 0.8 * f / 19; fw, fh = max(8, round(W * s)), max(8, round(H * s)); fr = bg.copy(); x0, y0 = (W - fw) // 2, (H - fh) // 2
            fr[y0:y0 + fh, x0:x0 + fw] = cv2.resize(im, (fw, fh), interpolation=cv2.INTER_AREA)
            tm = {}; t1 = time.perf_counter(); dets = detect(fr); tm["detect"] = (time.perf_counter() - t1) * 1e3
            ts = tr.update([dict(box=b, classId=c, score=sc) for b, c, sc in dets], f * 1000 / 15)
            for t in ts: hits[t["id"]] += 1
            tapx, tapy = (x0 + tap[0] * fw) / W, (y0 + tap[1] * fh) / H
            ident = [t for t in ts if id_policy(t["label"], t["score"], hits[t["id"]])["status"] == "identified"]
            r = roi_from_tap([tapx, tapy], W, H, [t["box"] for t in ident])
            if r["source"] == "track":
                t = next(t for t in ident if t["box"] == r["box"]); idc = N[t["label"]]; t_id = t_id if t_id is not None else f
                a = assess_crop(fr, r["box"], idc, P, tm); dec = g.push(a)
            else:
                # tracking fragmented / not identified: the user ROI is captured, but no name and no grade without identification
                dec = dict(status="unable_to_identify"); g.reset()
            tm["total"] = (time.perf_counter() - t1) * 1e3; lat.append(tm); ev.append(dec["status"])
            if dec["status"] == "graded" and grade is None: grade = dec["grade"]; t_gr = f
        res[k] = dict(cls=cls, label=lab, id_class=idc, id_correct=idc == cls if idc else None, t_id_frame=t_id, t_grade_frame=t_gr, grade=grade, events=ev, lat=lat,
                      price=graded_price(idc is not None, idc or cls, grade, PRICES, TODAY))
        json.dump(res, open(p, "w")); print(k, cls, idc, t_id, t_gr, grade, flush=True)

def negatives():
    T = json.load(open(f"{B}/cu_triage.json")); L = json.load(open(f"{B}/out/cu_leak_split.json")); p = f"{B}/out/e2e_negatives.json"
    res = json.load(open(p)) if os.path.exists(p) else {}; P = FROZEN_GATE
    for grp in ("unsupported", "printed_or_art", "grayscale_photo", "processed_cut", "crowd"):
        for k in T[grp]:
            if k in res or ("cu" + k) in L["dropped"]: continue
            if time.time() - T0 > LIM: break
            im = cv2.imread(f"/workspace/work/g9g/cu/img/cu{k}.jpg"); H, W = im.shape[:2]; dets = detect(im)
            ident = [(b, c, s) for b, c, s in dets if id_policy(c, s, 3)["status"] == "identified"]
            r = roi_from_tap([0.5, 0.5], W, H, [b for b, _, _ in ident]); out = dict(group=grp, g3=[[N[c], round(s, 3)] for _, c, s in dets], identified=[N[c] for _, c, _ in ident])
            if r["source"] == "track":
                b, c, s = next(x for x in ident if x[0] == r["box"]); a = assess_crop(im, b, N[c], P, {}); out.update(tap_id=N[c], single_frame_ok=a["ok"], grade=a["grade"] if a["ok"] else None, reasons=a["reasons"])
            else: out.update(tap_id=None, single_frame_ok=False, grade=None, reasons=["unable_to_identify"])
            res[k] = out
    json.dump(res, open(p, "w")); print("negatives", len(res))


def summary():
    A = json.load(open(f"{B}/out/e2e_approach.json")); NG = json.load(open(f"{B}/out/e2e_negatives.json")); CC = json.load(open(f"{B}/out/e2e_closeup_clip.json"))
    W = json.load(open(f"{B}/out/e2e_wide.json")); MD = json.load(open(f"{B}/out/e2e_mdev.json")); FE = json.load(open(f"{B}/out/feasibility.json"))
    T = json.load(open(f"{B}/cu_triage.json")); L = json.load(open(f"{B}/out/cu_leak_split.json"))
    pct = lambda v: dict(p50=round(float(np.percentile(v, 50)), 1), p95=round(float(np.percentile(v, 95)), 1), n=len(v)) if v else None
    # approach (CU-check, simulated move-closer)
    n = len(A); idd = [v for v in A.values() if v["id_class"]]; corr = [v for v in idd if v["id_correct"]]; gr = [v for v in A.values() if v["grade"]]
    gr_ok_id = [v for v in gr if v["id_correct"]]
    lab_ok = [v for v in gr if (v["grade"] in ("A", "B")) == (v["label"] == "f")]
    stages = collections.defaultdict(list); tot_closeup = []; tot_frame = []
    for v in A.values():
        for tm in v["lat"]:
            for k, x in tm.items(): stages[k].append(x)
            tot_frame.append(tm["total"])
            if "condition" in tm: tot_closeup.append(sum(tm.get(k, 0) for k in ("crop", "condition", "measure", "ripeness", "rules", "checks")))
    for s in CC["segments"]:
        for tm in s["lat"]:
            for k, x in tm.items(): stages["clip_" + k].append(x)
            if "condition" in tm: tot_closeup.append(sum(tm.get(k, 0) for k in ("crop", "condition", "measure", "ripeness", "rules", "checks")))
    approach = dict(items=n, missing_check_items=sorted(k for k, v in L["split"].items() if v == "check" and k not in A), identified=len(idd), id_correct=len(corr),
                    id_accuracy_of_identified=round(len(corr) / len(idd), 3) if idd else None, unable_to_identify=n - len(idd),
                    graded=len(gr), graded_with_correct_id=len(gr_ok_id), graded_on_wrong_id=len(gr) - len(gr_ok_id),
                    grade_band_matches_fresh_rotten_label=f"{len(lab_ok)}/{len(gr)}", grades=collections.Counter(v["grade"] for v in gr),
                    time_to_id_ms=pct([v["t_id_frame"] * 1000 / 15 for v in idd if v["t_id_frame"] is not None]),
                    time_to_grade_ms=pct([v["t_grade_frame"] * 1000 / 15 for v in gr]),
                    id_to_grade_ms=pct([(v["t_grade_frame"] - v["t_id_frame"]) * 1000 / 15 for v in gr]),
                    gate_acceptance_identified=round(len(gr) / len(idd), 3) if idd else None,
                    price_shown=sum(v["price"]["show"] for v in A.values()), price_kinds=collections.Counter(v["price"]["line"]["kind"] if v["price"]["show"] else v["price"]["reason"] for v in A.values()))
    segs = CC["segments"]; g_segs = [s for s in segs if s["grades"]]; flips = sum(sum(a != b for a, b in zip(s["grades"], s["grades"][1:])) for s in segs); pairs = sum(max(0, len(s["grades"]) - 1) for s in segs)
    clip = dict(segments=len(segs), identified=sum(s["tap_frame"] is not None for s in segs), graded=len(g_segs),
                grade_band_matches_dataset_label=f"{sum((s['grades'][0] in ('A','B')) == (s['label']=='fresh') for s in g_segs)}/{len(g_segs)}",
                consecutive_grade_flips=f"{flips}/{pairs}", time_to_id_ms=pct([s["id_frame_ms"] for s in segs if s["id_frame_ms"] is not None]),
                time_to_grade_ms=pct([s["grade_ms"] for s in g_segs]), not_graded_assessments=sum(e == "not_graded" for s in segs for e in s["events"]),
                assessments=sum(e in ("not_graded", "pending", "graded") for s in segs for e in s["events"]))
    grp = collections.defaultdict(lambda: dict(n=0, identified=0, graded=0))
    for k, v in NG.items():
        g = grp[v["group"]]; g["n"] += 1; g["identified"] += bool(v["tap_id"]); g["graded"] += bool(v["grade"])
    negs = {k: dict(v, abstention=round(1 - v["graded"] / v["n"], 3)) for k, v in grp.items()}
    unsup = [g for k, g in negs.items() if k != "crowd"]; un_n = sum(g["n"] for g in unsup); un_g = sum(g["graded"] for g in unsup)
    fc = FE["check_degraded_emission"]
    deg = dict(partial_truncation_emitted=fc["emitted_by_condition"].get("truncation"), poor_light_emitted=fc["emitted_by_condition"].get("lowlight"))
    out = dict(versions=VERSIONS, frozen_gate=FROZEN_GATE, wide=W, mdev=MD, approach_cu_check=approach, closeup_quality_clip=clip, negatives=negs,
               abstention_unsupported_printed_gray_processed=dict(n=un_n, graded=un_g, rate=round(1 - un_g / un_n, 3)),
               degraded_suite_check=fc, degraded_suite_default_checks=FE["check_degraded_emission_default_checks"],
               latency_ms={k: pct(v) for k, v in stages.items()}, closeup_path_ms=pct(tot_closeup), approach_frame_total_ms=pct(tot_frame),
               note="sandbox 2 vCPU, ONNX Runtime FP32, Python; frames 15 fps simulated. Not phone FPS.")
    json.dump(out, open(f"{B}/out/e2e.json", "w"), indent=1); print(json.dumps({k: out[k] for k in ("approach_cu_check", "closeup_quality_clip", "negatives", "abstention_unsupported_printed_gray_processed", "closeup_path_ms", "approach_frame_total_ms")}, indent=0)[:4000])
    print({k: v for k, v in out["latency_ms"].items()})

if __name__ == "__main__":
    m = sys.argv[1]
    if m == "detcache": detcache(sys.argv[2])
    else: globals()[m]()
