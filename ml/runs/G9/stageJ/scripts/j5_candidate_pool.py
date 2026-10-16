"""G9 Stage J5: phone-style TRAINING candidate pool from allowed licences only (user approval 2026-10-15 22:53 PKT: collect missing orange
training photos and apple/banana/tomato shortfalls; the sandbox cannot take photos, so this only gathers CANDIDATES).

Allowed: Wikimedia Commons per-file CC BY / CC BY-SA / CC0 / PD (extmetadata LicenseShortName; NonFree false; no NC/ND).
Refused: any Pexels, Pixabay, Mixkit or Unsplash origin (title, credit, artist, description), stock-site credits, drawings/logos.
Zenodo CC BY was considered; no record was added in this run (see the summary's `zenodo` note).

Every candidate is:
  * status CANDIDATE_UNVERIFIED, provenance NONE (no label: the query word is search metadata only), split J-train-candidate, NEVER eval;
  * person-separated: uploader/artist must not own any J-eval / J-dev item (Stage J and J2 partitions) or a J2 eval2 item;
  * pHash-deduplicated: dropped if Hamming <= 10 to ANY set in out/j3_reference_hashes.json (57,575 hashes incl. M-TEST stored hashes,
    J-eval, J-train) or <= 6 to another candidate in this pool.
Pixels are stored outside Git (<= 640 px) in /workspace/work/g9j5/cands/img; Git gets only the attribution/licence CSV and summary.
  python3 j5_candidate_pool.py meta      # search + licence + person filters -> cands.json
  python3 j5_candidate_pool.py dl 90     # download for up to 90 s (resumable)
  python3 j5_candidate_pool.py audit     # pHash dedupe + write out/j5/candidates/*
"""
from __future__ import annotations
import csv, hashlib, io, json, os, re, sys, time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j2_collect_commons as C   # noqa: E402  (csearch: licence + banned-origin filters)
import j_team_phone as T         # noqa: E402  (load_refs / RefIndex: committed earlier-reference manifest)

W = Path("/workspace/work/g9j5/cands"); OUT = HERE.parent / "out" / "j5" / "candidates"
QUERIES = {   # hand-held / everyday phone-style scenes; train-side only
    "citrus_orange": ["orange fruit in hand", "kinnow", "kinnow mandarin", "oranges kitchen table", "mandarin orange peeled table", "oranges fruit basket home",
                      "orange fruit on plate", "oranges market Pakistan", "malta orange fruit", "tangerines bowl"],
    "apple": ["apple in hand", "apples kitchen counter", "apple on desk", "apples fruit bowl home", "apples market Pakistan", "red apple plate"],
    "banana": ["bananas kitchen", "banana in hand", "bananas fruit bowl", "bananas market Pakistan"],
    "tomato": ["tomatoes kitchen", "tomato in hand", "tomatoes bowl", "tomatoes market Pakistan", "tomatoes cutting board whole"],
}
STOCK = re.compile(r"unsplash|pixabay|pexels|mixkit|shutterstock|istock|getty|adobe ?stock|dreamstime|123rf|freepik", re.I)
ALLOWED = re.compile(r"^(CC BY(-SA)? ?\d(\.\d)?|CC0|Public domain|PD.*)", re.I)


def persons_eval_dev():
    P = json.load(open(HERE.parent / "out/j_partitions.json"))["items"]; ks = set()
    for v in P.values():
        if v["split"] in ("J-eval", "J-dev") and v["source"] in ("commons", "commons_t"):
            ks |= {k for k in (("u:" + (v.get("uploader") or "").lower()) if v.get("uploader") else "", ("a:" + C.norm(v.get("artist"))[:80]) if v.get("artist") else "") if k}
    try:
        for v in json.load(open("/workspace/work/g9j2/eval2/eval2_cands.json")).values():
            if v.get("uploader"): ks.add("u:" + v["uploader"].lower())
            if v.get("author"): ks.add("a:" + C.norm(v["author"])[:80])
    except FileNotFoundError: pass
    return ks


def prior_titles():
    t = set()
    for p in ("/workspace/work/g9j2/eval2/eval2_cands.json", "/workspace/work/g9j2/train2/train2_cands_commons.json", "/workspace/work/g9i/cands/cands.json",
              "/workspace/work/g9j/train/train_cands.json", "/workspace/work/g9h/hset/cands.json", "/workspace/work/g9g/cu/cands.json"):
        try:
            d = json.load(open(p)); t |= {v.get("title") for v in (d.values() if isinstance(d, dict) else d)}
        except Exception: pass
    return t


