"""Stage G annotated recordings (ffmpeg). demo: wide scan (M-DEV still) -> tap -> simulated move-closer (CU-check still) -> ID + grade +
official price, or a clear refusal. compare: naive (confidence-only fresh/rotten) vs gated grading across crop sizes. Licensed Commons
stills only (credits frame at the end). Usage: render_g.py demo|compare"""
import json, os, sys, subprocess, collections, cv2, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from g_models import detect, N
from e2e_g import assess_crop, PRICES, TODAY
from ml.eval.closeup import roi_from_tap, id_policy, GradeGate, FROZEN_GATE, crop_rect
from ml.eval.tracker import IouTracker
from ml.prices.display import category_price, graded_price
from ml.grading.measure import object_mask
B = "/workspace/work/nutrisole/ml/runs/G9/stageG"; OUT = f"{B}/out/video"; os.makedirs(OUT, exist_ok=True)
CM = json.load(open(f"{B}/cu_manifest.json")); FONT = cv2.FONT_HERSHEY_SIMPLEX
def canvas(): return np.full((720, 1280, 3), 24, np.uint8)
def fit(im, w, h):
    s = min(w / im.shape[1], h / im.shape[0]); return cv2.resize(im, (int(im.shape[1] * s), int(im.shape[0] * s)), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_NEAREST), s
def text(c, t, x, y, sc=0.7, col=(255, 255, 255), th=2):
    cv2.putText(c, t, (x, y), FONT, sc, (0, 0, 0), th + 3, cv2.LINE_AA); cv2.putText(c, t, (x, y), FONT, sc, col, th, cv2.LINE_AA)
def panel(c, lines, x=860, y=60):
    cv2.rectangle(c, (x - 10, y - 35), (1270, y + 32 * len(lines)), (45, 45, 45), -1)
    for i, (t, col) in enumerate(lines): cv2.putText(c, t, (x, y + 32 * i), FONT, 0.55, col, 1, cv2.LINE_AA)
class W:
    def __init__(s, name): s.p = f"/workspace/work/g9g/fr_{name}"; os.makedirs(s.p, exist_ok=True); [os.remove(f"{s.p}/{f}") for f in os.listdir(s.p)]; s.n = 0
    def add(s, c, k=1):
        for _ in range(k): cv2.imwrite(f"{s.p}/{s.n:05d}.png", c); s.n += 1
    def enc(s, out):
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-framerate", "15", "-i", f"{s.p}/%05d.png", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], check=True)
def title(w, lines, k=45):
    c = canvas()
    for i, t in enumerate(lines): text(c, t, 60, 200 + 50 * i, 0.9 if i == 0 else 0.7, (255, 255, 255) if i == 0 else (200, 200, 200), 2 if i == 0 else 1)
    w.add(c, k)
def credits(w, keys):
    c = canvas(); text(c, "Image credits (Wikimedia Commons)", 40, 50, 0.8)
    MM = json.load(open("/workspace/work/cv/g9e/commons/manifest.json"))
    for i, k in enumerate(keys):
        m = CM[k] if k in CM else next((dict(v, user=v.get("uploader")) for v in MM.values() if k and k.startswith("m0") and k in json.dumps(v)), None)
        if m: text(c, f"{m['title'][5:70]} - {(m['artist'] or m['user'])[:40]} - {m['licence']}", 40, 100 + 30 * i, 0.5, (210, 210, 210), 1)
    text(c, "Research prototype (NutriSole G9 Stage G). Visual grade = appearance only, agent-verified labels, not certified.", 40, 680, 0.5, (180, 180, 180), 1); w.add(c, 75)

