"""G7 Phase 3, stage 3: merge G3+ByteTrack (stage 1, sandbox) with OWLv2 (stage 2, Kaggle) on keyframes -> PROPOSED labels,
disagreement flags, prioritised human-review queue and contact sheets. Nothing produced here is ground truth.

Per keyframe, G3 boxes (score >= 0.10, from frames.json at that frame) and OWLv2 boxes (score >= 0.10, supported-class prompts;
"other" prompts kept only to flag unsupported objects) are matched class-agnostically (greedy, IoU >= 0.5).
Per proposed box:
  status  agree            both models, same class
          class_dispute    both models, different class            -> label "disputed:<g3>|<owl>"
          g3_only          G3 only (OWLv2 missed)                  -> kept only if G3 score >= 0.35
          owl_only         OWLv2 only (possible G3 miss)           -> kept only if OWLv2 score >= 0.25
  flags   low_conf (max score < 0.35), small_box (shorter side < 12 px at the 480 scale; < 6 px = below the G6 small6 view),
          temporal (the ByteTrack track covering the box changed label within +-1 s or lived < 1 s), id_change (track id differs
          from the id that covered the same region on the previous keyframe), unsupported_overlap (an OWLv2 'other' box IoU >= 0.5).
The proposal never takes the max-confidence class silently: a dispute stays a dispute until a human resolves it.
Keyframe priority (review queue) = 3*disputes + 2*owl_only + temporal + id_change + 0.5*small + 0.5*low_conf; negatives: any
supported box >= 0.35 (G3) or >= 0.3 (OWLv2) makes the frame an absence-check item. Queue = top 4 keyframes per clip, then
global top --queue (default 60). Contact sheet per queued item: previous sampled frame / keyframe / next sampled frame with
G3 (green) and OWLv2 (blue) boxes.
  python ml/autolabel/merge.py --stage1 DIR --owl owlv2_keyframes.json --roles roles.json --clips c1=path ... --out OUT
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os

import cv2
import numpy as np

NAMES = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - i
    return i / u if u > 0 else 0.0


def match(A, B, thr=0.5):
    pairs = sorted(((iou(a["box"], b["box"]), i, j) for i, a in enumerate(A) for j, b in enumerate(B)), reverse=True)
    ua, ub, m = set(), set(), []
    for v, i, j in pairs:
        if v < thr:
            break
        if i in ua or j in ub:
            continue
        ua.add(i); ub.add(j); m.append((i, j))
    return m, ua, ub


def nms(d, thr=0.5):
    keep = []
    for x in sorted(d, key=lambda z: -z["score"]):
        if all(iou(k["box"], x["box"]) < thr or k["cls"] != x["cls"] for k in keep):
            keep.append(x)
    return keep


def merge_clip(cid, s1dir, owl, role):
    F = json.load(open(f"{s1dir}/{cid}/frames.json")); K = json.load(open(f"{s1dir}/{cid}/keyframes.json"))["keyframes"]
    W, H = F["w"], F["h"]; s480 = 480 / max(W, H); frames = F["frames"]; by_fi = {f["fi"]: k for k, f in enumerate(frames)}
    track_hist = {}
    for f in frames:
        for t in f["tracks"]:
            track_hist.setdefault(t["id"], []).append((f["t"], t["label"]))
    out, prev_cover = [], []
    for kf in K:
        k = by_fi[kf["fi"]]; fr = frames[k]
        g3 = [dict(box=d["box"], cls=d["classId"], score=d["score"]) for d in fr["dets"] if d["score"] >= 0.10]
        ow_all = owl.get(kf["file"], None)
        ow = nms([d for d in (ow_all or []) if d["cls"] >= 0 and d["score"] >= 0.10])
        other = [d for d in (ow_all or []) if d["cls"] < 0 and d["score"] >= 0.15]
        m, ua, ub = match(g3, ow)
        boxes = []
        for i, j in m:
            a, b = g3[i], ow[j]
            boxes.append(dict(box=a["box"], status="agree" if a["cls"] == b["cls"] else "class_dispute",
                              label=NAMES[a["cls"]] if a["cls"] == b["cls"] else f"disputed:{NAMES[a['cls']]}|{NAMES[b['cls']]}",
                              g3=[NAMES[a["cls"]], a["score"]], owl=[NAMES[b["cls"]], b["score"], b["prompt"]]))
        for i, a in enumerate(g3):
            if i not in ua and a["score"] >= 0.35:
                boxes.append(dict(box=a["box"], status="g3_only", label=NAMES[a["cls"]], g3=[NAMES[a["cls"]], a["score"]], owl=None))
        for j, b in enumerate(ow):
            if j not in ub and b["score"] >= 0.25:
                boxes.append(dict(box=b["box"], status="owl_only", label=NAMES[b["cls"]], g3=None, owl=[NAMES[b["cls"]], b["score"], b["prompt"]]))
        cover = []
        for bx in boxes:
            fl = []
            sc = max((bx["g3"] or [0, 0])[1], (bx["owl"] or [0, 0])[1])
            if sc < 0.35:
                fl.append("low_conf")
            side = min(bx["box"][2] - bx["box"][0], (bx["box"][3] - bx["box"][1]) * H / W) * W * s480
            if side < 12:
                fl.append("small_box_lt6" if side < 6 else "small_box_6_12")
            tr = max(fr["tracks"], key=lambda t: iou(t["box"], bx["box"]), default=None)
            if tr is not None and iou(tr["box"], bx["box"]) >= 0.5:
                h = [l for t, l in track_hist[tr["id"]] if abs(t - fr["t"]) <= 1.0]
                life = track_hist[tr["id"]][-1][0] - track_hist[tr["id"]][0][0]
                if len(set(h)) > 1 or life < 1.0:
                    fl.append("temporal")
                pc = max(prev_cover, key=lambda c: iou(c[1], bx["box"]), default=None)
                if pc is not None and iou(pc[1], bx["box"]) >= 0.3 and pc[0] != tr["id"]:
                    fl.append("id_change")
                cover.append((tr["id"], bx["box"])); bx["track_id"] = tr["id"]
            if any(iou(o["box"], bx["box"]) >= 0.5 for o in other):
                fl.append("unsupported_overlap")
            bx["flags"] = fl
        prev_cover = cover or prev_cover
        st = [b["status"] for b in boxes]; fls = [f for b in boxes for f in b["flags"]]
        if role == "negative":
            hits = [b for b in boxes if ((b["g3"] or [0, 0])[1] >= 0.35) or ((b["owl"] or [0, 0])[1] >= 0.3)]
            pr = 2.0 * len(hits)
        else:
            pr = 3 * st.count("class_dispute") + 2 * st.count("owl_only") + fls.count("temporal") + fls.count("id_change") + 0.5 * (fls.count("small_box_lt6") + fls.count("small_box_6_12")) + 0.5 * fls.count("low_conf")
        out.append(dict(file=kf["file"], fi=kf["fi"], t=kf["t"], owl_available=ow_all is not None, boxes=boxes, priority=round(pr, 2),
                        unsupported_objects=sorted({o["prompt"] for o in other})))
    return dict(clip=cid, role=role, w=W, h=H, n_sampled_frames=len(frames), keyframes=out)


def sheet(video, rec, kf, out_path, step_fi):
    cap = cv2.VideoCapture(video); ims = []
    for fi in (max(0, kf["fi"] - step_fi), kf["fi"], kf["fi"] + step_fi):
        cap.set(cv2.CAP_PROP_POS_FRAMES, fi); ok, im = cap.read()
        if not ok:
            im = np.zeros((360, 640, 3), np.uint8)
        im = cv2.resize(im, (640, int(640 * im.shape[0] / im.shape[1])))
        if fi == kf["fi"]:
            h, w = im.shape[:2]
            for b in kf["boxes"]:
                x1, y1, x2, y2 = [int(v * s) for v, s in zip(b["box"], (w, h, w, h))]
                col = (0, 200, 0) if b["status"] == "agree" else (0, 0, 255) if b["status"] == "class_dispute" else (255, 120, 0) if b["status"] == "owl_only" else (0, 220, 220)
                cv2.rectangle(im, (x1, y1), (x2, y2), col, 2); cv2.putText(im, b["label"][:28], (x1, max(12, y1 - 3)), cv2.FONT_HERSHEY_SIMPLEX, 0.4, col, 1)
        cv2.putText(im, f"{rec['clip']} fi={fi}" + (" KEY" if fi == kf["fi"] else ""), (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        ims.append(im)
    hmax = max(i.shape[0] for i in ims); ims = [cv2.copyMakeBorder(i, 0, hmax - i.shape[0], 0, 0, cv2.BORDER_CONSTANT) for i in ims]
    cv2.imwrite(out_path, np.hstack(ims), [cv2.IMWRITE_JPEG_QUALITY, 80])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1", required=True); ap.add_argument("--owl", required=True); ap.add_argument("--roles", required=True)
    ap.add_argument("--videos", nargs="+", required=True, help="dirs holding <clip>.webm"); ap.add_argument("--out", required=True)
    ap.add_argument("--queue", type=int, default=60); ap.add_argument("--sheets", type=int, default=60)
    a = ap.parse_args()
    owl = json.load(open(a.owl))["clips"]; roles = json.load(open(a.roles))
    os.makedirs(f"{a.out}/proposals", exist_ok=True); os.makedirs(f"{a.out}/sheets", exist_ok=True)
    recs, summ = [], dict(clips=0, keyframes=0, keyframes_with_owl=0, boxes=0, status={}, flags={}, verified_boxes=0)
    for d in sorted(glob.glob(f"{a.stage1}/*/keyframes.json")):
        cid = d.split("/")[-2]; role = roles.get(cid, "unknown")
        if role in ("reject",):
            continue
        r = merge_clip(cid, a.stage1, owl.get(cid, {}), role); recs.append(r)
        json.dump(r, open(f"{a.out}/proposals/{cid}.json", "w"))
        summ["clips"] += 1; summ["keyframes"] += len(r["keyframes"]); summ["keyframes_with_owl"] += sum(k["owl_available"] for k in r["keyframes"])
        for k in r["keyframes"]:
            for b in k["boxes"]:
                summ["boxes"] += 1; summ["status"][b["status"]] = summ["status"].get(b["status"], 0) + 1
                for f in b["flags"]:
                    summ["flags"][f] = summ["flags"].get(f, 0) + 1
    cand = []
    for r in recs:
        top = sorted([k for k in r["keyframes"] if k["priority"] > 0], key=lambda k: -k["priority"])[:4]
        cand += [(k["priority"], r, k) for k in top]
    cand.sort(key=lambda z: -z[0]); q = cand[:a.queue]
    with open(f"{a.out}/review_queue.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(["rank", "clip", "role", "keyframe", "t_s", "priority", "n_boxes", "disputes", "owl_only", "flags", "sheet", "verified_by", "verdict"])
        for i, (p, r, k) in enumerate(q):
            sh = f"sheets/{i:03d}_{r['clip']}_{k['fi']}.jpg"
            st = [b["status"] for b in k["boxes"]]
            w.writerow([i, r["clip"], r["role"], k["file"], k["t"], p, len(k["boxes"]), st.count("class_dispute"), st.count("owl_only"),
                        ";".join(sorted({f for b in k["boxes"] for f in b["flags"]})), sh, "", ""])
            if i < a.sheets:
                vid = next((p_ for dd in a.videos for p_ in glob.glob(f"{dd}/{r['clip']}.*")), None)
                if vid:
                    step = max(1, int(round((k["fi"] / max(k["t"], 1e-6)) / 4))) if k["t"] > 0 else 6
                    sheet(vid, r, k, f"{a.out}/{sh}", step)
    neg = {r["clip"]: sum(1 for k in r["keyframes"] if k["priority"] > 0) for r in recs if r["role"] == "negative"}
    summ.update(review_queue=len(q), negatives_frames_needing_absence_check=neg,
                note="PROPOSED labels only; verified_boxes counts human-verified boxes (0 unless review_queue.csv verdicts are filled by a person).")
    json.dump(summ, open(f"{a.out}/summary.json", "w"), indent=1); print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
