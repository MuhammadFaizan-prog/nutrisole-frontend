"""G9 Stage F P3: market-train (MT) labels = OWLv2 proposals (non-G3) cleaned as in Stage E (12-class, score >= thr [0.30], container
boxes dropped, class NMS 0.4, fragments dropped) + agent edit ops (normalised coords, region ops act on box centres):
  ["del", x1,y1,x2,y2] | ["delc", x1,y1,x2,y2,c] | ["rel", x1,y1,x2,y2,c_from|-1,c_to] | ["add", x1,y1,x2,y2,c] | ["delid", n...]
  ["grey", x1,y1,x2,y2]  grey out (pixels -> 114 in the training image) a pile / unverifiable region; boxes centred in it are deleted
  ["all", c]  relabel every box to class c
Negatives: {"neg": true} -> no boxes (the whole image is a verified non-target scene). Rejected: {"status": "rejected"}.
Usage: build_mt.py EDITS.json OUT.json"""
import json, sys
sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageE/scripts"); import build_labels as BL
P = json.load(open("/workspace/work/cv/g9f/kowl_out/owl_props.json"))["images"]
def clean(i, thr=0.30):
    ds = [d["box"] + [d["cls"], d["score"]] for d in P[i]["dets"] if d["cls"] >= 0 and d["score"] >= thr]
    keep = [d for d in ds if len([e for e in ds if e is not d and e[4] == d[4] and BL.inr(e, d) and BL.area(e) < 0.5 * BL.area(d)]) < 2]
    keep.sort(key=lambda d: -d[5]); out = []
    for d in keep:
        if all(not (e[4] == d[4] and BL.iou(d, e) > 0.4) for e in out): out.append(d)
    def inter(a, b): return max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return [d for d in out if not any(e is not d and e[4] == d[4] and BL.area(e) > BL.area(d) and inter(d, e) > 0.6 * BL.area(d) for e in out)]
if __name__ == "__main__":
    E = json.load(open(sys.argv[1])); out = {}
    for i, e in E.items():
        if e.get("status") == "rejected": out[i] = dict(status="rejected", note=e.get("note", ""), boxes=[], grey=[]); continue
        if e.get("neg"): out[i] = dict(status="ok", negative=True, note=e.get("note", ""), boxes=[], grey=[]); continue
        bx = [d[:5] for d in clean(i, e.get("thr", 0.30))]; gr = []; dead = set()
        for op in e.get("ops", []):
            k, a = op[0], op[1:]
            if k == "delid": dead |= set(a); continue
            if dead: bx = [b for n, b in enumerate(bx) if n not in dead]; dead = set()
            if k == "del": bx = [b for b in bx if not BL.inr(b, a[:4])]
            elif k == "delc": bx = [b for b in bx if not (BL.inr(b, a[:4]) and b[4] == a[4])]
            elif k == "rel": bx = [b[:4] + [a[5]] if BL.inr(b, a[:4]) and (a[4] == -1 or b[4] == a[4]) else b for b in bx]
            elif k == "all": bx = [b[:4] + [a[0]] for b in bx]
            elif k == "add": bx.append(list(a[:4]) + [a[4]])
            elif k == "grey": gr.append(list(a[:4])); bx = [b for b in bx if not BL.inr(b, a[:4])]
        if dead: bx = [b for n, b in enumerate(bx) if n not in dead]
        out[i] = dict(status="ok", negative=False, note=e.get("note", ""), boxes=[[round(v, 5) for v in b[:4]] + [int(b[4])] for b in bx], grey=[[round(v, 4) for v in g] for g in gr])
    json.dump(out, open(sys.argv[2], "w"), indent=0)
    print(len(out), "images,", sum(len(v["boxes"]) for v in out.values()), "boxes,", sum(len(v["grey"]) for v in out.values()), "grey regions,", sum(v.get("negative", False) for v in out.values()), "negatives")
