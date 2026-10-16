# G6 close: verify locked splits (test, test_rf, neg_test, test_oiv7, test_oiv7c) + gauntlet clips are byte-identical to G5 (content sha256),
# and the web-mandi holdout/dev files match ml/runs/G6/video_benchmark/locked_hashes.json.
import hashlib, os, json, glob
R = "/workspace/work/nutrisole/ml/runs"
G5 = json.load(open(f"{R}/G5/locked_hashes.json")); out = {}
lists = {sp: f"/workspace/work/cv/g3data/det_v3/{sp}.txt" for sp in ["test", "test_rf", "neg_test", "test_oiv7"]}; lists["test_oiv7c"] = "/workspace/work/cv/g4data/test_oiv7c.txt"
for sp, p in lists.items():
    files = [l.strip() for l in open(p) if l.strip()]
    lh = hashlib.sha256("\n".join(os.path.basename(f) for f in files).encode()).hexdigest(); h = hashlib.sha256()
    for f in files:
        h.update(open(f, "rb").read()); lp = f.replace("/images/", "/labels/")[:-4] + ".txt"; h.update(open(lp, "rb").read() if os.path.exists(lp) else b"")
    ref = G5.get(sp, {})
    out[sp] = dict(n=len(files), list_sha256=lh, content_sha256=h.hexdigest(), g5_content_sha256=ref.get("content_sha256"),
                   g5_list_sha256=ref.get("list_sha256"), identical_to_g5=(ref.get("content_sha256") == h.hexdigest() and ref.get("list_sha256") == lh) if ref else None)
clips = {}
for d in ["/workspace/work/cv/g1clips", "/workspace/work/cv/g2clips_negtest"]:
    for f in sorted(glob.glob(d + "/**/*", recursive=True)):
        if os.path.isfile(f) and f.endswith((".mp4", ".json", ".avi")): clips[f.replace("/workspace/work/cv/", "")] = hashlib.sha256(open(f, "rb").read()).hexdigest()
out["clips_sha256"] = clips; out["clips_identical_to_g5"] = clips == G5.get("clips_sha256")
wm = {}
p = f"{R}/G6/video_benchmark/locked_hashes.json"
if os.path.exists(p):
    L = json.load(open(p)); items = L.get("files", L) if isinstance(L, dict) else {}
    ok = 0; bad = []; miss = []
    for k, v in (items.items() if isinstance(items, dict) else []):
        sha = v if isinstance(v, str) else (v.get("sha256") if isinstance(v, dict) else None)
        if not sha: continue
        cand = [c for c in [k] + sorted(glob.glob(f"/workspace/work/cv/g6src/raw/{k}.*")) if os.path.isfile(c)]
        if not cand: miss.append(k); continue
        (ok := ok + 1) if hashlib.sha256(open(cand[0], "rb").read()).hexdigest() == sha else bad.append(k)
    wm = dict(checked=ok + len(bad), match=ok, mismatch=bad, missing=miss)
out["web_mandi"] = wm
json.dump(out, open(f"{R}/G6/locked_hashes.json", "w"), indent=1)
print({k: (v["identical_to_g5"], v["n"]) for k, v in out.items() if isinstance(v, dict) and "n" in v}, "clips identical:", out["clips_identical_to_g5"], "web_mandi:", {k: (v if isinstance(v, int) else len(v)) for k, v in wm.items()})