def demo():
    w = W("demo"); used = []
    title(w, ["NutriSole: scan -> select -> move closer -> grade or refuse", "Sandbox simulation on licensed stills (not a phone recording; no FPS claim).",
              "Detector G3 (480, unchanged) | gate: 96 px on full-res frame + 3 agreeing assessments", "Prices: official Lahore list, shown with source, date, location and unit."])
    # 1. wide scan: M-DEV still with the most identified boxes
    md = json.load(open("/workspace/work/g9g/cache/mdev.json")); LB = json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageF/m_labels_v2.json"))
    from e2e_g import _iou
    def tp(k):  # identified boxes that match a labelled box of the same class (IoU >= .5); false IDs penalised
        Wd, Hh = md[k]["W"], md[k]["H"]; gt = [[b[0] * Wd, b[1] * Hh, b[2] * Wd, b[3] * Hh, b[4]] for b in LB[k]["boxes"]]; n = 0
        for b, c_, s_ in md[k]["dets"]:
            if id_policy(c_, s_, 3)["status"] != "identified": continue
            n += 1 if any(g[4] == c_ and _iou(b, g) >= .5 for g in gt) else -1
        return n
    k = max(md, key=tp)
    im = cv2.imread(f"/workspace/work/cv/g9e/commons/img/{k}.jpg"); f, s = fit(im, 840, 680); c = canvas(); c[20:20 + f.shape[0], 10:10 + f.shape[1]] = f; seen = []
    for b, cl, sc in md[k]["dets"]:
        st = id_policy(cl, sc, 3)["status"]; col = (80, 220, 80) if st == "identified" else (0, 165, 255); bb = [int(v * s) for v in b]
        cv2.rectangle(c, (bb[0] + 10, bb[1] + 20), (bb[2] + 10, bb[3] + 20), col, 2)
        text(c, N[cl] if st == "identified" else "Unable to identify", bb[0] + 12, bb[1] + 16, 0.45, col, 1)
        if st == "identified" and cl not in seen: seen.append(cl)
    lines = [("WIDE SCAN (stall view)", (255, 255, 255)), ("Quality: move closer to check", (0, 200, 255))]
    for cl in seen[:4]:
        p = category_price(True, N[cl], PRICES, TODAY); lines.append((f"{N[cl]}: " + (p["line"]["text"][:44] if p["show"] else "no current official price"), (220, 220, 220)))
        if p["show"]: lines.append(("   " + p["line"]["text"][44:90], (170, 170, 170)))
    lines.append(("Official reference, not this seller's price", (150, 150, 150)))
    panel(c, lines); w.add(c, 60); used.append(None)
    mdk = k
    # 2. approach sequences: one graded with correct ID, one refusal
    A = json.load(open(f"{B}/out/e2e_approach.json"))
    good = next((k for k, v in A.items() if v["grade"] and v["id_correct"] and v["cls"] in ("apple", "tomato", "carrot", "banana", "citrus")), None)
    bad = next((k for k, v in A.items() if v["id_correct"] and not v["grade"]), None) or next((k for k, v in A.items() if not v["id_class"]), None)
    T = json.load(open(f"{B}/cu_triage.json"))
    for k in [x for x in (good, bad) if x]:
        cls, lab, tap = T["item"][k]; used.append("cu" + k); im = cv2.imread(f"/workspace/work/g9g/cu/img/cu{k}.jpg"); H, Wd = im.shape[:2]
        bg = (cv2.GaussianBlur(im, (0, 0), 25) * 0.5).astype(np.uint8); tr = IouTracker(); hits = collections.Counter(); g = GradeGate(FROZEN_GATE); final = None
        title(w, [f"Select the {cls} -> 'move closer to check quality'", "Simulated approach: the still is scaled 0.2 -> 1.0 (never above its native pixels)", "Shown 3x slower than the simulated 15 fps"], 30)
        for fi in range(20):
            sc = 0.2 + 0.8 * fi / 19; fw, fh = max(8, round(Wd * sc)), max(8, round(H * sc)); fr = bg.copy(); x0, y0 = (Wd - fw) // 2, (H - fh) // 2
            fr[y0:y0 + fh, x0:x0 + fw] = cv2.resize(im, (fw, fh), interpolation=cv2.INTER_AREA)
            ts = tr.update([dict(box=b, classId=c_, score=s_) for b, c_, s_ in detect(fr)], fi * 1000 / 15)
            for t in ts: hits[t["id"]] += 1
            ident = [t for t in ts if id_policy(t["label"], t["score"], hits[t["id"]])["status"] == "identified"]
            r = roi_from_tap([(x0 + tap[0] * fw) / Wd, (y0 + tap[1] * fh) / H], Wd, H, [t["box"] for t in ident])
            f, s = fit(fr, 840, 680); c = canvas(); c[20:20 + f.shape[0], 10:10 + f.shape[1]] = f
            tx, ty = int((x0 + tap[0] * fw) * s) + 10, int((y0 + tap[1] * fh) * s) + 20; cv2.circle(c, (tx, ty), 10, (255, 255, 255), 2)
            lines = [("CLOSE-UP", (255, 255, 255))]
            if r["source"] == "track":
                t = next(t for t in ident if t["box"] == r["box"]); idc = N[t["label"]]; a = assess_crop(fr, r["box"], idc, FROZEN_GATE, {}); dec = g.push(a)
                bb = [int(v * s) for v in r["box"]]; col = (80, 220, 80) if dec["status"] == "graded" else (0, 200, 255) if dec["status"] == "pending" else (60, 60, 230)
                cv2.rectangle(c, (bb[0] + 10, bb[1] + 20), (bb[2] + 10, bb[3] + 20), col, 3)
                lines += [(f"ID: {idc} (score {t['score']:.2f})", (220, 220, 220)), (f"crop side: {a['side']:.0f} px of frame (gate 96)", (220, 220, 220))]
                if dec["status"] == "graded":
                    final = (idc, dec["grade"]); p = graded_price(True, idc, dec["grade"], PRICES, TODAY)
                    lines += [(f"Visual grade {dec['grade']} (appearance only)", (80, 220, 80)), (f"condition model: {a.get('cond')}", (200, 200, 200))]
                    lines += [((p["line"]["text"][:46]) if p["show"] else "No price shown (" + p["reason"] + ")", (220, 220, 220))] + ([(p["line"]["text"][46:92], (170, 170, 170)), ("Official reference, not this seller's price", (150, 150, 150))] if p["show"] else [])
                elif dec["status"] == "pending": lines += [("Hold steady... " + dec["reasons"][0], (0, 200, 255))]
                else: lines += [("Not graded: " + ", ".join(x.split(":")[0] for x in dec["reasons"])[:44], (60, 60, 230)), ("Move closer to check quality" if any(x.startswith("too_small") for x in dec["reasons"]) else "Could not be graded reliably", (60, 60, 230))]
            else:
                g.reset(); lines += [("Unable to identify", (0, 165, 255)), ("No name, no grade, no price", (0, 165, 255))]
            panel(c, lines); w.add(c, 3)
        c2 = c.copy(); msg = f"RESULT: {final[0]} graded {final[1]} (latched when the gate passed; later frames too close)" if final else "RESULT: could not be graded reliably"
        text(c2, msg, 20, 700, 0.8, (80, 220, 80) if final else (60, 60, 230)); w.add(c2, 40)
    credits(w, [mdk] + used[1:]); w.enc(f"{OUT}/g9g_demo_walkthrough.mp4")
    with open(f"{OUT}/demo_sources.json", "w") as fh: json.dump(dict(wide_mdev_image=mdk, approach_items=[good, bad]), fh)
    print("demo", w.n, good, bad, mdk)

