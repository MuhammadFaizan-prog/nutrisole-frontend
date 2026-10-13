"""G9 existing-models arm (addendum 2026-10-14 02:19 PKT): RAW-detector scoring and offline TRACKED replay from the raw dumps,
identical frames (synthetic DEV clips, fixed-frame stride 2), identical IoU (0.5) and identical GT for every model.

Pre-registered (written before any candidate synthetic result was looked at):
  * Raw, per processed frame with a GT primary object (harness primary(): largest GT box of the segment class):
      correct    = some box IoU>=0.5 with the primary object and the right class
      wrong      = no correct box, but some box IoU>=0.5 with it carrying another class   (wrong-class prediction)
      missing    = no box IoU>=0.5 at all                                                   (missed object)
      uncovered  = GT class not in the model's class map (counted as missing-by-design, reported separately)
    wrong-class DETECTIONS = every box (any frame) that overlaps a GT object (IoU>=0.5) with a different class, and no same-class GT.
    background boxes = boxes overlapping no GT object (IoU<0.5 to all) on the det clip.
    neg clip: raw false boxes per minute (all boxes are false), frames with any box.
  * DEV threshold rule (per model, G3 included): the conf in {0.10,0.15,...,0.90} maximising raw correct-frame rate on the det clip
    subject to raw neg false boxes/min <= G3's raw neg false boxes/min at its production threshold 0.35. Ties -> higher conf.
    If no threshold meets the constraint, the model is reported at its lowest-FA threshold and flagged.
  * Tracked = same raw boxes >= conf -> scene_guard(minArea 0.01, rule 2 off) -> IouTracker (default params) -> harness metrics().
    Promotion needs recall to hold: lower FA alone never wins.
"""
from __future__ import annotations

import collections
import gzip
import json
import os
import sys

import numpy as np

H = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(H, "../../../.."))
sys.path.insert(0, os.path.join(REPO, "ml/eval")); sys.path.insert(0, os.path.join(REPO, "ml"))
from video_gauntlet import metrics, primary, NAMES  # noqa: E402
from tracker import IouTracker, iou  # noqa: E402
from scene_guard import scene_guard  # noqa: E402
from roboflow_adapter import coverage  # noqa: E402

CLIPS = "/workspace/work/cv/g3clips_dev"
MODELS = ["g3", "snapml", "calories"]
THRS = [round(x, 2) for x in np.arange(0.10, 0.901, 0.05)]
COVER = {"g3": set(NAMES), "snapml": set(coverage("snapml")["mapped"]), "calories": set(coverage("calories")["mapped"])}


def load_dump(m, kind):
    for p in (f"{H}/gauntlet_dev/{m}_{kind}/raw_dets_{kind}.json.gz", f"{H}/gauntlet_dev/raw_{m}_{kind}/raw_dets_{kind}.json.gz"):
        if os.path.exists(p):
            d = json.load(gzip.open(p, "rt"))
            return {int(k): v for k, v in d["frames"].items()}, p
    return None, None


def raw_det(gt, dump, thr, m):
    st = collections.Counter(); st_cls = collections.defaultdict(collections.Counter); small = collections.Counter()
    wrong_dets = collections.Counter(); bg = 0; nproc = 0
    seg_of = {}
    for si, s in enumerate(gt["segments"]):
        for fi in range(s["start"], s["end"] + 1):
            seg_of[fi] = s
    for fi, boxes in dump.items():
        nproc += 1
        fr = gt["frames"][fi]
        bx = [b for b in boxes if b[1] >= thr]
        objs = fr["objects"]
        for b in bx:
            ious = [(iou(b[2:], o["box_norm"]), o["cls"]) for o in objs]
            hit = [c for v, c in ious if v >= 0.5]
            if not hit:
                bg += 1
            elif b[0] not in hit:
                wrong_dets[f"{NAMES[hit[0]]}->{NAMES[b[0]]}"] += 1
        s = seg_of.get(fi)
        if s is None:
            continue
        p = primary([o for o in objs if o["cls"] == s["cls"]]) or primary(objs)
        if p is None:
            continue
        ov = [b for b in bx if iou(b[2:], p["box_norm"]) >= 0.5]
        cname = NAMES[p["cls"]]
        if any(b[0] == p["cls"] for b in ov):
            r = "correct"
        elif ov:
            r = "wrong"
        else:
            r = "missing"
        if cname not in COVER[m]:
            r = r if r == "wrong" else "uncovered"
        st[r] += 1; st_cls[cname][r] += 1
        bb = p["box_norm"]
        if (bb[2] - bb[0]) * (bb[3] - bb[1]) < 0.02:
            small[r] += 1
    n = sum(st.values()); ncov = n - st["uncovered"]
    return dict(thr=thr, frames_scored=n, processed=nproc, correct=st["correct"], wrong=st["wrong"], missing=st["missing"], uncovered=st["uncovered"],
                correct_rate=round(st["correct"] / max(1, n), 4), correct_rate_covered=round(st["correct"] / max(1, ncov), 4),
                wrong_rate=round(st["wrong"] / max(1, n), 4), wrong_class_detections=sum(wrong_dets.values()), wrong_pairs=dict(wrong_dets.most_common(12)),
                background_boxes=bg, small_objects=dict(small), per_class={c: dict(v) for c, v in st_cls.items()})


