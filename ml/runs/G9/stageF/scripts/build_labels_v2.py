"""G9 Stage F P2: M-DEV labels v2 = v1 (ml/runs/G9/stageE/m_labels.json, kept unchanged) + v2 repair ops (no model prediction is used;
only raw images and non-G3 OWLv2 proposals). Region proposals for a crowd region k of image I: OWLv2 dets with class in the 12 classes,
score >= thr (default 0.20), centre inside the region, side < 50% of the region side; class-agnostic NMS 0.4; container boxes (holding
>= 2 other centres) and fragments (> 60% inside a larger box) dropped; all relabelled to the region's class. Numbered in that order.
v2 ops per image (applied in order; coords normalised to the full image):
  ["conv", k, [drop nums], thr]    replace v1 crowd region k by its region proposals minus 'drop nums'
  ["keep", k, "reason"]            keep crowd/ignore region k (documented)
  ["del"|"delc"|"rel"|"crowd"|"ign"|"add", ...]   as in Stage E build_labels.py
  ["dupx", iou]                    drop same-class duplicate boxes with IoU > iou (keep the larger)
New images (M-DEV pool, no v1 labels): {"new": true, "thr":..., "ops": [...]} = Stage E cleanup of whole-image proposals + ops.
Usage: build_labels_v2.py EDITS_V2.json OUT.json"""
import json, sys
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageE/scripts")
import build_labels as BL
V1 = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageE/m_labels.json"))
P = BL.P
def region_props(I, reg, thr=0.20):
    rw, rh = reg[2] - reg[0], reg[3] - reg[1]
    ds = [d["box"] + [reg[4], d["score"]] for d in P[I + ".jpg"]["dets"] if d["cls"] >= 0 and d["score"] >= thr and BL.inr(d["box"], reg)
          and (d["box"][2] - d["box"][0]) < 0.5 * rw and (d["box"][3] - d["box"][1]) < 0.5 * rh]
    ds = [d for d in ds if sum(1 for e in ds if e is not d and BL.inr(e, d)) < 2]
    ds.sort(key=lambda d: -d[5]); out = []
    for d in ds:
        if all(BL.iou(d, e) <= 0.4 for e in out): out.append(d)
    def inter(a, b): return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return [d for d in out if not any(e is not d and BL.area(e) > BL.area(d) and inter(d, e) > 0.6 * BL.area(d) for e in out)]
