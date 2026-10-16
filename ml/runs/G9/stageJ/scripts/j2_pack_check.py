"""G9 Stage J2: static integrity check of the pilot2 / train2 packs (no browser in the sandbox this session, so the headless-Chromium smoke test
j_tool_test.py could not be re-run). Checks: zip members; every template placeholder substituted; the HTML equals the frozen tool template once
title/pack/copy/N/data are substituted back (so the tool code is byte-identical to the one already browser-tested in Stage J and used for the
265 review); embedded photo count and ids == key; each photo decodes as a JPEG without EXIF; copy orders differ but hold the same ids; fallback CSV
rows/order == HTML order; contact sheets == ceil(N/20); inline <script> blocks pass `node --check`. Output: out/gaps/j2_pack_check.json."""
import zipfile, json, csv, io, re, base64, subprocess, tempfile, os, math
from PIL import Image
J = "/workspace/work/nutrisole/ml/runs/G9/stageJ"; GO = f"{J}/out/gaps"; TPL = open(f"{J}/tool/labeler_template.html").read()
key = list(csv.DictReader(open(f"{GO}/j2_blind_key.csv"))); packs = json.load(open(f"{GO}/j2_packs.json")); res = {}
for batch, lst in packs.items():
    ids = {r["blind_id"] for r in key if r["batch"] == batch}; orders = []
    for p in lst:
        z = zipfile.ZipFile(p["zip"]); names = z.namelist(); copy = "annotator1" if "annotator1" in p["zip"] else "annotator2"
        html = z.read(f"NutriSole_labelling_{batch}_{copy}.html").decode()
        m = re.search(r"(\[\{\"id\":.*?\}\])", html, re.S); data = json.loads(m.group(1))
        back = html.replace(m.group(1), "__DATA__")
        title = {"pilot2": "Pilot 2 (supplementary evaluation photos)", "train2": "Training photos, pack 2"}[batch]
        exp = (TPL.replace("__PACK_TITLE__", f"{title}, {len(data)} photos").replace("__PACK_ID__", f"G9J-{batch}").replace("__COPY__", copy).replace("__N__", str(len(data))))
        tool_identical = back == exp
        exif = 0; bad = 0
        for d in data:
            try:
                im = Image.open(io.BytesIO(base64.b64decode(d["src"].split(",", 1)[1]))); im.load(); exif += bool(im.info.get("exif"))
            except Exception: bad += 1
        fb = list(csv.DictReader(io.StringIO(z.read(f"fallback/fallback_{batch}_{copy}.csv").decode())))
        scripts = re.findall(r"<script>(.*?)</script>", re.sub(r"\[\{\"id\":.*?\}\]", "[]", html, flags=re.S), re.S); syn = []
        for s in scripts:
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f: f.write(s)
            syn.append(subprocess.run(["node", "--check", f.name], capture_output=True, text=True).returncode == 0); os.unlink(f.name)
        order = [d["id"] for d in data]; orders.append(order)
        res[os.path.basename(p["zip"])] = dict(items=len(data), ids_match_key=set(order) == ids and len(order) == len(ids), placeholders_left=re.findall(r"__[A-Z_]+__", html),
            tool_code_identical_to_template=tool_identical, jpeg_decode_failures=bad, photos_with_exif=exif, fallback_rows=len(fb), fallback_order_matches=[r["item_id"] for r in fb] == order,
            contact_sheets=sum(n.startswith("fallback/contact_sheets/") for n in names), contact_sheets_expected=math.ceil(len(data) / 20),
            has_guide="annotation_guide.md" in names, has_start="START_HERE.txt" in names, inline_scripts_node_check=syn, mb=p["mb"], sha256=p["sha256"])
    res[batch + "_copies_differ_in_order_same_ids"] = orders[0] != orders[1] and sorted(orders[0]) == sorted(orders[1])
json.dump(res, open(f"{GO}/j2_pack_check.json", "w"), indent=1); print(json.dumps(res, indent=1))
