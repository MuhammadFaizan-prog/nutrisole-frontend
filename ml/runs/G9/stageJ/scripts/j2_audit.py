"""G9 Stage J2 (gaps): licence audit, pHash near-duplicate audit and source separation for the NEW candidates, then assignment.
New eval candidates (pilot2, J-EVAL ONLY): Commons per-file CC/PD packaging / partly-hidden / extra apple+citrus (commons_e2), and more FruitNet
  (b6fftwbr2v, CC BY 4.0, already a whole-J-eval source) Good-quality Orange/Apple rows not used before.
New training candidates (J-TRAIN ONLY): Mendeley CC BY 4.0 datasets (mb_in y3649cmgg6, bg_in 56td5w4wz2, vegnet 6nxnjbn9w6, sp_co 6ps7gtp2wg,
  veg_in chv7dmvtfm rest, citrus_tw bxfgvsn9kw rest) + Commons train-side apple (commons_t2).
Rules (frozen here, same as j_partition.py):
  * licence: Commons extmetadata LicenseShortName per file must be CC (no NC/ND) / PD / CC0, NonFree false; credit/artist/description must not name
    Pexels, Pixabay, Mixkit or Unsplash. Mendeley: dataset data_licence via public API must be CC BY 4.0 (snapshot in j2_mendeley_licences.json).
  * near-duplicates: 64-bit pHash Hamming <= 10 against EVERY earlier reference (Stage H in-kernel list incl. M-DEV/M-TEST HASHES ONLY, H-set,
    G3 train/DEV/clips, Stage D-F pools, CU), every Stage J item in all splits (incl. quarantined Stage J training files), and each other.
    A new eval item that collides with anything existing is DROPPED (frozen eval/train never change). A new training item colliding with any eval
    item (old or new), any reference or any existing J item is QUARANTINED. Within one new training source, near-dups (<= 6) keep one representative.
  * source separation: a Commons uploader/artist may sit in one split only (existing owners win; eval2 owners beat train2). Mendeley datasets are
    one group each; none of the new datasets is an eval source (eval datasets: FruitNet, carrot_m, tomato_m).
Labels here are SOURCE metadata (exploratory) only. M-TEST content is never opened.
Output: out/gaps/j2_candidates.json, j2_licence.csv, j2_quarantine.csv, j2_audit_summary.json."""
import json, csv, re, os, glob, hashlib, collections
import numpy as np, imagehash
from PIL import Image
W = "/workspace/work/g9j2"; G9 = "/workspace/work/nutrisole/ml/runs/G9"; OUT = f"{G9}/stageJ/out"; GO = f"{OUT}/gaps"
P = json.load(open(f"{OUT}/j_partitions.json"))
ref = list(json.load(open("/workspace/work/g9h/eval_hashes.json"))) + list(json.load(open("/workspace/work/g9h/hset/hhash.json")).values())
rh = json.load(open("/workspace/work/g9h/refhash.json")); ref += [h for _, h in rh["g9e"] + rh["m"]] + list(rh["pool"].values()) + list(rh["cu"].values())
ref = sorted(set(ref)); BLANK = {"0000000000000000", "8000000000000000"}
def bits(h): return np.unpackbits(np.frombuffer(bytes.fromhex(h), np.uint8))
RA = np.array([bits(h) for h in ref], np.uint8)
# existing Stage J items (all splits) + quarantined Stage J train files that still exist on disk
J = {k: (v["phash"], v["split"]) for k, v in P["items"].items()}
for k in P["quarantined"]:
    p = f"/workspace/work/g9j/train/img/{k}.jpg" if os.path.exists(f"/workspace/work/g9j/train/img/{k}.jpg") else f"/workspace/work/g9i/cands/img/{k}.jpg"
    if os.path.exists(p): J[k] = (str(imagehash.phash(Image.open(p).convert("RGB"))), "quarantined")
JK = list(J); JA = np.array([bits(J[k][0]) for k in JK], np.uint8)
BANNED = re.compile(r"unsplash|pixabay|pexels|mixkit", re.I)
ML = json.load(open(f"{GO}/j2_mendeley_licences.json"))
def lic_ok(v):
    if v["source"].startswith("commons"):
        L = v.get("licence", "")
        if not re.search(r"CC|Public domain|PD|CC0", L, re.I) or re.search(r"\bNC\b|\bND\b|-nc|-nd", L, re.I): return False, "licence not CC/PD or NC/ND"
        if BANNED.search(" ".join([v.get("credit", ""), v.get("author", ""), v.get("title", "")])): return False, "banned stock origin"
        if not v.get("author") and not v.get("uploader"): return False, "no author"
        return True, ""
    did = v.get("mendeley_id") or v["uploader"].split()[-1]; m = ML.get(did, {})
    return (m.get("licence") == "CC BY 4.0", "" if m.get("licence") == "CC BY 4.0" else f"dataset licence {m.get('licence')}")
