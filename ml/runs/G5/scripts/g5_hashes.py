# G5: verify locked splits (test, test_rf, neg_test, test_oiv7, test_oiv7c) + gauntlet clips are byte-identical to G4 (content sha256).
import hashlib, os, json, glob
G4 = json.load(open("/workspace/work/nutrisole/ml/runs/G4/locked_hashes.json")); out = {}
lists = {sp: f"/workspace/work/cv/g3data/det_v3/{sp}.txt" for sp in ["test", "test_rf", "neg_test", "test_oiv7"]}; lists["test_oiv7c"] = "/workspace/work/cv/g4data/test_oiv7c.txt"
for sp, p in lists.items():
    files = [l.strip() for l in open(p) if l.strip()]
    lh = hashlib.sha256("\n".join(os.path.basename(f) for f in files).encode()).hexdigest(); h = hashlib.sha256()
    for f in files:
        h.update(open(f, "rb").read()); lp = f.replace("/images/", "/labels/")[:-4] + ".txt"; h.update(open(lp, "rb").read() if os.path.exists(lp) else b"")
    ref = G4.get(sp, {})
    out[sp] = dict(n=len(files), list_sha256=lh, content_sha256=h.hexdigest(), g4_content_sha256=ref.get("content_sha256"),
                   identical_to_g4=(ref.get("content_sha256") == h.hexdigest()) if ref else None)
clips = {}
for d in ["/workspace/work/cv/g1clips", "/workspace/work/cv/g2clips_negtest"]:
    for f in sorted(glob.glob(d + "/**/*", recursive=True)):
        if os.path.isfile(f) and f.endswith((".mp4", ".json", ".avi")): clips[f.replace("/workspace/work/cv/", "")] = hashlib.sha256(open(f, "rb").read()).hexdigest()
out["clips_sha256"] = clips; out["clips_identical_to_g4"] = clips == G4.get("clips_sha256")
json.dump(out, open("/workspace/work/nutrisole/ml/runs/G5/locked_hashes.json", "w"), indent=1)
print({k: (v["identical_to_g4"], v["n"]) for k, v in out.items() if isinstance(v, dict) and "n" in v}, "clips identical:", out["clips_identical_to_g4"])