def raw_neg(gt, dump, thr):
    minutes = len(gt["frames"]) / gt["fps"] / 60
    nb, fa, per = 0, 0, collections.Counter()
    seg_src = collections.Counter()
    seg_of = {fi: s["src"] for s in gt["segments"] for fi in range(s["start"], s["end"] + 1)}
    for fi, boxes in dump.items():
        bx = [b for b in boxes if b[1] >= thr]
        nb += len(bx); fa += bool(bx)
        for b in bx:
            per[NAMES[b[0]]] += 1
            seg_src[seg_of.get(fi, "?")] += 1
    return dict(thr=thr, false_boxes=nb, false_boxes_per_min=round(nb / minutes, 2), frames_with_box=fa, processed=len(dump),
                frac_frames_with_box=round(fa / max(1, len(dump)), 4), per_class=dict(per), by_source=dict(seg_src))


def tracked(gt, dump, thr, kind):
    trk = IouTracker(); shown, display = [], []
    for fi, fr in enumerate(gt["frames"]):
        if fi in dump:
            dets = [dict(box=b[2:], classId=b[0], score=b[1]) for b in dump[fi] if b[1] >= thr]
            dets = [d for d in dets if (d["box"][2] - d["box"][0]) * gt["w"] >= 2 and (d["box"][3] - d["box"][1]) * gt["h"] >= 2]
            dets = scene_guard(dets, maxSameClass=0, minAreaFrac=0.01)
            if fr.get("reset"):
                trk.reset()
            display = [dict(id=t["id"], box=t["box"], label=t["label"], score=t["score"], grade=None, level=None, reasons=None) for t in trk.update(dets, fr["t_ms"])]
        shown.append(display)
    r = metrics(gt, shown, kind)
    r.pop("segments_detail", None)
    return r


def main():
    gdet = json.load(open(f"{CLIPS}/det_clip.json")); gneg = json.load(open(f"{CLIPS}/neg_clip.json"))
    out = dict(rule=__doc__.split("Pre-registered")[1].strip(), models={})
    dumps = {}
    for m in MODELS:
        dd, pd = load_dump(m, "det"); dn, pn = load_dump(m, "neg")
        if dd is None or dn is None:
            out["models"][m] = dict(error="raw dump missing", det=pd, neg=pn); continue
        dumps[m] = (dd, dn)
        out["models"][m] = dict(dump_det=os.path.relpath(pd, H), dump_neg=os.path.relpath(pn, H), coverage=sorted(COVER[m], key=NAMES.index),
                                sweep=[dict(det=raw_det(gdet, dd, t, m), neg=raw_neg(gneg, dn, t)) for t in THRS])
    if "g3" in dumps:
        fa_cap = next(s["neg"]["false_boxes_per_min"] for s in out["models"]["g3"]["sweep"] if s["det"]["thr"] == 0.35)
        out["fa_cap_boxes_per_min"] = fa_cap
        for m in dumps:
            assert set(dumps[m][0]) == set(dumps["g3"][0]) and set(dumps[m][1]) == set(dumps["g3"][1]), f"frame sets differ for {m}"
            sw = out["models"][m]["sweep"]
            ok = [s for s in sw if s["neg"]["false_boxes_per_min"] <= fa_cap]
            if ok:
                best = max(ok, key=lambda s: (s["det"]["correct_rate"], s["det"]["thr"])); flag = None
            else:
                best = min(sw, key=lambda s: (s["neg"]["false_boxes_per_min"], -s["det"]["correct_rate"])); flag = "no threshold meets the FA cap"
            t = best["det"]["thr"]
            out["models"][m].update(tuned_thr=t, tuned_flag=flag,
                                    raw_at_035=next(s for s in sw if s["det"]["thr"] == 0.35), raw_at_tuned=best,
                                    tracked_at_035=dict(det=tracked(gdet, dumps[m][0], 0.35, "det"), neg=tracked(gneg, dumps[m][1], 0.35, "neg")),
                                    tracked_at_tuned=dict(det=tracked(gdet, dumps[m][0], t, "det"), neg=tracked(gneg, dumps[m][1], t, "neg")))
    json.dump(out, open(f"{H}/raw_tracked_dev.json", "w"), indent=1)
    for m, v in out["models"].items():
        if "tuned_thr" in v:
            a, b = v["raw_at_035"], v["raw_at_tuned"]
            print(m, "thr", v["tuned_thr"], v["tuned_flag"], "| raw035", a["det"]["correct_rate"], a["det"]["wrong"], a["det"]["missing"], a["neg"]["false_boxes_per_min"],
                  "| rawT", b["det"]["correct_rate"], b["neg"]["false_boxes_per_min"], "| trk035", v["tracked_at_035"]["det"]["frame_acc"], v["tracked_at_035"]["neg"]["false_alarms_per_min"],
                  "| trkT", v["tracked_at_tuned"]["det"]["frame_acc"], v["tracked_at_tuned"]["det"]["segment_acc"], v["tracked_at_tuned"]["neg"]["false_alarms_per_min"])


if __name__ == "__main__":
    main()
