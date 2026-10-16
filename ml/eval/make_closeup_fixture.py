"""Writes ml/eval/fixtures/closeup_parity.json (Python reference outputs replayed by native/tests/cvCloseup.test.ts)."""
import json, random, sys
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.closeup import detector_to_frame, crop_rect, roi_from_tap, id_policy, quality_reasons, GradeGate, FROZEN_GATE, DEFAULT_GATE, blockiness, touches_edge
from ml.prices.display import category_price, graded_price
rnd = random.Random(7); F = dict(gate=FROZEN_GATE, mapping=[], crop=[], roi=[], id=[], quality=[], gate_seqs=[], block=[], price=[], edge=[])
for W, H in [(1920, 1080), (1080, 1920), (4032, 3024), (640, 480), (3840, 2160), (720, 1280)]:
    for _ in range(6):
        x1, y1 = rnd.uniform(0, 400), rnd.uniform(0, 400); b = [x1, y1, x1 + rnd.uniform(5, 200), y1 + rnd.uniform(5, 200)]
        fb = detector_to_frame(b, W, H); F["mapping"].append(dict(box=b, W=W, H=H, out=fb))
        F["crop"].append(dict(box=fb, W=W, H=H, out=crop_rect(fb, W, H)))
        F["edge"].append(dict(box=fb, W=W, H=H, out=touches_edge(fb, W, H, 0.01)))
    tap = [rnd.random(), rnd.random()]; boxes = [detector_to_frame([rnd.uniform(0, 300), rnd.uniform(0, 300), rnd.uniform(300, 480), rnd.uniform(300, 480)], W, H) for _ in range(3)]
    F["roi"].append(dict(tap=tap, W=W, H=H, boxes=boxes, out=roi_from_tap(tap, W, H, boxes)))
    F["roi"].append(dict(tap=[0.02, 0.98], W=W, H=H, boxes=[], out=roi_from_tap([0.02, 0.98], W, H, [])))
for lab, sc, hits, amb in [(1, 0.9, 3, False), (1, 0.45, 5, False), (3, 0.8, 2, False), (3, 0.8, 4, True), (7, 0.5, 3, False)]:
    F["id"].append(dict(args=[lab, sc, hits, amb], out=id_policy(lab, sc, hits, amb)))
for _ in range(40):
    q = dict(sidePx=rnd.choice([32, 64, 95.9, 96, 128, 300]), blurVar=rnd.choice([5, 14.9, 15, 400]), meanV=rnd.choice([30, 79.9, 80, 150, 250]),
             touchesEdge=rnd.random() < .2, visibleFrac=rnd.choice([0.1, 0.25, 0.6]), maxProb=rnd.choice([0.6, 0.7, 0.99]), margin=rnd.choice([0.2, 0.3, 0.98]),
             blockiness=rnd.choice([None, 1.1, 1.41, 2.0]))
    if q["blockiness"] is None: del q["blockiness"]
    F["quality"].append(dict(q=q, out=quality_reasons(q, FROZEN_GATE)))
for mode in ("count", "score"):
    for _ in range(6):
        g = GradeGate({**FROZEN_GATE, "mode": mode}); seq = []
        for _ in range(8):
            a = dict(ok=rnd.random() < .8, grade=rnd.choice(["A", "B", "B", "Reject"]), pFresh=round(rnd.random(), 3), reasons=["blurry"]); seq.append(dict(a=a, out=g.push(a)))
        F["gate_seqs"].append(dict(mode=mode, seq=seq))
for k in range(4):
    w, h = [(32, 32), (40, 24), (64, 48), (20, 30)][k]; gray = [[(x * 7 + y * 3 + (x // 8) * 40 * (k % 2) + rnd.randint(0, 9)) % 256 for x in range(w)] for y in range(h)]
    F["block"].append(dict(w=w, h=h, gray=[v for row in gray for v in row], out=blockiness(gray)))
S = [json.load(open(f"/workspace/work/nutrisole/ml/prices/fixtures/parsed_{k}_2026-10-12.json")) for k in ("fruit", "vegetable")]
F["price_sources"] = S
for cls in ["apple", "banana", "tomato", "carrot", "citrus", "mango", "guava"]:
    for today in ["2026-10-14", "2026-10-20"]:
        for ident in [True, False]:
            F["price"].append(dict(fn="category", args=[ident, cls, today], out=category_price(ident, cls, S, today)))
        for gr in ["A", "B", "C", "Reject", None]:
            F["price"].append(dict(fn="graded", args=[True, cls, gr, today], out=graded_price(True, cls, gr, S, today)))
json.dump(F, open("/workspace/work/nutrisole/ml/eval/fixtures/closeup_parity.json", "w"))
print({k: len(v) for k, v in F.items() if isinstance(v, list)})
print([ (p["args"], p["out"].get("line", {}).get("text", p["out"].get("reason"))) for p in F["price"][:8]])
