"""Build M-DEV labels from OWLv2 proposals (non-G3) + agent edits. Proposal cleanup (mechanical, before review): keep 12-class proposals with
score >= thr (default 0.25); drop 'container' boxes that hold the centres of >= 2 other kept boxes of the same class (pile boxes); within-class
NMS 0.4; drop fragment boxes (>60% of the box inside a larger same-class box). Agent edit ops (normalised full-image coords; region ops act on box centres), applied in order:
  ["del", x1,y1,x2,y2]                 delete every box centred in the region
  ["delc", x1,y1,x2,y2, c]             delete boxes of class c centred in the region
  ["rel", x1,y1,x2,y2, c_from|-1, c_to] relabel (c_from -1 = any class)
  ["crowd", x1,y1,x2,y2, c]            add crowd region of class c and delete boxes of class c centred in it
  ["ign", x1,y1,x2,y2]                 ignore region (crowd of class -1: boxes centred in it are deleted; any detection centred in it is ignored)
  ["add", x1,y1,x2,y2, c]              add a box
  ["delid", n, ...]                    delete proposals by sheet number (numbering of the cleaned proposal list)
Status 'ok' or 'rejected' (+ note). Usage: build_labels.py EDITS.json OUT.json"""
import json, sys
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
def area(b): return (b[2] - b[0]) * (b[3] - b[1])
def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1])); i = ix * iy
    return i / (area(a) + area(b) - i + 1e-12)
def ctr(b): return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
def inr(b, r): x, y = ctr(b); return r[0] <= x <= r[2] and r[1] <= y <= r[3]
P = json.load(open("/workspace/work/cv/g9e/owl_props.json"))["images"]
def clean(i, thr):
    ds = [d["box"] + [d["cls"], d["score"]] for d in P[i + ".jpg"]["dets"] if d["cls"] >= 0 and d["score"] >= thr]
    keep = []
    for d in ds:
        inner = [e for e in ds if e is not d and e[4] == d[4] and inr(e, d) and area(e) < 0.5 * area(d)]
        if len(inner) < 2: keep.append(d)
    keep.sort(key=lambda d: -d[5]); out = []
    for d in keep:
        if all(not (e[4] == d[4] and iou(d, e) > 0.4) for e in out): out.append(d)
    def inter(a, b): return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return [d for d in out if not any(e is not d and e[4] == d[4] and area(e) > area(d) and inter(d, e) > 0.6 * area(d) for e in out)]  # fragments
if __name__ == "__main__":
    E = json.load(open(sys.argv[1])); out = {}
    for i, e in E.items():
        if e.get("status") == "rejected": out[i] = dict(status="rejected", note=e.get("note", ""), boxes=[], crowd=[]); continue
        if e.get("neg"): out[i] = dict(status="ok", negative=True, note=e.get("note", ""), boxes=[], crowd=[]); continue
        bx = [d[:5] for d in clean(i, e.get("thr", 0.25))] if not e.get("scratch") else []; dead = set(); cr = []
        for op in e.get("ops", []):
            k, a = op[0], op[1:]
            if k == "delid": dead |= set(a); continue
            bx = [b for n, b in enumerate(bx) if n not in dead] if dead else bx; dead = set()
            if k == "del": bx = [b for b in bx if not inr(b, a[:4])]
            elif k == "delc": bx = [b for b in bx if not (inr(b, a[:4]) and b[4] == a[4])]
            elif k == "rel": bx = [b[:4] + [a[5]] if inr(b, a[:4]) and (a[4] == -1 or b[4] == a[4]) else b for b in bx]
            elif k == "crowd": cr.append(list(a[:4]) + [a[4]]); bx = [b for b in bx if not (inr(b, a[:4]) and b[4] == a[4])]
            elif k == "ign": cr.append(list(a[:4]) + [-1]); bx = [b for b in bx if not inr(b, a[:4])]
            elif k == "add": bx.append(list(a[:4]) + [a[4]])
        if dead: bx = [b for n, b in enumerate(bx) if n not in dead]
        out[i] = dict(status="ok", note=e.get("note", ""), boxes=[[round(v, 5) for v in b[:4]] + [int(b[4])] for b in bx], crowd=[[round(v, 5) for v in c[:4]] + [int(c[4])] for c in cr])
    json.dump(out, open(sys.argv[2], "w"), indent=0)
    print(len(out), "images,", sum(len(v["boxes"]) for v in out.values()), "boxes,", sum(len(v["crowd"]) for v in out.values()), "crowd")
