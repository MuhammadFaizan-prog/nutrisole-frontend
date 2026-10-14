"""Stage G CU leakage + split. (1) Commons title overlap with every earlier Commons pool (Stage D/E/F manifests, incl. M-DEV and
M-TEST candidates: titles/hashes only, M-TEST images are NOT scored or viewed). (2) 64-bit pHash vs all earlier Commons images
(g9d/g9e/g9f img dirs) and DEV clip frames. (3) Split used items by uploader: CU-tune / CU-check (sha1(user) parity, ~60/40)."""
import json, glob, os, hashlib, cv2, numpy as np, re
B = "/workspace/work/nutrisole/ml/runs/G9/stageG"; C = json.load(open("/workspace/work/g9g/cu/cands.json")); T = json.load(open(f"{B}/cu_triage.json"))
def ph(im):
    g = cv2.resize(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), (32, 32), interpolation=cv2.INTER_AREA).astype(np.float32)
    d = cv2.dct(g)[:8, :8]; return int("".join("1" if v > np.median(d) else "0" for v in d.flatten()), 2)
titles = set()
for p in glob.glob("/workspace/work/cv/g9*/**/*.json", recursive=True) + glob.glob("/workspace/work/nutrisole/ml/runs/G9/stage[DEF]/*.csv") + glob.glob("/workspace/work/nutrisole/ml/runs/G9/stage[DEF]/*manifest*"):
    if os.path.getsize(p) > 30e6: continue
    try: titles |= set(re.findall(r"File:[^\"\n,|]+?\.(?:jpe?g|JPE?G|png)", open(p, errors="ignore").read()))
    except Exception: pass
import time; t0 = time.time(); HC = "/workspace/work/g9g/refhash.json"; hc = json.load(open(HC)) if os.path.exists(HC) else {}
for p in glob.glob("/workspace/work/cv/g9[def]/**/*.jpg", recursive=True):
    if "sheet" in p or "/dt_" in p or "/sl_" in p or p in hc: continue
    if time.time() - t0 > 80: json.dump(hc, open(HC, "w")); raise SystemExit(f"partial {len(hc)}")
    im = cv2.imread(p, cv2.IMREAD_REDUCED_COLOR_4)
    if im is not None: hc[p] = str(ph(im))
json.dump(hc, open(HC, "w")); refs = [int(v) for v in hc.values()]
res = {}; drop = []
for k, c in C.items():
    t = c["title"]; im = cv2.imread(f"/workspace/work/g9g/cu/img/{k}.jpg")
    if im is None: res[k] = dict(unreadable=True); drop.append(k); continue
    h = ph(im)
    dmin = int(min(bin(int(h) ^ int(r)).count("1") for r in refs)) if len(refs) else 99
    res[k] = dict(title_overlap=t in titles, phash_min=dmin)
    if t in titles or dmin <= 10: drop.append(k)
split = {}
for k in T["item"]:
    u = C["cu" + k]["user"] or C["cu" + k]["artist"]; split[k] = "tune" if int(hashlib.sha1(u.encode()).hexdigest(), 16) % 10 < 6 else "check"
out = dict(n_refs=int(len(refs)), n_ref_titles=len(titles), dropped=drop, per_image=res, split=split,
           split_counts={s: sum(v == s for v in split.values()) for s in ("tune", "check")})
json.dump(out, open(f"{B}/out/cu_leak_split.json", "w"), indent=1); print(len(refs), len(titles), drop, out["split_counts"])
