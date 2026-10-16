"""G8: prioritised ~30-item HUMAN review queue of hard auto-label examples (PROPOSALS, never ground truth).
Quota buckets so crowded stalls don't swamp the queue: lemon/citrus confusion 8, guava 6, small objects 6, G3-vs-OWLv2
disagreement (uncrowded frames, by dispute fraction) 7, negative-clip false hits 3; max 2 keyframes per clip, unique keyframes.
Renders each item with merge.sheet (prev/key/next frame; green agree, red dispute, blue owl_only, yellow g3_only) and stacks
10 per contact-sheet JPG. Low memory: one cv2 capture at a time, 1 thread.
  python g8_hard_queue.py AUTOLABEL_DIR OUT_DIR VIDEO_DIR [VIDEO_DIR...]"""
import csv, glob, json, os, sys
import cv2, numpy as np
cv2.setNumThreads(1)
sys.path.insert(0, "/workspace/work/nutrisole/ml/autolabel"); import merge as M
AL, OUT, VD = sys.argv[1], sys.argv[2], sys.argv[3:]
CIT = {"citrus", "lemon_lime"}
recs = [json.load(open(p)) for p in sorted(glob.glob(f"{AL}/proposals/*.json"))]
def labs(b): return {x[0] for x in (b["g3"], b["owl"]) if x}
def sc(b): return max((b["g3"] or [0, 0])[1], (b["owl"] or [0, 0])[1])
B = {k: [] for k in ("lemon_citrus_confusion", "guava", "small_object", "g3_owl_disagreement", "negative_false_hit")}
for r in recs:
    for k in r["keyframes"]:
        bx = k["boxes"]; key = (r, k)
        if r["role"] == "negative":
            h = [b for b in bx if ((b["g3"] or [0, 0])[1] >= 0.35) or ((b["owl"] or [0, 0])[1] >= 0.3)]
            if h: B["negative_false_hit"].append((max(sc(b) for b in h) + 0.1 * len(h), key, f"{len(h)} confident hits on negative clip"))
            continue
        lc = [b for b in bx if b["status"] == "class_dispute" and labs(b) <= CIT]
        if lc: B["lemon_citrus_confusion"].append((len(lc) + max(sc(b) for b in lc), key, f"{len(lc)} lemon_lime<->citrus disputes"))
        gv = [b for b in bx if "guava" in labs(b) and b["status"] != "agree"]
        if gv: B["guava"].append((len(gv) + max(sc(b) for b in gv), key, f"{len(gv)} guava non-agree ({', '.join(sorted({b['label'] for b in gv}))[:80]})"))
        sm = [b for b in bx if "small_box_lt6" in b["flags"] and sc(b) >= 0.3]
        if sm: B["small_object"].append((len(sm) + max(sc(b) for b in sm), key, f"{len(sm)} confident boxes <6px@480"))
        conf = [b for b in bx if sc(b) >= 0.35]
        if 2 <= len(conf) <= 15:
            d = [b for b in conf if b["status"] in ("class_dispute", "owl_only", "g3_only")]
            if d: B["g3_owl_disagreement"].append((len(d) / len(conf) + 0.05 * len(d), key, f"{len(d)}/{len(conf)} confident boxes disputed/one-model-only"))
Q = dict(lemon_citrus_confusion=8, guava=6, small_object=6, g3_owl_disagreement=7, negative_false_hit=3)
seen, per, sel = set(), {}, []
for cat, n in Q.items():
    got = 0
    for s, (r, k), why in sorted(B[cat], key=lambda z: -z[0]):
        if got >= n: break
        if (r["clip"], k["fi"]) in seen or per.get(r["clip"], 0) >= 2: continue
        seen.add((r["clip"], k["fi"])); per[r["clip"]] = per.get(r["clip"], 0) + 1; sel.append((cat, s, r, k, why)); got += 1
# top-up to 30 from disagreement bucket if a bucket ran short
for s, (r, k), why in sorted(B["g3_owl_disagreement"], key=lambda z: -z[0]):
    if len(sel) >= 30: break
    if (r["clip"], k["fi"]) in seen or per.get(r["clip"], 0) >= 2: continue
    seen.add((r["clip"], k["fi"])); per[r["clip"]] = per.get(r["clip"], 0) + 1; sel.append(("g3_owl_disagreement", s, r, k, why))
os.makedirs(f"{OUT}/items", exist_ok=True)
vids = {os.path.splitext(os.path.basename(p))[0]: p for d in VD for p in glob.glob(f"{d}/*")}
rows_all = []
with open(f"{OUT}/hard_review_queue.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["rank", "category", "clip", "role", "keyframe", "fi", "t_s", "score", "why", "boxes", "sheet", "tile", "verified_by", "verdict"])
    for i, (cat, s, r, k, why) in enumerate(sel):
        p = f"{OUT}/items/{i+1:02d}_{cat}_{r['clip']}_{k['fi']}.jpg"
        if r["clip"] in vids and not os.path.exists(p):
            step = max(1, int(round((k["fi"] / max(k["t"], 1e-6)) / 4))) if k["t"] > 0 else 6
            M.sheet(vids[r["clip"]], r, k, p, step)
        w.writerow([i + 1, cat, r["clip"], r["role"], k["file"], k["fi"], k["t"], round(s, 2), why,
                    "; ".join(f"{b['status']}:{b['label']}" for b in k["boxes"] if sc(b) >= 0.3)[:300], f"review_sheet_{i//10+1}.jpg", i % 10 + 1, "", ""])
        rows_all.append((i, p, cat, why, r["clip"], k["fi"]))
for sn in range(0, len(rows_all), 10):
    rows = []
    for i, p, cat, why, c, fi in rows_all[sn:sn + 10]:
        im = cv2.imread(p)
        if im is None: im = np.zeros((360, 1920, 3), np.uint8)
        h, wd = im.shape[:2]; im = cv2.resize(im, (1200, int(1200 * h / wd)))
        cap = np.full((26, 1200, 3), 30, np.uint8)
        cv2.putText(cap, f"#{i+1} [{cat}] {c} fi={fi}: {why}"[:130], (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        rows.append(np.vstack([cap, im])); del im
    cv2.imwrite(f"{OUT}/review_sheet_{sn//10+1}.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
print(len(sel), {c: sum(1 for z in sel if z[0] == c) for c in Q})
