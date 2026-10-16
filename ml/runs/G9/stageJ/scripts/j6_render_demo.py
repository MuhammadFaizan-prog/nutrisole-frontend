"""Render the G9 J6 demo video from a REAL host-side run (host_run.json from native/scripts/g9j6_host_pipeline.ts).
Every box, crop, title, reason and timing drawn here is read from that run's output; nothing is invented. Labelled host-side, not a phone."""
import json, re, subprocess, textwrap
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

RUN = json.load(open("/workspace/work/g9j6/host_run.json")); C = json.load(open("/workspace/work/g9j5/cands/cands.json"))
IMG = Path("/workspace/work/g9j5/cands/img"); OUT = Path("/workspace/work/g9j6/frames"); OUT.mkdir(parents=True, exist_ok=True)
for f in OUT.glob("*.png"): f.unlink()
F = lambda s, b=False: ImageFont.truetype(f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if b else ''}.ttf", s)
M = lambda s: ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", s)
W, H = 1280, 720
BANNER = "HOST-SIDE SIMULATION · sandbox CPU · Node + onnxruntime-node 1.24.3 · same TS pipeline + same ONNX files · NOT A PHYSICAL DEVICE"
NAMES = ["Banana", "Apple", "Mango", "Citrus", "Guava", "Pomegranate", "Lemon/lime", "Tomato", "Potato", "Cucumber", "Carrot", "Capsicum"]
rep = RUN["report"]; frames = []


def base():
    im = Image.new("RGB", (W, H), "#101512"); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 34], fill="#8a1c1c"); d.text((12, 8), BANNER, font=F(15, True), fill="white")
    return im, d


def add(im, secs):
    p = OUT / f"f{len(frames):03d}.png"; im.save(p); frames.append((p, secs))


def card(title, lines, secs, mono=False):
    im, d = base(); d.text((60, 80), title, font=F(34, True), fill="#f2c946"); y = 150
    for l in lines:
        for w in textwrap.wrap(l, 92 if mono else 80) or [""]:
            d.text((60, y), w, font=M(19) if mono else F(22), fill="#e8efe8"); y += 30 if mono else 34
    add(im, secs)


def credit(cid):
    c = C.get(cid, {}); a = " ".join((c.get("author") or c.get("uploader") or "").split())[:60]
    return f"Photo: {a} · {c.get('licence','')} · Wikimedia Commons ({c.get('title','')[5:60]}) · unverified training candidate, not eval"


def scene(r, step):
    """step 0 = still + tap; 1 = detections + crop; 2 = result."""
    im, d = base()
    with Image.open(IMG / f"{r['id']}.jpg") as src:
        st = ImageOps.exif_transpose(src).convert("RGB")
        s = min(1.0, 1280 / max(st.size)); st = st.resize((r["w"], r["h"]), Image.BILINEAR) if s < 1 or st.size != (r["w"], r["h"]) else st
    k = min(800 / r["w"], 600 / r["h"]); vw, vh = int(r["w"] * k), int(r["h"] * k); ox, oy = 20 + (800 - vw) // 2, 50 + (600 - vh) // 2
    im.paste(st.resize((vw, vh)), (ox, oy))
    P = lambda x, y: (ox + x * k, oy + y * k)
    if r.get("plan"):
        fx, fy = r["plan"]["framePoint"]; tx, ty = P(fx * r["w"], fy * r["h"])
        d.ellipse([tx - 12, ty - 12, tx + 12, ty + 12], outline="#ff4fd8", width=4); d.text((tx + 14, ty - 10), "tap", font=F(16, True), fill="#ff4fd8")
    if step >= 1:
        for b in r["last_dets"]:
            x1, y1 = P(b["box"][0], b["box"][1]); x2, y2 = P(b["box"][2], b["box"][3])
            d.rectangle([x1, y1, x2, y2], outline="#7fd38b", width=2); d.text((x1 + 3, y1 + 2), NAMES[b["classId"]], font=F(13, True), fill="#7fd38b")
        if r.get("plan"):
            c = r["plan"]["crop"]; x1, y1 = P(c["x"], c["y"]); x2, y2 = P(c["x"] + c["w"], c["y"] + c["h"])
            d.rectangle([x1, y1, x2, y2], outline="#f2c946", width=4); d.text((x1 + 4, y2 - 20), f"crop {c['w']}x{c['h']} px ({r['plan']['source']})", font=F(14, True), fill="#f2c946")
    # right panel
    X = 840; d.rectangle([X, 50, W - 20, 650], fill="#1b241d")
    badge = "REAL INFERENCE · G3+H2 ONNX · host CPU (not phone)" if step == 2 else "PLACEHOLDER · no model output (running)"
    d.rectangle([X + 10, 60, W - 30, 100], fill="#7fd38b" if step == 2 else "#f2a446"); d.text((X + 18, 70), badge[:58], font=F(13, True), fill="#111")
    y = 115
    def line(t, f=F(18), col="#e8efe8", wrap=36):
        nonlocal y
        for w in textwrap.wrap(t, wrap) or [""]: d.text((X + 18, y), w, font=f, fill=col); y += 26
    line(f"still {r['w']}x{r['h']} · burst = same still x3", F(15), "#aab")
    line(f"tap mode: {r['tapMode']}", F(15), "#aab"); y += 6
    if step == 0: line("Stage 1: tap → 3 stills → G3 detector (480 letterbox)", F(18))
    if step == 1:
        line(f"G3 boxes on last still: {len(r['last_dets'])}", F(18)); line(f"wide id: {r['wide'].get('status')} {r['wide'].get('reason','')}", F(16))
        line("Stage 2: crop → H2 close-up (224) → FROZEN_VERIFY", F(18))
    if step == 2:
        line(r["title"], F(21, True), "#ffffff", 30); y += 4
        v = r["verify"] or {}; line(f"verify: {v.get('status','-')} {v.get('reason','')}", F(16))
        line(f"domain: {r['domain']['domainId'] or '-'} (cv={r['domain']['cvClass'] or '-'})", F(16))
        line(f"nutrition: {'USDA FDC ' + str(r['nutrition_fdc']) + ' per 100 g' if r['nutrition_fdc'] else 'n/a'}", F(16))
        line("price: no verified source supplied", F(16)); line("grade: none (grades disabled)", F(16)); y += 6
        for l in r["logLines"]: line(re.sub(r"ms=([0-9.]+)", lambda m: "ms=%.1f" % float(m.group(1)), l), M(14), "#9fd0ff")
        line(f"host total {r['total_ms']} ms (2 vCPU sandbox)", M(14), "#9fd0ff")
    d.text((20, 660), credit(r["id"])[:150], font=F(12), fill="#9aa")
    d.text((20, 684), "Functional demo only: unverified images, no accuracy, latency or FPS claim for phones.", font=F(13), fill="#f2a446")
    add(im, [3.0, 3.5, 5.5][step])