def compare():
    w = W("cmp"); R = {json.loads(l)["id"]: json.loads(l) for l in open(f"{B}/out/feas_items.jsonl")}; T = json.load(open(f"{B}/cu_triage.json"))
    keys = [k for k, v in R.items() if v["split"] == "check" and v["cls"] in ("apple", "tomato", "banana", "citrus", "carrot") and "256" in v["sizes"]][:4]
    title(w, ["Naive vs gated grading on the same crop", "Naive: fresh/rotten from model confidence alone, always shown", "Gated: 96 px on full-res pixels + blur / light / occlusion / truncation / JPEG / uncertainty checks",
              "Crops downsampled from licensed close-ups (CU-check, DEV); label = source category, agent-verified"])
    for k in keys:
        it = R[k]; cls, lab, tap = T["item"][k]; im = cv2.imread(f"/workspace/work/g9g/cu/img/cu{k}.jpg"); H, Wd = im.shape[:2]
        dets = detect(im); r = roi_from_tap(tap, Wd, H, [d[0] for d in dets]); box = r["box"]
        if r["source"] == "tap_roi":
            x1, y1, x2, y2 = map(int, box); m, _ = object_mask(im[y1:y2, x1:x2][:, :, ::-1].copy()); ys, xs = np.where(m)
            if len(xs) > 50: box = [x1 + xs.min(), y1 + ys.min(), x1 + xs.max() + 1, y1 + ys.max() + 1]
        cr = crop_rect(box, Wd, H); nat = im[cr["y"]:cr["y"] + cr["h"], cr["x"]:cr["x"] + cr["w"]]
        for s_ in ["32", "64", "96", "128", "192", "256"]:
            for cond in ("clean", "lowlight", "occlusion"):
                rr = it["sizes"].get(s_, {}).get(cond)
                if not rr: continue
                h0, w0 = nat.shape[:2]; sc = int(s_) / (h0 * w0) ** .5; small = cv2.resize(nat, (max(2, round(w0 * sc)), max(2, round(h0 * sc))), interpolation=cv2.INTER_AREA)
                if cond == "lowlight": small = np.clip((small.astype(np.float32) / 255) ** 1.8 * 0.35 * 255, 0, 255).astype(np.uint8)
                if cond == "occlusion": small = small.copy(); small[:, : int(0.5 * small.shape[1])] = (60, 90, 140)
                big, _ = fit(small, 520, 520); big = cv2.resize(small, (big.shape[1], big.shape[0]), interpolation=cv2.INTER_NEAREST)
                c = canvas(); text(c, f"{cls} | label: {it['label']} (source category, agent-verified) | crop {s_} px | {cond}", 20, 40, 0.65)
                for j, x in enumerate((20, 660)):
                    c[80:80 + big.shape[0], x:x + big.shape[1]] = big
                q = dict(sidePx=rr["side"], blurVar=rr["blur"], meanV=rr["meanV"], touchesEdge=rr["edge"], visibleFrac=rr["vis"], maxProb=rr["maxP"], margin=rr["margin"])
                from ml.eval.closeup import quality_reasons
                bl = json.loads([l for l in open(f"{B}/out/feas_block.jsonl") if json.loads(l)["id"] == k][0])["sizes"][s_][cond]; q["blockiness"] = bl
                rs = quality_reasons(q, FROZEN_GATE) + ([] if rr["grade"] in ("A", "B", "C", "Reject") else ["rubric_ungradable"])
                ncol = (80, 220, 80) if rr["cond"] == it["label"] else (60, 60, 230)
                text(c, f"NAIVE: {rr['cond']} ({rr['maxP']:.2f})", 20, 660, 0.8, ncol)
                text(c, ("GATED: grade " + rr["grade"] + f" ({rr['cond']})") if not rs else "GATED: Not graded", 660, 660, 0.8, (80, 220, 80) if not rs else (0, 200, 255))
                if rs: text(c, ", ".join(x.split(":")[0] for x in rs)[:60], 660, 700, 0.55, (0, 200, 255), 1)
                w.add(c, 12)
    credits(w, ["cu" + k for k in keys]); w.enc(f"{OUT}/g9g_naive_vs_gated.mp4"); print("compare", w.n, keys)

if __name__ == "__main__": globals()[sys.argv[1]]()
