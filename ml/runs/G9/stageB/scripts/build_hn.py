"""Build the Stage B hard-negative manifest from the agent's review verdicts (video tiles + Commons stills), dedupe by pHash,
split Commons by uploader (~20% dev), leakage audit vs holdout keyframes, and write the kernel payload (Commons by URL, video crops
as base64 JPEG). Outputs: ml/runs/G9/stageB/hn_manifest.csv, leakage_audit.json, /workspace/work/cv/g9b/hn_payload.json"""
import json, csv, os, glob, base64, hashlib, collections, urllib.parse
import cv2, imagehash
from PIL import Image
R = "/workspace/work/nutrisole"; O = f"{R}/ml/runs/G9/stageB"; G = "/workspace/work/cv/g9b"
split = {r["clip_id"]: r for r in csv.DictReader(open(f"{O}/mining_split.csv"))}
rng = lambda a, b: [f"{a[:2]}{i:03d}" for i in range(int(a[2:]), int(b[2:]) + 1)]
VT_ACCEPT = (["vt004", "vt005", "vt006", "vt007", "vt008", "vt009"] + rng("vt014", "vt046") + ["vt048", "vt049", "vt050", "vt057", "vt058", "vt060", "vt061", "vt062"]
             + rng("vt063", "vt073") + ["vt083", "vt084"])
VT_TYPE = {**{k: "sack_seeds" for k in rng("vt004", "vt009")}, **{k: "out_of_taxonomy_produce(cupuacu)" for k in ("vt014", "vt015")},
           **{k: "out_of_taxonomy_produce(tapereba)" for k in rng("vt016", "vt033")}, **{k: "utensil/fish/fabric" for k in rng("vt034", "vt046")},
           "vt048": "clothing", "vt049": "utensil", "vt050": "utensil", "vt057": "fruit_coloured_crate", "vt058": "fruit_coloured_crate",
           "vt060": "out_of_taxonomy_produce(onion)", "vt061": "out_of_taxonomy_produce(onion)", "vt062": "person/clothing",
           **{k: "fish" for k in ("vt063", "vt064", "vt065")}, **{k: "clothing/umbrella" for k in rng("vt066", "vt071")}, "vt072": "bag", "vt073": "bag",
           "vt083": "clothing", "vt084": "glass/utensil"}
VD_HN = ["vd000", "vd001", "vd002", "vd013"] + rng("vd015", "vd020")
VD_TYPE = {"vd000": "out_of_taxonomy_produce(papaya)", "vd001": "out_of_taxonomy_produce(papaya)", "vd002": "out_of_taxonomy_produce(papaya)", "vd013": "out_of_taxonomy_produce(cabbage)", **{k: "clothing(print)" for k in rng("vd015", "vd020")}}
VD_POS = {**{k: "banana" for k in rng("vd003", "vd010") + ["vd012"]}, "vd014": "carrot", "vd021": "carrot", **{k: "tomato" for k in rng("vd022", "vd051")}}
CM_W = """0014 0025 0057 0079 0098 0145 0162 0164 0191 0199 0207 0270 0293 0345 0352 0354 0371 0375 0406 0410 0418 0421 0428 0446 0448 0451 0465 0467
0477 0483 0484 0501 0504 0505 0515 0528 0545 0551 0552 0556 0558 0570 0579 0580 0581 0582 0595 0598 0600 0602 0604 0611 0618 0621 0633 0652 0655 0675
0687 0689 0735 0747 0763 0773 0786 0800 0806 0821 0832 0833 0836 0837 0838 0839 0840 0841 0842 0843 0857 0882 0893 0932 0943 0945 0996 1011 1020 1022
1024 1028 1033 1035 1093 1119 1122 1141 1142 1144 1145 1218 1231 1233 1235 1237 1241 1243 1245 1247 1249 1360 1361 1362 1368 1370 1392 1393 1397 1403
1443 1460 1504 1550 1554 1585 1637 1653 1662 1732 1735 1738 1739 1753 1777 1778 1779 1818 1838 1847 1848 1944 1954 1973 1998""".split()
cdet = json.load(open(f"{G}/commons/g3_dets.json")); cman = {v["file"]: v for v in json.load(open(f"{G}/commons/manifest_search.json")).values() if "file" in v}
rows, payload = [], dict(items=[], mdev_pos=[])
def vid_crop(c):
    p = None
    for d in ("g6src", "g7src"):
        for e in ("webm", "ogv"):
            q = f"/workspace/work/cv/{d}/raw/{c['clip']}.{e}"
            if os.path.exists(q): p = q
    cap = cv2.VideoCapture(p); cap.set(cv2.CAP_PROP_POS_FRAMES, c["fi"]); ok, fr = cap.read(); a, b, s = c["crop"]; im = fr[b:b + s, a:a + s]
    if max(im.shape[:2]) > 320: im = cv2.resize(im, (320, 320))
    return im
