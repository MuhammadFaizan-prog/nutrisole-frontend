# NutriSole CV G8: auto-label MERGE step on Kaggle CPU (sandbox OOM). Runs ml/autolabel/merge.py unchanged, then builds a
# prioritised ~30-item hard-example human review queue (lemon/citrus confusion, guava, small objects, G3 vs OWLv2 disagreements)
# rendered as 3 contact-sheet JPGs. Everything here is PROPOSALS, never ground truth.
import glob, os, sys, json, csv, subprocess, shutil, tarfile, time
W = "/kaggle/working"; t0 = time.time()
def log(*a): print(f"[{time.time()-t0:7.1f}s]", *a, flush=True)
I = "/kaggle/input"
def find(pat):
    L = sorted(glob.glob(f"{I}/**/{pat}", recursive=True))
    return sorted(L, key=lambda p: 0 if "g8-merge" in p else 1)
kf = find("keyframes.json"); log("keyframes.json found", len(kf), kf[:2])
roots = sorted({os.path.dirname(os.path.dirname(p)) for p in kf if "/stage1/" in p}) or sorted({os.path.dirname(os.path.dirname(p)) for p in kf})
# keep the root with most clips
from collections import Counter
cnt = Counter(os.path.dirname(os.path.dirname(p)) for p in kf if os.path.exists(os.path.join(os.path.dirname(p), "frames.json"))); s1 = cnt.most_common(1)[0][0]; log("stage1 root", s1, cnt.most_common(3))
owl = [p for p in find("owlv2_keyframes.json")][0]; roles = find("roles.json")[0]; code = [p for p in find("merge.py") if "merge" in p]
log("owl", owl, "roles", roles, "merge.py", code)
merge_py = code[0]
vids = find("*.webm") + find("*.mp4") + find("*.mkv"); vdirs = sorted({os.path.dirname(v) for v in vids}); log("videos", len(vids), vdirs)
# pass the video dirs; merge.py globs <dir>/<clip>.*
os.makedirs(f"{W}/code", exist_ok=True); shutil.copy(merge_py, f"{W}/code/merge.py"); sys.path.insert(0, f"{W}/code")
OUT = f"{W}/autolabel"
cmd = [sys.executable, f"{W}/code/merge.py", "--stage1", s1, "--owl", owl, "--roles", roles, "--videos", *vdirs, "--out", OUT]
log("RUN", " ".join(cmd)); r = subprocess.run(cmd, capture_output=True, text=True); open(f"{W}/merge.log", "w").write(r.stdout + "\n--stderr--\n" + r.stderr)
log("merge rc", r.returncode, r.stderr[-2000:]);
if r.returncode != 0: sys.exit(1)
import merge as M, cv2, numpy as np
recs = [json.load(open(p)) for p in sorted(glob.glob(f"{OUT}/proposals/*.json"))]
CIT = {"citrus", "lemon_lime"}
def score(r, k):
    if r["role"] == "negative":
        hits = [b for b in k["boxes"] if ((b["g3"] or [0, 0])[1] >= 0.35) or ((b["owl"] or [0, 0])[1] >= 0.3)]
        return (1.5 * len(hits), ["negative_hit"] if hits else [])
    s, why = 0.0, set()
    for b in k["boxes"]:
        g = (b["g3"] or [None])[0]; o = (b["owl"] or [None])[0]; labs = {x for x in (g, o) if x}
        if b["status"] == "class_dispute":
            s += 2; why.add("g3_vs_owl_dispute")
            if labs <= CIT: s += 4; why.add("lemon_citrus_confusion")
            elif labs & CIT: s += 2; why.add("citrus_vs_other")
        elif b["status"] in ("owl_only", "g3_only"):
            s += 1; why.add(b["status"])
        if "guava" in labs: s += 2 if b["status"] != "agree" else 0.5; why.add("guava")
        if any(f.startswith("small_box") for f in b["flags"]): s += 1; why.add("small_object")
        if "temporal" in b["flags"]: s += 0.5
    return (s, sorted(why))
cand = []
for r in recs:
    for k in r["keyframes"]:
        s, why = score(r, k)
        if s > 0: cand.append((s, why, r, k))
cand.sort(key=lambda z: -z[0]); per, sel = Counter(), []
for c in cand:
    if per[c[2]["clip"]] >= 2: continue
    per[c[2]["clip"]] += 1; sel.append(c)
    if len(sel) >= 30: break
RV = f"{W}/review"; os.makedirs(f"{RV}/items", exist_ok=True)
vid = {os.path.splitext(os.path.basename(v))[0]: v for v in vids}
tiles = []
with open(f"{RV}/hard_review_queue.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["rank", "clip", "role", "keyframe", "fi", "t_s", "hard_score", "reasons", "boxes", "sheet", "tile", "verified_by", "verdict"])
    for i, (s, why, r, k) in enumerate(sel):
        p = f"{RV}/items/{i:02d}_{r['clip']}_{k['fi']}.jpg"
        if r["clip"] in vid:
            step = max(1, int(round((k["fi"] / max(k["t"], 1e-6)) / 4))) if k["t"] > 0 else 6
            M.sheet(vid[r["clip"]], r, k, p, step)
        bl = "; ".join(f"{b['status']}:{b['label']}" for b in k["boxes"])[:300]
        sheetno = i // 10 + 1
        w.writerow([i + 1, r["clip"], r["role"], k["file"], k["fi"], k["t"], round(s, 2), "|".join(why), bl, f"review_sheet_{sheetno}.jpg", i % 10 + 1, "", ""])
        tiles.append((i, p, why, s))
# 3 contact sheets x 10 items: each item = keyframe panel only (middle third) + caption
for sn in range(0, len(tiles), 10):
    rows = []
    for i, p, why, s in tiles[sn:sn + 10]:
        im = cv2.imread(p)
        if im is None: im = np.zeros((360, 1920, 3), np.uint8)
        h, wd = im.shape[:2]; im = cv2.resize(im, (1200, int(1200 * h / wd)))
        cap = np.full((26, 1200, 3), 30, np.uint8); cv2.putText(cap, f"#{i+1} score {s:.1f}  {', '.join(why)}"[:140], (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1)
        rows.append(np.vstack([cap, im]))
    cv2.imwrite(f"{RV}/review_sheet_{sn//10+1}.jpg", np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 82])
log("hard queue", len(sel), "sheets", len(glob.glob(f"{RV}/review_sheet_*.jpg")))
with tarfile.open(f"{W}/g8_merge_out.tgz", "w:gz") as t:
    t.add(OUT, arcname="autolabel"); t.add(RV, arcname="review")
shutil.rmtree(f"{W}/code", ignore_errors=True); log("DONE", json.dumps(json.load(open(f"{OUT}/summary.json")))[:500])