card("NutriSole G9 Stage J6 · debug CV pipeline (host-side run)",
     ["What you see: the cv-gauntlet-device debug pipeline (device/debugPipeline.ts) executed on the Hark sandbox CPU through onnxruntime-node,",
      "with the exact ONNX files pushed to the phone (G3 detector det_yolo11n_640_raw.onnx, H2 h2_mnv3s.onnx, sha256-checked).",
      "No camera: each still is a licensed Commons photo; the 3-photo burst repeats the same still. Taps are simulated (view centre or top G3 box).",
      "This is NOT a recording of a phone. Phone numbers come only from your P1 run (see G9_stageJ6_ANDROID_P1_ADDENDUM.md).",
      "Recorded 2026-10-16 PKT."], 9)
# placeholder state (what the phone shows before models load / when they are missing)
im, d = base(); d.rectangle([340, 120, 940, 620], fill="#222"); d.text((360, 140), "DEBUG · phone test", font=F(18, True), fill="#f2c946")
d.rectangle([360, 180, 920, 220], fill="#f2a446"); d.text((372, 190), "PLACEHOLDER · no model output (loading models)", font=F(17, True), fill="#111")
d.text((360, 560), "Loading models…", font=F(20), fill="#ddd")
d.text((60, 640), "Placeholder state as drawn by CvDebugScan.tsx before both ONNX sessions load (or when models are missing). Badge turns green only for a real pipeline result.", font=F(15), fill="#e8efe8")
add(im, 6)
term = ["$ ORT_NODE_DIR=… node --experimental-strip-types scripts/g9j6_host_pipeline.ts",
        f"io_errors: h2 {rep['io_errors']['h2']} g3_det {rep['io_errors']['g3_det']}   (real runtime metadata vs MODEL_IO)",
        f"host init ms: h2 {rep['host_init_ms']['h2']}  g3_det {rep['host_init_ms']['g3_det']}   RSS MB: {rep['host_rss_mb']}",
        f"parity n={rep['parity']['n']}: det tensor maxAbs {rep['parity']['det_tensor_maxAbs']} (tol 0.0078) · h2 tensor maxAbs {rep['parity']['h2_tensor_maxAbs']} · h2 top-1 agree {rep['parity']['h2_top1_agree']}/{rep['parity']['n']} · det classes agree {rep['parity']['det_classes_agree']}/{rep['parity']['n']}",
        "latency (host, ms): " + ", ".join(f"{k} p50 {v['p50']:.1f} p95 {v['p95']:.1f}" for k, v in rep["latency_host"].items()),
        f"pipeline runs: {len(RUN['runs'])} · display contract errors {rep['pipeline']['display_errors']} · grades shown {rep['pipeline']['grades_shown']}"]
card("Harness output (host-side)", term, 9, mono=True)
pick = [r for r in RUN["runs"] if r["verify"] and r["verify"].get("status") == "verified"]
seen = set(); reasons = []
for r in RUN["runs"]:
    rs = (r["verify"] or {}).get("reason")
    if r not in pick and rs and rs not in seen and r["tapMode"] == "det": seen.add(rs); reasons.append(r)
for r in RUN["runs"]:
    if len(reasons) >= 5: break
    if r not in pick and r not in reasons and r["tapMode"] == "centre" and r["last_dets"]: reasons.append(r)
for r in pick + reasons[:5]:
    for s in (0, 1, 2): scene(r, s)
tit = sum(1 for r in RUN["runs"] if "Not graded" in r["title"])
card("Summary (host-side, functional only)",
     [f"{len(RUN['runs'])} simulated taps on {rep['parity']['n']} stills: {tit} named + Not graded, {len(RUN['runs']) - tit} Unable to identify; 0 grades, 0 percentages.",
      "Abstention is expected: H2 v2 accepted 9/99 supported items in Stage H/I; H3 is the planned fix and is blocked on human labels.",
      "Mapping: citrus → citrus_orange via domainMap.ts → USDA FDC nutrition per 100 g; no price shown without a verified official source.",
      "Next: your P1 phone run (exact steps in the addendum) gives the first real device init / latency / memory numbers."], 10)
lst = OUT / "list.txt"
with open(lst, "w") as f:
    for p, s in frames: f.write(f"file '{p}'\nduration {s}\n")
    f.write(f"file '{frames[-1][0]}'\n")
dst = "/workspace/projects/9399e4e3-d6d0-4c6b-a760-12b4c7c9c514/files/g9/stageJ/handoff/G9_stageJ6_demo.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", "fps=25,scale=1280:720,format=yuv420p",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", dst], check=True)
print(len(frames), sum(s for _, s in frames), dst)
