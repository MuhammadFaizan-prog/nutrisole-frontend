"""Video gauntlet v2: replay clips through the app pipeline with exported (ONNX) models.

Pipeline per processed frame (same conventions as native/src/cv):
  letterbox(imgsz) -> detector (ONNX) -> decode (e2e or raw+NMS) -> map to frame
  -> score >= RUBRIC.detectorMinScore -> IouTracker (hysteresis, resets on new objects)
  -> quality THROTTLE: classifier + measurements + rules only for tracks stable >= stableMs,
     re-graded at most every 1000 ms per track, max 3 tracks per frame.
Asynchronous inference is simulated with dropFramesWhileBusy: a frame that arrives while
the previous one is still being processed (by measured wall time on THIS CPU) is dropped
and the UI keeps showing the last result; results are aligned to completion time.

Metrics (per clip kind):
  frame_acc            frames where the primary GT object is covered by a displayed track
                       (IoU>=0.5) whose label == GT class / frames with a GT object
  per_class_recall     same, per class
  segment_acc          majority displayed label on the primary object over the segment == GT
  ttfc_ms              time from segment start (object starts entering) to first correct
                       displayed label; None if never (counted as failure)
  label_flicker_10s    label changes of the primary object's displayed label per 10 s in the
                       STATIC phase (hand shake only); also reported for all phases
  grade_flicker_10s    grade changes per 10 s per track in static phase (quality clip)
  false_alarms_per_min distinct displayed tracks on negative clips per minute
  latency              det-only and full-pipeline ms p50/p90/p95 (+ FPS) on this CPU
REGRESSION TEST ONLY (synthetic clips from test images) -- not a headline number.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time

import cv2
import numpy as np
import onnxruntime as ort

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from geometry import letterbox, dst_to_src, cls_preprocess, decode  # noqa: E402
from tracker import IouTracker, iou  # noqa: E402
from grading.measure import measure  # noqa: E402
from grading.rules import grade, RUBRIC  # noqa: E402

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
GRADE_COL = {"A": (60, 180, 60), "B": (60, 200, 200), "C": (0, 140, 255), "Reject": (40, 40, 220), "ungradable": (160, 160, 160)}


def sess(p):
    so = ort.SessionOptions()
    so.intra_op_num_threads = 2
    return ort.InferenceSession(p, so, providers=["CPUExecutionProvider"])


def pct(a, q):
    return float(np.percentile(a, q)) if len(a) else None


def run_clip(video, gt, det, det_kind, imgsz, cls, cls_names, cls_imgsz, temp, annotate_path=None, realtime=True):
    cap = cv2.VideoCapture(video)
    fps, W, H = gt["fps"], gt["w"], gt["h"]
    trk = IouTracker()
    di = det.get_inputs()[0].name
    ci = cls.get_inputs()[0].name if cls else None
    vw = cv2.VideoWriter(annotate_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (W, H)) if annotate_path else None
    shown = []          # displayed state per frame (list of tracks with label/grade)
    lat_det, lat_full = [], []
    busy_until = -1.0
    display = []        # current UI state
    pending = None      # (ready_time_ms, state)
    grades = {}         # track id -> dict(grade, reasons, level, last_ms)
    dropped = 0
    for fi, fr in enumerate(gt["frames"]):
        ok, frame = cap.read()
        if not ok:
            break
        t = fr["t_ms"]
        if pending and pending[0] <= t:
            display = pending[1]
            pending = None
        if realtime and t < busy_until:
            dropped += 1
        else:
            t0 = time.perf_counter()
            x, tf = letterbox(frame, imgsz)
            out = det.run(None, {di: x})[0]
            t1 = time.perf_counter()
            dets = []
            for d in decode(out, det_kind, RUBRIC["detectorMinScore"]):
                b = dst_to_src(d["box"], tf)
                if b[2] - b[0] < 2 or b[3] - b[1] < 2:
                    continue
                dets.append(dict(box=[b[0] / W, b[1] / H, b[2] / W, b[3] / H], classId=d["classId"], score=d["score"]))
            if fr.get("reset"):
                trk.reset()
            tracks = trk.update(dets, t)
            n_graded = 0
            alive = {tr.id for tr in trk.tracks}  # internal Track dataclasses (update() returns dicts)
            for k in list(grades):
                if k not in alive:
                    del grades[k]
            for tr in tracks:
                if cls is None or not tr["stable"] or n_graded >= 3:
                    continue
                g = grades.get(tr["id"])
                if g and t - g["last_ms"] < 1000:
                    continue
                bx = tr["box"]
                x1, y1, x2, y2 = bx[0] * W, bx[1] * H, bx[2] * W, bx[3] * H
                pw, ph = 0.05 * (x2 - x1), 0.05 * (y2 - y1)
                crop = frame[int(max(0, y1 - ph)):int(min(H, y2 + ph)), int(max(0, x1 - pw)):int(min(W, x2 + pw))]
                if crop.size == 0 or min(crop.shape[:2]) < 16:
                    continue
                p = cls.run(None, {ci: cls_preprocess(crop, cls_imgsz)})[0][0].astype(np.float64)
                logit = np.log(np.clip(p, 1e-9, 1.0)) / temp
                pc = np.exp(logit - logit.max())
                pc /= pc.sum()
                probs = {n: float(v) for n, v in zip(cls_names, pc)}
                c = crop
                s = 160 / max(c.shape[:2])
                if s < 1:
                    c = cv2.resize(c, (int(c.shape[1] * s), int(c.shape[0] * s)), interpolation=cv2.INTER_AREA)
                m = measure(cv2.cvtColor(c, cv2.COLOR_BGR2RGB), NAMES[tr["label"]]).to_dict()
                gr = grade(NAMES[tr["label"]], tr["score"], probs, m)
                level = max(probs, key=probs.get)
                grades[tr["id"]] = dict(grade=gr["grade"], reasons=gr["reasons"], level=level, probs=probs, last_ms=t)
                n_graded += 1
            t2 = time.perf_counter()
            lat_det.append(1000 * (t1 - t0))
            lat_full.append(1000 * (t2 - t0))
            state = [dict(id=tr["id"], box=tr["box"], label=tr["label"], score=tr["score"],
                          grade=grades.get(tr["id"], {}).get("grade"), level=grades.get(tr["id"], {}).get("level"),
                          reasons=grades.get(tr["id"], {}).get("reasons")) for tr in tracks]
            proc_ms = 1000 * (t2 - t0)
            if realtime:
                busy_until = t + proc_ms
                pending = (t + proc_ms, state)
                if proc_ms <= 0:
                    display, pending = state, None
            else:
                display = state
        shown.append(display)
        if vw is not None:
            vis = frame.copy()
            for o in fr["objects"]:
                b = o["box_norm"]
                cv2.rectangle(vis, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), (255, 255, 255), 1)
            for s_ in display:
                b = s_["box"]
                col = GRADE_COL.get(s_["grade"] or "", (255, 200, 0))
                cv2.rectangle(vis, (int(b[0] * W), int(b[1] * H)), (int(b[2] * W), int(b[3] * H)), col, 2)
                txt = f"#{s_['id']} {NAMES[s_['label']]} {s_['score']:.2f}" + (f" | {s_['grade']}" if s_["grade"] else "")
                cv2.putText(vis, txt, (int(b[0] * W) + 2, max(14, int(b[1] * H) - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
                if s_.get("reasons"):
                    cv2.putText(vis, s_["reasons"][0][:48], (int(b[0] * W) + 2, min(H - 4, int(b[3] * H) + 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1, cv2.LINE_AA)
            hdr = f"t={t/1000:.1f}s seg={fr['segment']} {fr['phase']}  GT: " + ",".join(NAMES[o['cls']] for o in fr["objects"][:3])
            cv2.putText(vis, hdr, (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(vis, "SYNTHETIC REGRESSION CLIP (desktop CPU replay)", (4, H - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
            vw.write(vis)
    if vw is not None:
        vw.release()
    return shown, lat_det, lat_full, dropped


def primary(objs):
    if not objs:
        return None
    return max(objs, key=lambda o: (o["box_norm"][2] - o["box_norm"][0]) * (o["box_norm"][3] - o["box_norm"][1]))


def match(state, gtbox):
    best, bi = None, 0.0
    for s in state:
        v = iou(s["box"], gtbox)
        if v >= 0.5 and v > bi:
            best, bi = s, v
    return best


def metrics(gt, shown, kind):
    fps = gt["fps"]
    res = {}
    if kind == "neg":
        ids = set()
        for st in shown:
            for s in st:
                ids.add(s["id"])
        minutes = len(shown) / fps / 60
        fa_frames = sum(1 for st in shown if st)
        res.update(false_alarm_tracks=len(ids), minutes=round(minutes, 3), false_alarms_per_min=round(len(ids) / minutes, 2),
                   frames_with_any_box=fa_frames, frames=len(shown))
        return res
    n, correct = 0, 0
    pc_n, pc_c = collections.Counter(), collections.Counter()
    seg_rows = []
    for seg in gt["segments"]:
        labels_all, labels_static, ttfc, grades_static = [], [], None, collections.defaultdict(list)
        seg_corr = seg_n = 0
        for fi in range(seg["start"], seg["end"] + 1):
            fr = gt["frames"][fi]
            p = primary([o for o in fr["objects"] if o["cls"] == seg["cls"]]) or primary(fr["objects"])
            if p is None:
                continue
            m = match(shown[fi], p["box_norm"])
            lab = m["label"] if m else None
            ok = lab == p["cls"]
            n += 1
            correct += ok
            seg_n += 1
            seg_corr += ok
            pc_n[p["cls"]] += 1
            pc_c[p["cls"]] += ok
            labels_all.append(lab)
            if fr["phase"] == "static":
                labels_static.append(lab)
                if m and m.get("grade"):
                    grades_static[m["id"]].append(m["grade"])
            if ok and ttfc is None:
                ttfc = fr["t_ms"] - gt["frames"][seg["start"]]["t_ms"]
        maj = collections.Counter([l for l in labels_all if l is not None]).most_common(1)
        maj = maj[0][0] if maj else None

        def changes(seq):
            seq = [s for s in seq if s is not None]
            return sum(1 for a, b in zip(seq, seq[1:]) if a != b)
        static_s = len(labels_static) / fps
        all_s = len(labels_all) / fps
        g_changes = sum(changes(v) for v in grades_static.values())
        seg_rows.append(dict(seg=gt["segments"].index(seg), cls=NAMES[seg["cls"]], quality=seg.get("quality"), frame_acc=round(seg_corr / max(1, seg_n), 3),
                             majority=NAMES[maj] if maj is not None else None, seg_correct=maj == seg["cls"], ttfc_ms=ttfc,
                             label_changes_static=changes(labels_static), static_s=round(static_s, 2), label_changes_all=changes(labels_all), all_s=round(all_s, 2),
                             grade_changes_static=g_changes, static_grades=sorted({g for v in grades_static.values() for g in v}),
                             no_box_frac_static=round(sum(1 for l in labels_static if l is None) / max(1, len(labels_static)), 3)))
    ttfcs = [r["ttfc_ms"] for r in seg_rows if r["ttfc_ms"] is not None]
    st = sum(r["static_s"] for r in seg_rows)
    al = sum(r["all_s"] for r in seg_rows)
    res.update(frames_with_gt=n, frame_acc=round(correct / max(1, n), 4),
               per_class_recall={NAMES[c]: dict(n=pc_n[c], recall=round(pc_c[c] / pc_n[c], 3)) for c in sorted(pc_n)},
               segments=len(seg_rows), segment_acc=round(sum(r["seg_correct"] for r in seg_rows) / max(1, len(seg_rows)), 4),
               never_correct_segments=sum(1 for r in seg_rows if r["ttfc_ms"] is None),
               ttfc_ms=dict(p50=pct(ttfcs, 50), p90=pct(ttfcs, 90), max=max(ttfcs) if ttfcs else None, n=len(ttfcs)),
               label_flicker_per_10s_static=round(10 * sum(r["label_changes_static"] for r in seg_rows) / max(1e-9, st), 3),
               label_flicker_per_10s_all=round(10 * sum(r["label_changes_all"] for r in seg_rows) / max(1e-9, al), 3),
               grade_flicker_per_10s_static=round(10 * sum(r["grade_changes_static"] for r in seg_rows) / max(1e-9, st), 3),
               no_box_frac_static=round(float(np.mean([r["no_box_frac_static"] for r in seg_rows])), 3),
               segments_detail=seg_rows)
    if kind == "quality":
        # quality level on segments where a grade was produced (majority of graded frames)
        qc = qn = 0
        rot_tp = rot_n = 0
        for seg, row in zip(gt["segments"], seg_rows):
            levels = []
            for fi in range(seg["start"], seg["end"] + 1):
                p = primary(gt["frames"][fi]["objects"])
                if p is None:
                    continue
                m = match(shown[fi], p["box_norm"])
                if m and m.get("level"):
                    levels.append(m["level"])
            if levels:
                maj = collections.Counter(levels).most_common(1)[0][0]
                qn += 1
                qc += maj == seg["quality"]
                row["quality_majority"] = maj
            if seg["quality"] == "rotten":
                rot_n += 1
                rot_tp += bool(levels) and collections.Counter(levels).most_common(1)[0][0] == "rotten"
        res.update(quality_segments_graded=qn, quality_segment_acc=round(qc / max(1, qn), 4), rotten_segment_recall=round(rot_tp / max(1, rot_n), 4),
                   rotten_segments=rot_n)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--det", required=True)
    ap.add_argument("--det-kind", choices=["e2e", "raw"], required=True)
    ap.add_argument("--imgsz", type=int, default=320)
    ap.add_argument("--cls", default=None)
    ap.add_argument("--cls-names", default="fresh,rotten")
    ap.add_argument("--cls-imgsz", type=int, default=192)
    ap.add_argument("--temp", type=float, default=1.0)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--annotate", action="store_true")
    ap.add_argument("--no-realtime", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    det = sess(a.det)
    cls = sess(a.cls) if a.cls else None
    report = dict(det=a.det, det_kind=a.det_kind, imgsz=a.imgsz, cls=a.cls, cls_imgsz=a.cls_imgsz, temperature=a.temp,
                  device=f"CPU x{os.cpu_count()} (sandbox), onnxruntime {ort.__version__}, 2 intra-op threads",
                  realtime_drop_frames=not a.no_realtime, tracker_params=IouTracker().p, rubric=RUBRIC["rubricVersion"],
                  disclaimer="Synthetic handheld clips from locked TEST images: regression test, not a headline or phone number.", clips={})
    all_det, all_full = [], []
    for kind in ["det", "quality", "neg"]:
        vp, gp = f"{a.clips}/{kind}_clip.mp4", f"{a.clips}/{kind}_clip.json"
        if not os.path.exists(vp):
            continue
        gt = json.load(open(gp))
        ann = f"{a.out}/{kind}_annotated.mp4" if a.annotate else None
        t0 = time.time()
        shown, ld, lf, dropped = run_clip(vp, gt, det, a.det_kind, a.imgsz, cls, a.cls_names.split(","), a.cls_imgsz, a.temp, ann, not a.no_realtime)
        m = metrics(gt, shown, kind)
        m.update(n_frames=len(shown), processed_frames=len(ld), dropped_frames=dropped, wall_s=round(time.time() - t0, 1),
                 latency_det_ms=dict(p50=pct(ld, 50), p90=pct(ld, 90), p95=pct(ld, 95)),
                 latency_full_ms=dict(p50=pct(lf, 50), p90=pct(lf, 90), p95=pct(lf, 95)),
                 effective_fps=round(1000 / float(np.mean(lf)), 1) if lf else None)
        report["clips"][kind] = m
        all_det += ld
        all_full += lf
        print(kind, json.dumps({k: v for k, v in m.items() if k not in ("segments_detail", "per_class_recall")}), flush=True)
    report["latency_overall"] = dict(det_ms=dict(p50=pct(all_det, 50), p90=pct(all_det, 90), p95=pct(all_det, 95)),
                                     full_ms=dict(p50=pct(all_full, 50), p90=pct(all_full, 90), p95=pct(all_full, 95)),
                                     det_fps=round(1000 / float(np.mean(all_det)), 1) if all_det else None)
    json.dump(report, open(f"{a.out}/gauntlet.json", "w"), indent=1)
    print("wrote", f"{a.out}/gauntlet.json")


if __name__ == "__main__":
    main()
