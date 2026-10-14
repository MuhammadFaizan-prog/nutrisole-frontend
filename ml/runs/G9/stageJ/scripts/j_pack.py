"""G9 Stage J: build the offline labelling packs (one zip per annotator per batch).
Each zip holds: the single-file labelling tool (HTML, every photo embedded, no internet needed), the plain-language guide, a fallback blind CSV
in the same order as that copy's tool, numbered contact sheets (fallback, 20 photos per sheet), and START_HERE.txt.
Copies: annotator 1 and annotator 2 see the SAME photos in DIFFERENT random orders (seeds 101 / 202). No source, label, licence or
split is shown; photos are re-encoded without metadata and named by blind id only. The blind-id -> source key stays in out/j_blind_key.csv.
Usage: j_pack.py [pilot|train|all]"""
import csv, io, json, base64, random, sys, os, zipfile, hashlib
from PIL import Image, ImageDraw, ImageFont
ROOT = "/workspace/work/nutrisole"; J = f"{ROOT}/ml/runs/G9/stageJ"; OUT = f"{J}/out"; LAB = f"{J}/labeling"; os.makedirs(LAB, exist_ok=True)
TPL = open(f"{J}/tool/labeler_template.html").read()
GUIDE = f"{ROOT}/docs/cv/gauntlet/G9_stageJ_annotation_guide.md"
KEYS = list(csv.DictReader(open(f"{OUT}/j_blind_key.csv")))
def path(k): return f"/workspace/work/g9i/cands/img/{k}.jpg" if os.path.exists(f"/workspace/work/g9i/cands/img/{k}.jpg") else f"/workspace/work/g9j/train/img/{k}.jpg"
def clean_jpeg(k, side=640, q=84):
    im = Image.open(path(k)).convert("RGB"); w, h = im.size; s = min(1.0, side / max(w, h))
    if s < 1: im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
    b = io.BytesIO(); im.save(b, "JPEG", quality=q, optimize=True); return b.getvalue(), im   # PIL writes no EXIF unless asked
def font(sz):
    for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(f): return ImageFont.truetype(f, sz)
    return ImageFont.load_default()
F = font(26); FS = font(16)
def sheets(ids, ims, prefix):
    out = []
    for s in range(0, len(ids), 20):
        cell, cols = 300, 5; sh = Image.new("RGB", (cols * cell, 4 * (cell + 34) + 40), "white"); d = ImageDraw.Draw(sh)
        d.text((10, 8), f"{prefix} sheet {s // 20 + 1:02d}  (write the label next to each id in the fallback CSV)", fill="black", font=FS)
        for j, bid in enumerate(ids[s:s + 20]):
            im = ims[bid].copy(); im.thumbnail((cell - 10, cell - 10)); x, y = (j % cols) * cell, 40 + (j // cols) * (cell + 34)
            sh.paste(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2)); d.text((x + 8, y + cell + 2), bid, fill=(180, 0, 0), font=F)
        b = io.BytesIO(); sh.save(b, "JPEG", quality=80); out.append((f"contact_sheets/{prefix}_sheet_{s // 20 + 1:02d}.jpg", b.getvalue()))
    return out
FB_COLS = ["item_id", "label", "other_produce_name", "occluded_or_printed_what", "cut", "bag", "multi", "rotten_damaged", "note", "annotator", "contact_sheet"]
def build(batch):
    rows = [r for r in KEYS if r["batch"] == batch]; ids = sorted(r["blind_id"] for r in rows); kid = {r["blind_id"]: r["key"] for r in rows}
    raw, ims = {}, {}
    for bid in ids: raw[bid], ims[bid] = clean_jpeg(kid[bid])
    sheet_of = {bid: f"{batch}_sheet_{n // 20 + 1:02d}.jpg" for n, bid in enumerate(ids)}
    shs = sheets(ids, ims, batch)
    title = {"pilot": "Pilot (evaluation photos)", "train": "Training photos"}[batch]
    res = []
    for copy, seed in (("annotator1", 101), ("annotator2", 202)):
        order = ids[:]; random.Random(seed).shuffle(order); pack_id = f"G9J-{batch}"
        data = [dict(id=b, src="data:image/jpeg;base64," + base64.b64encode(raw[b]).decode()) for b in order]
        html = (TPL.replace("__PACK_TITLE__", f"{title}, {len(order)} photos").replace("__PACK_ID__", pack_id).replace("__COPY__", copy)
                   .replace("__N__", str(len(order))).replace("__DATA__", json.dumps(data, separators=(",", ":"))))
        fb = io.StringIO(); w = csv.writer(fb); w.writerow(FB_COLS)
        for b in order: w.writerow([b, "", "", "", "", "", "", "", "", "", sheet_of[b]])
        start = open(f"{J}/tool/START_HERE.txt").read().replace("__COPY__", copy).replace("__BATCH__", title).replace("__N__", str(len(order)))
        zp = f"{LAB}/nutrisole_G9J_{batch}_{copy}.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("START_HERE.txt", start)
            z.writestr(f"NutriSole_labelling_{batch}_{copy}.html", html)
            if os.path.exists(GUIDE): z.writestr("annotation_guide.md", open(GUIDE).read())
            z.writestr(f"fallback/fallback_{batch}_{copy}.csv", fb.getvalue())
            for n, b in shs: z.writestr("fallback/" + n, b)
        res.append(dict(zip=zp, mb=round(os.path.getsize(zp) / 1e6, 1), items=len(order), sha256=hashlib.sha256(open(zp, "rb").read()).hexdigest(),
                        html_order_first5=order[:5]))
    return res
which = sys.argv[1] if len(sys.argv) > 1 else "all"
R = {b: build(b) for b in (["pilot", "train"] if which == "all" else [which])}
prev = json.load(open(f"{OUT}/j_packs.json")) if os.path.exists(f"{OUT}/j_packs.json") else {}
prev.update(R); json.dump(prev, open(f"{OUT}/j_packs.json", "w"), indent=1); print(json.dumps(R, indent=1))