def meta():
    W.mkdir(parents=True, exist_ok=True); J = W / "cands.json"
    D = json.loads(J.read_text()) if J.exists() else {}
    bad_people, prior = persons_eval_dev(), prior_titles() | {v["title"] for v in D.values()}
    jobs = [(c, q) for c, qs in QUERIES.items() for q in qs]
    with ThreadPoolExecutor(3) as ex: res = list(ex.map(lambda j: (j, C.csearch(j[1], 30)), jobs))
    st = Counter()
    for (c, q), rs in res:
        for r in rs:
            if r["title"] in prior: st["dup_title"] += 1; continue
            if STOCK.search(" ".join(str(r.get(k, "")) for k in ("title", "credit", "author"))): st["stock_origin"] += 1; continue
            if not ALLOWED.search(r["licence"] or "") or re.search(r"\bNC\b|\bND\b|-nc|-nd", r["licence"], re.I): st["licence"] += 1; continue
            pk = {k for k in (("u:" + r["uploader"].lower()) if r.get("uploader") else "", ("a:" + C.norm(r["author"])[:80]) if r.get("author") else "") if k}
            if pk & bad_people: st["eval_dev_person"] += 1; continue
            prior.add(r["title"]); st["kept"] += 1
            D["j5c" + hashlib.sha1(r["title"].encode()).hexdigest()[:8]] = dict(source="commons_j5", query_class=c, **r)
    J.write_text(json.dumps(D, indent=0)); print(dict(st), "pool", len(D))


def dl(limit):
    from PIL import Image
    J = W / "cands.json"; D = json.loads(J.read_text()); (W / "img").mkdir(exist_ok=True); t0 = time.time(); n = 0
    for k, v in D.items():
        if "size" in v or v.get("fail"): continue
        if time.time() - t0 > limit: break
        try:
            im = Image.open(io.BytesIO(C.get(v["url"], 30))).convert("RGB"); w, h = im.size; s = min(1.0, 640 / max(w, h))
            if s < 1: im = im.resize((round(w * s), round(h * s)), Image.LANCZOS)
            im.save(W / "img" / f"{k}.jpg", quality=88); v["size"] = [w, h]; n += 1; time.sleep(0.3)
        except Exception as e: v["fail"] = str(e)[:80]
    J.write_text(json.dumps(D, indent=0))
    print("downloaded", n, "have", sum("size" in v for v in D.values()), "/", len(D))


def audit():
    J = W / "cands.json"; D = json.loads(J.read_text())
    R = T.RefIndex(T.load_refs()); kept, rows, st = [], [], Counter()
    for k, v in sorted(D.items()):
        p = W / "img" / f"{k}.jpg"
        if not p.exists(): st["not_downloaded"] += 1; continue
        h = T.phash(p); d, hit = R.nearest(h)
        status, why = "CANDIDATE_UNVERIFIED", ""
        if d <= 10: status, why = "DROPPED", f"pHash {d} to earlier set {hit[2]}"
        else:
            near = [(bin(int(h, 16) ^ int(x, 16)).count("1"), kk) for kk, x in kept]
            if near and min(near)[0] <= 6: status, why = "DROPPED", f"within-pool near-dup of {min(near)[1]} ({min(near)[0]})"
        if status != "DROPPED": kept.append((k, h))
        st[status] += 1
        rows.append(dict(cand_id=k, status=status, drop_reason=why, split="J-train-candidate", eval_eligible="no", provenance="NONE", human_verified="no",
                         query_class=v["query_class"], query=v["query"], title=v["title"], page_url=v["page"], file_url=v["original_url"], licence=v["licence"],
                         licence_url=v.get("licence_url", ""), author=v.get("author", ""), uploader=v.get("uploader", ""), credit=v.get("credit", ""),
                         orig_size="x".join(map(str, v["size"])), stored_sha256=hashlib.sha256(p.read_bytes()).hexdigest(), phash=h, ref_dmin=d))
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "j5_candidate_pool.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    cand = [r for r in rows if r["status"] == "CANDIDATE_UNVERIFIED"]
    summ = dict(note="Unverified TRAINING candidates (Commons per-file CC/PD). Not labels; never eval; two independent annotators + adjudicator decide.",
                searched=len(D), downloaded=len(rows), status=dict(st), candidates_by_query_class=dict(Counter(r["query_class"] for r in cand)),
                licences=dict(Counter(r["licence"] for r in cand)), reference_manifest_sha256=hashlib.sha256((HERE.parent / "out/j3_reference_hashes.json").read_bytes()).hexdigest(),
                banned_sources="Pexels, Pixabay, Mixkit, Unsplash and stock-site credits refused", zenodo="not added this run (no record with phone-style produce photos and per-record CC BY checked yet)",
                pixels="/workspace/work/g9j5/cands/img (not in Git)")
    (OUT / "j5_candidate_pool_summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    m = sys.argv[1]
    meta() if m == "meta" else dl(float(sys.argv[2])) if m == "dl" else audit()