def apply(bx, cr, ops, I, v1cr):
    log = []
    for op in ops:
        k, a = op[0], op[1:]
        if k == "conv":
            reg = v1cr[a[0]]; drop = set(a[1]) if len(a) > 1 else set(); thr = a[2] if len(a) > 2 else 0.20
            rp = [d[:5] for n, d in enumerate(region_props(I, reg, thr)) if n not in drop]
            cr = [c for c in cr if c != reg]; bx = bx + rp; log.append(f"conv crowd{a[0]} -> {len(rp)} boxes")
        elif k == "convpx":  # region proposals whose centre lies in a tile-pixel sub-rectangle of crowd a[0]; the crowd itself is removed
            reg = v1cr[a[0]]; W, H = P[I + ".jpg"]["w"], P[I + ".jpg"]["h"]; pad = 0.03
            x0, y0 = max(0, reg[0] - pad), max(0, reg[1] - pad); x1, y1 = min(1, reg[2] + pad), min(1, reg[3] + pad)
            cx0, cy0 = int(x0 * W), int(y0 * H); sc = min(880 / (int(x1 * W) - cx0), 660 / (int(y1 * H) - cy0)); q = a[1]
            sub = [(q[0] / sc + cx0) / W, (q[1] / sc + cy0) / H, (q[2] / sc + cx0) / W, (q[3] / sc + cy0) / H]
            drop = set(a[2]) if len(a) > 2 else set()
            rp = [d[:5] for n, d in enumerate(region_props(I, reg)) if n not in drop and BL.inr(d, sub)]
            cr = [c for c in cr if c != reg]; bx = bx + rp; log.append(f"convpx crowd{a[0]} -> {len(rp)} boxes")
        elif k == "delsmallpx":  # drop boxes centred in v1 region a[0] whose geometric-mean side < a[1] native px (slat fragments, <50% visible)
            reg = v1cr[a[0]]; W, H = P[I + ".jpg"]["w"], P[I + ".jpg"]["h"]; n0 = len(bx)
            bx = [b for b in bx if not (BL.inr(b, reg) and ((b[2] - b[0]) * W * (b[3] - b[1]) * H) ** .5 < a[1])]; log.append(f"delsmallpx {n0 - len(bx)}")
        elif k == "recrowd":  # re-add v1 region a[0] as a residual crowd behind proposal-based boxes (unboxed members stay ignored)
            if v1cr[a[0]] not in cr: cr = cr + [list(v1cr[a[0]])]
            log.append(f"recrowd {a[0]}")
        elif k == "keep": log.append(f"keep crowd{a[0]}: {a[1]}")
        elif k in ("addpx", "ignpx", "crowdpx"):  # boxes in review-tile pixel coords of v1 crowd region a[0] (crowd_sheet.py geometry)
            reg = v1cr[a[0]]; W, H = P[I + ".jpg"]["w"], P[I + ".jpg"]["h"]; pad = 0.03
            x0, y0 = max(0, reg[0] - pad), max(0, reg[1] - pad); x1, y1 = min(1, reg[2] + pad), min(1, reg[3] + pad)
            cx0, cy0 = int(x0 * W), int(y0 * H); sc = min(880 / (int(x1 * W) - cx0), 660 / (int(y1 * H) - cy0))
            for q in a[1]:
                b = [(q[0] / sc + cx0) / W, (q[1] / sc + cy0) / H, (q[2] / sc + cx0) / W, (q[3] / sc + cy0) / H]
                b = [min(1, max(0, v)) for v in b]
                if k == "addpx": bx = bx + [b + [q[4] if len(q) > 4 else reg[4]]]
                elif k == "ignpx": cr = cr + [b + [-1]]
                else: cr = cr + [b + [q[4] if len(q) > 4 else reg[4]]]
            log.append(f"{k} crowd{a[0]} {len(a[1])}")
        elif k == "dupx":
            bx = sorted(bx, key=lambda b: -BL.area(b)); o = []
            for b in bx:
                if all(not (b[4] == e[4] and BL.iou(b, e) > a[0]) for e in o): o.append(b)
            log.append(f"dupx removed {len(bx) - len(o)}"); bx = o
        elif k == "del": bx = [b for b in bx if not BL.inr(b, a[:4])]
        elif k == "delc": bx = [b for b in bx if not (BL.inr(b, a[:4]) and b[4] == a[4])]
        elif k == "rel": bx = [b[:4] + [a[5]] if BL.inr(b, a[:4]) and (a[4] == -1 or b[4] == a[4]) else b for b in bx]
        elif k == "crowd": cr = cr + [list(a[:4]) + [a[4]]]; bx = [b for b in bx if not (BL.inr(b, a[:4]) and b[4] == a[4])]
        elif k == "crowdk": cr = cr + [list(a[:4]) + [a[4]]]  # residual crowd behind boxes (boxes kept)
        elif k == "ign": cr = cr + [list(a[:4]) + [-1]]; bx = [b for b in bx if not BL.inr(b, a[:4])]
        elif k == "add": bx = bx + [list(a[:4]) + [a[4]]]
        elif k == "uncrowd": cr = [c for c in cr if not (BL.inr(c, a[:4]))]
    return bx, cr, log
if __name__ == "__main__":
    E = json.load(open(sys.argv[1])); E = E.get("edits", E); out = {}
    for I in sorted(set(V1) | set(E)):
        e = E.get(I, {})
        if e.get("new"):
            if e.get("neg"): out[I] = dict(status="ok", negative=True, note=e.get("note", ""), boxes=[], crowd=[], v2_new=True); continue
            if e.get("status") == "rejected": out[I] = dict(status="rejected", note=e.get("note", ""), boxes=[], crowd=[], v2_new=True); continue
            bx = [d[:5] for d in BL.clean(I, e.get("thr", 0.25))]; cr = []; v1cr = []
        else:
            v = V1[I]; bx = [list(b) for b in v["boxes"]]; cr = [list(c) for c in v.get("crowd", [])]; v1cr = [list(c) for c in cr]
            if v.get("status") == "rejected": out[I] = dict(v); continue
        bx, cr, log = apply(bx, cr, e.get("ops", []), I, v1cr)
        out[I] = dict(status="ok", negative=(not bx and not cr) and (e.get("neg") or V1.get(I, {}).get("negative", False)), note=e.get("note", V1.get(I, {}).get("note", "")),
                      v2_log=log, v2_new=bool(e.get("new")), boxes=[[round(v, 5) for v in b[:4]] + [int(b[4])] for b in bx], crowd=[[round(v, 5) for v in c[:4]] + [int(c[4])] for c in cr])
    json.dump(out, open(sys.argv[2], "w"), indent=0)
    print(len(out), "images,", sum(len(v["boxes"]) for v in out.values()), "boxes,", sum(len(v["crowd"]) for v in out.values()), "crowd/ignore")