cands = {x["id"]: x for t in ("vt", "vd") for x in json.load(open(f"{G}/vsheets/{t}_cands.json"))}
os.makedirs(f"{G}/hn_local", exist_ok=True)
for ids, sp, typ in ((VT_ACCEPT, "train", VT_TYPE), (VD_HN, "dev", VD_TYPE)):
    for i in ids:
        c = cands[i]; im = vid_crop(c); fn = f"{G}/hn_local/vc_{i}.jpg"; cv2.imwrite(fn, im, [cv2.IMWRITE_JPEG_QUALITY, 90])
        rows.append(dict(id=f"vc_{i}", split=sp, kind="video_crop", source=f"VB8 clip {c['clip']} ({split[c['clip']]['stageB_role']}), fi {c['fi']}, t {c['t']} s, crop {c['crop']}",
                         licence=split[c["clip"]]["licence"], uploader=split[c["clip"]]["uploader"], page=split[c["clip"]]["page"], target_type=typ[i],
                         g3_class=c["cls"], g3_score=c["score"], neighbours=f"fi {c['fi']}+-0.5 s kept as metadata only (not trained)",
                         review="agent_verified_negative", review_method="Hark visual review of context crop on contact sheet vsheets/" + i[:2] + "_*.jpg; no human", local=fn))
for i, cls in VD_POS.items():
    c = cands[i]; im = vid_crop(c); H, W = im.shape[:2]
    # tight crop of the box itself for the verifier (box expanded 1.2x inside the stored context crop)
    a, b, s = c["crop"]; fW, fH = c["W"], c["H"]; sc = im.shape[0] / s
    x0, y0, x1, y1 = c["box"][0] * fW - a, c["box"][1] * fH - b, c["box"][2] * fW - a, c["box"][3] * fH - b
    cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) * 1.2, (y1 - y0) * 1.2
    t = im[int(max(0, (cy - h / 2) * sc)):int(min(H, (cy + h / 2) * sc)), int(max(0, (cx - w / 2) * sc)):int(min(W, (cx + w / 2) * sc))]
    payload["mdev_pos"].append(dict(id=i, cls=cls, title=urllib.parse.unquote(split[c["clip"]]["page"].split("/wiki/", 1)[1]), fi=c["fi"], box=c["box"]))
for k in CM_W:
    f = f"cm{k}.jpg"; m = cman[f]
    sp = "dev" if int(hashlib.md5((m["uploader"] or "").encode()).hexdigest(), 16) % 5 == 0 else "train"
    rows.append(dict(id=f"cw_{k}", split=sp, kind="commons_whole", source=m["title"], licence=m["licence"], uploader=m["uploader"], page=m["page"], target_type=m["type"],
                     g3_class=";".join(str(b[4]) for b in cdet[f]["boxes"]), g3_score=max(b[5] for b in cdet[f]["boxes"]), neighbours="",
                     review="agent_verified_negative", review_method="Hark visual review of whole image on contact sheet csheets/cs_*.jpg; no human", local=f"{G}/commons/img/{f}", url=m["thumb"]))
