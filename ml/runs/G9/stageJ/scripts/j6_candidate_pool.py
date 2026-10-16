"""G9 Stage J6: second batch of UNVERIFIED training candidates, reusing j5_candidate_pool.py unchanged (same licence filter, banned-origin
filter, eval/dev person exclusion, 57,575-hash reference dedupe). Additions only:
  * queries favour the apple / orange / tomato / banana shortfalls with smartphone close-ups, Pakistani markets, transparent packaging,
    partial occlusion, varied light/size/ripeness/angle; plus HARD NEGATIVES (persimmon, printed/painted produce, plastic fruit,
    unrelated round objects) tagged query_class=hard_negative_* (never a supported label; annotators decide);
  * dedupe also against the 162 J5 candidates (pHash <= 6) and their titles, so the two pools never overlap.
Every row: CANDIDATE_UNVERIFIED, provenance NONE, split J-train-candidate, eval_eligible no. Pixels outside Git (/workspace/work/g9j6/cands/img).
  python3 j6_candidate_pool.py meta [group]   # group: fruit | neg | all (default all)
  python3 j6_candidate_pool.py dl 90
  python3 j6_candidate_pool.py audit
"""
from __future__ import annotations
import csv, hashlib, json, sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j5_candidate_pool as P5   # noqa: E402
import j_team_phone as T         # noqa: E402

J5W = Path("/workspace/work/g9j5/cands"); J5CSV = HERE.parent / "out/j5/candidates/j5_candidate_pool.csv"
P5.W = Path("/workspace/work/g9j6/cands"); P5.OUT = HERE.parent / "out" / "j6" / "candidates"
FRUIT = {
    "apple": ["apple close-up", "apples plastic bag", "apples market stall", "apples Lahore", "apple fruit vendor", "green apples", "apples crate market",
              "apple held hand close", "apples shop display", "apples ripe tree close", "apple bitten", "apples in net bag"],
    "citrus_orange": ["kinnow Pakistan", "oranges plastic bag", "oranges market stall", "mandarins close-up", "orange fruit close-up", "oranges cart vendor"],
    "tomato": ["tomatoes plastic bag", "tomatoes market stall", "tomato close-up", "tomatoes vendor Pakistan", "green tomatoes", "tomatoes crate"],
    "banana": ["bananas market stall", "bananas cart vendor", "banana close-up", "bananas Pakistan", "bananas plastic bag", "ripe bananas spots"],
}
NEG = {
    "hard_negative_persimmon": ["persimmon fruit", "persimmons market"],
    "hard_negative_printed": ["fruit painting still life", "fruit poster", "fruit stickers"],
    "hard_negative_artificial": ["plastic fruit", "artificial fruit"],
    "hard_negative_object": ["red ball", "orange ball", "yellow toy"],
}


def j5_seed():
    titles, hashes = set(), []
    for v in json.loads((J5W / "cands.json").read_text()).values(): titles.add(v.get("title"))
    with open(J5CSV, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["status"] == "CANDIDATE_UNVERIFIED": hashes.append((r["cand_id"], r["phash"]))
    return titles, hashes


def meta(group="all"):
    P5.QUERIES = {**(FRUIT if group in ("fruit", "all") else {}), **(NEG if group in ("neg", "all") else {})}
    titles, _ = j5_seed(); orig = P5.prior_titles
    P5.prior_titles = lambda: orig() | titles
    P5.meta()
    D = json.loads((P5.W / "cands.json").read_text())   # re-key j5c -> j6c so ids never collide with the J5 pool
    D = {("j6c" + k[3:] if k.startswith("j5c") else k): dict(v, source="commons_j6") for k, v in D.items()}
    (P5.W / "cands.json").write_text(json.dumps(D, indent=0))


def audit():
    D = json.loads((P5.W / "cands.json").read_text()); _, seed = j5_seed()
    R = T.RefIndex(T.load_refs()); kept, rows, st = list(seed), [], Counter()
    for k, v in sorted(D.items()):
        p = P5.W / "img" / f"{k}.jpg"
        if not p.exists(): st["not_downloaded"] += 1; continue
        h = T.phash(p); d, hit = R.nearest(h); status, why = "CANDIDATE_UNVERIFIED", ""
        if d <= 10: status, why = "DROPPED", f"pHash {d} to earlier set {hit[2]}"
        else:
            near = [(bin(int(h, 16) ^ int(x, 16)).count("1"), kk) for kk, x in kept]
            if near and min(near)[0] <= 6: status, why = "DROPPED", f"near-dup of {min(near)[1]} ({min(near)[0]})"
        if status != "DROPPED": kept.append((k, h))
        st[status] += 1
        rows.append(dict(cand_id=k, status=status, drop_reason=why, split="J-train-candidate", eval_eligible="no", provenance="NONE", human_verified="no",
                         query_class=v["query_class"], query=v["query"], title=v["title"], page_url=v["page"], file_url=v["original_url"], licence=v["licence"],
                         licence_url=v.get("licence_url", ""), author=v.get("author", ""), uploader=v.get("uploader", ""), credit=v.get("credit", ""),
                         orig_size="x".join(map(str, v["size"])), stored_sha256=hashlib.sha256(p.read_bytes()).hexdigest(), phash=h, ref_dmin=d))
    P5.OUT.mkdir(parents=True, exist_ok=True)
    with open(P5.OUT / "j6_candidate_pool.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    cand = [r for r in rows if r["status"] == "CANDIDATE_UNVERIFIED"]
    summ = dict(note="J6 batch of unverified TRAINING candidates (Commons per-file CC/PD, same filters as J5). Not labels; never eval; query word is metadata only.",
                searched=len(D), downloaded=len(rows), status=dict(st), candidates_by_query_class=dict(Counter(r["query_class"] for r in cand)),
                licences=dict(Counter(r["licence"] for r in cand)), dedupe="pHash <= 10 vs 57,575 reference hashes (incl. M-TEST stored hashes); <= 6 vs the 162 J5 candidates and within pool",
                reference_manifest_sha256=hashlib.sha256((HERE.parent / "out/j3_reference_hashes.json").read_bytes()).hexdigest(),
                banned_sources="Pexels, Pixabay, Mixkit, Unsplash and stock-site credits refused", pixels=str(P5.W / "img") + " (not in Git)")
    (P5.OUT / "j6_candidate_pool_summary.json").write_text(json.dumps(summ, indent=1)); print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "meta": meta(sys.argv[2] if len(sys.argv) > 2 else "all")
    elif m == "dl": P5.dl(float(sys.argv[2]))
    else: audit()