def pkeys(v):
    ks = set()
    if v["source"].startswith("commons"):
        if v.get("uploader"): ks.add("u:" + v["uploader"].lower())
        a = re.sub(r"\s+", " ", (v.get("author") or "").lower()).strip()
        if a and not re.search(r"^(unknown|anonymous|unbekannt|author unknown)|unknown author", a) and len(a) > 2: ks.add("a:" + a[:80])
    else: ks.add("d:" + v["source"])
    return ks
owner = {}
for v in P["items"].values():
    vv = dict(source=v["source"], uploader=v["uploader"], author=v["artist"])
    for pk in pkeys(vv): owner.setdefault(pk, v["split"])
E = json.load(open(f"{W}/eval2/eval2_cands.json"))
T = {}
for f in sorted(glob.glob(f"{W}/train2/train2_cands_*.json")): T.update(json.load(open(f)))
new = [(k, v, "J-eval", f"{W}/eval2/img/{k}.jpg") for k, v in sorted(E.items())] + [(k, v, "J-train", f"{W}/train2/img/{k}.jpg") for k, v in sorted(T.items())]
lic_rows, quar, kept = [], {}, {}
newA, newK = [], []
for k, v, split, img in new:
    if "size" not in v or not os.path.exists(img): quar[k] = ("download failed", split); continue
    ok, why = lic_ok(v)
    lic_rows.append(dict(key=k, source=v["source"], split=split, licence=v.get("licence"), author=v.get("author", ""), uploader=v.get("uploader", ""), credit=v.get("credit", ""),
                         source_url=v.get("page", ""), file_url=v.get("original_url") or v.get("url") or v.get("src_path", ""), licence_url=v.get("licence_url", ""),
                         compliant="yes" if ok else "no", issue=why))
    if not ok: quar[k] = (f"licence: {why}", split); continue
    h = str(imagehash.phash(Image.open(img).convert("RGB")))
    if h in BLANK: quar[k] = ("blank hash", split); continue
    b = bits(h); dref = int((RA ^ b).sum(1).min()); dj = (JA ^ b).sum(1); jmin = int(dj.min()); jk = JK[int(dj.argmin())]
    if dref <= 10: quar[k] = (f"near-dup of an earlier reference set (Hamming {dref})", split); continue
    if jmin <= 10: quar[k] = (f"near-dup (Hamming {jmin}) of Stage J item {jk} ({J[jk][1]})", split); continue
    # separation
    clash = [pk for pk in pkeys(v) if owner.get(pk, split) != split]
    if clash: quar[k] = (f"{clash[0]} already owned by {owner[clash[0]]} (source separation)", split); continue
    if newA:
        d = (np.array(newA) ^ b).sum(1); j = int(d.argmin())
        if d[j] <= 10:
            kj = newK[j]; sj = kept[kj]["split"]
            if sj != split: quar[k] = (f"near-dup (Hamming {int(d[j])}) of new {sj} item {kj}", split); continue
            if d[j] <= 6: quar[k] = (f"within-split near-dup (Hamming {int(d[j])}) of {kj}: same group, one representative kept", split); continue
    for pk in pkeys(v): owner.setdefault(pk, split)
    kept[k] = dict(split=split, source=v["source"], label=v["label"], kind=v.get("group"), uploader=v.get("uploader", ""), author=v.get("author", ""),
                   page=v.get("page", ""), licence=v.get("licence"), phash=h, ref_dmin=dref, j_dmin=jmin, src_path=v.get("src_path", ""), title=v.get("title", ""))
    newA.append(b); newK.append(k)
json.dump(kept, open(f"{GO}/j2_candidates.json", "w"), indent=0)
with open(f"{GO}/j2_licence.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(lic_rows[0])); w.writeheader(); w.writerows(lic_rows)
with open(f"{GO}/j2_quarantine.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["key", "intended_split", "reason"]); [w.writerow([k, s, r]) for k, (r, s) in sorted(quar.items())]
C = collections.Counter
summ = dict(new_candidates=len(new), licence_checked=len(lic_rows), licence_noncompliant=sum(r["compliant"] == "no" for r in lic_rows), kept=len(kept),
            quarantined=len(quar), quarantine_reasons=C(re.sub(r"\(.*|[0-9]+", "", r).strip() for r, _ in quar.values()),
            kept_eval_by_label=C(v["label"] for v in kept.values() if v["split"] == "J-eval"),
            kept_train_by_label=C(v["label"] for v in kept.values() if v["split"] == "J-train"),
            kept_train_by_source_label=C(f"{v['source']}|{v['label']}" for v in kept.values() if v["split"] == "J-train"),
            quarantined_by_source=C(k[:4] for k in quar), reference_hashes=len(ref), stage_j_hashes=len(JK), m_test_content_opened=False)
json.dump(summ, open(f"{GO}/j2_audit_summary.json", "w"), indent=1); print(json.dumps(summ, indent=1))