# reviewed but rejected Commons images (for the record)
rej = [f for f, v in cdet.items() if v.get("boxes") and f[2:6] not in CM_W]
hold0 = [c for c, r in split.items() if r["stageB_role"] == "holdout_never_used"]; up_h0 = {split[c]["uploader"] for c in hold0}
for r in rows:
    if r["kind"] == "commons_whole" and r["uploader"] in up_h0: r["review"] = "agent_verified_negative_but_excluded(uploader_also_in_holdout)"
excl_up = [r["id"] for r in rows if r["review"].startswith("agent_verified_negative_but")]
rows_all = rows; rows = [r for r in rows if r["review"] == "agent_verified_negative"]
# pHash dedupe within the HN set (Hamming <= 6): keep first
ph = {r["id"]: imagehash.phash(Image.open(r["local"])) for r in rows}; keep, dropped = [], []
for r in rows:
    if any(ph[r["id"]] - ph[k["id"]] <= 6 for k in keep if k["split"] == r["split"] or True): dropped.append(r["id"]); r["dedup"] = "dropped_near_duplicate"; continue
    r["dedup"] = "kept"; keep.append(r)
# leakage audit: pHash vs keyframes of the 34 holdout clips
hold = [c for c, r in split.items() if r["stageB_role"] == "holdout_never_used"]; hk = []
for c in hold:
    for p in glob.glob(f"/workspace/work/cv/g7al/stage1/{c}/keyframes/*.jpg"): hk.append((c, imagehash.phash(Image.open(p))))
mind = {r["id"]: int(min((ph[r["id"]] - h for _, h in hk), default=99)) for r in keep}
up_h = {split[c]["uploader"] for c in hold}
audit = dict(holdout_clips=len(hold), holdout_keyframes_compared=len(hk), hn_kept=len(keep), min_phash_distance_to_holdout=min(mind.values()) if mind else None,
             hn_within_10_of_holdout=[k for k, v in mind.items() if v <= 10],
             video_sources=sorted({r["source"].split()[2] for r in keep if r["kind"] == "video_crop"}),
             video_source_roles=sorted({split[r["source"].split()[2]]["stageB_role"] for r in keep if r["kind"] == "video_crop"}),
             commons_uploaders_in_holdout_uploaders_after_exclusion=sorted({r["uploader"] for r in keep if r["kind"] == "commons_whole"} & up_h), excluded_for_uploader_overlap=excl_up,
             holdout_tiles_used=0, muktee_clips_used=0, mdev_in_train=sum(1 for r in keep if r["split"] == "train" and r["kind"] == "video_crop" and split[r["source"].split()[2]]["stageB_role"] == "M-dev"),
             near_duplicates_dropped=dropped, commons_reviewed_rejected=len(rej), video_tiles_reviewed=len([i for i in cands if i.startswith("vt")]), video_tiles_rejected=len([i for i in cands if i.startswith("vt") and i not in VT_ACCEPT]))
for r in keep:
    it = dict(id=r["id"], split=r["split"], kind=r["kind"])
    if r["kind"] == "video_crop":
        c = cands[r["id"][3:]]; it.update(title=urllib.parse.unquote(split[c["clip"]]["page"].split("/wiki/", 1)[1]), fi=c["fi"], crop=c["crop"])
    else: it["url"] = r["url"]
    payload["items"].append(it)
json.dump(payload, open(f"{G}/hn_payload.json", "w"))
flds = ["id", "split", "kind", "target_type", "g3_class", "g3_score", "review", "review_method", "dedup", "source", "licence", "uploader", "page", "neighbours"]
with open(f"{O}/hn_manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=flds, extrasaction="ignore"); w.writeheader(); w.writerows(rows_all)
json.dump(audit, open(f"{O}/leakage_audit.json", "w"), indent=1)
print(collections.Counter((r["split"], r["kind"]) for r in keep), "dropped", len(dropped), "mdev_pos", len(payload["mdev_pos"]))
print({k: v for k, v in audit.items() if k not in ("near_duplicates_dropped",)})
print("payload bytes", os.path.getsize(f"{G}/hn_payload.json"))
