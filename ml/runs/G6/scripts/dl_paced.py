#!/usr/bin/env python3
"""G6.2 paced Commons downloader: one file at a time, 45 s gap, exponential backoff on 429/failure (max 3 tries/file/run).
Idempotent: skips files already in raw/ (>10 kB). Logs to ../g6logs/commons_dl.log. Same URL logic as dl.py."""
import json, subprocess, os, time, hashlib
os.chdir("/workspace/work/cv/g6src")
S = json.load(open("meta/commons_selected.json"))
LOG = "/workspace/work/cv/g6logs/commons_dl.log"
def log(m): open(LOG, "a").write(time.strftime("%H:%M:%S ") + m + "\n")
def tc(s):
    u = s["url"].split("?")[0]; base = u.split("/commons/", 1)[1]; name = base.rsplit("/", 1)[1]
    if max(s["w"], s["h"]) > 1280 or not u.endswith(".webm"):
        for r in ["720p.vp9.webm", "720p.webm", "480p.vp9.webm", "480p.webm"]:
            if min(s["w"], s["h"]) < int(r[:3]): continue
            yield f"https://upload.wikimedia.org/wikipedia/commons/transcoded/{base}/{name}.{r}"
    yield u
for s in S:
    h = hashlib.md5(s["title"].encode()).hexdigest()[:8]; out = f"raw/c{h}.webm"
    if os.path.exists(out) and os.path.getsize(out) > 10000: continue
    if os.path.exists("/workspace/work/cv/g6logs/STOP_DL"): break
    ok = False
    for attempt in range(3):
        for u in tc(s):
            r = subprocess.run(["curl", "-sL", "--max-time", "300", "-w", "%{http_code}", "-A",
                                "NutriSoleResearch/0.2 (FYP CV benchmark; muhammadfaizanali18@gmail.com)", "-o", out + ".part", u],
                               capture_output=True, text=True)
            code = r.stdout.strip()
            if code == "200" and os.path.getsize(out + ".part") > 10000:
                os.rename(out + ".part", out); log(f"OK {out} {code} {os.path.getsize(out)//1024}KB {u[-50:]}"); ok = True; break
            log(f"try{attempt} {code} {s['title'][:60]} {u[-30:]}")
            if code == "429": break
            time.sleep(5)
        if ok: break
        time.sleep(120 * (2 ** attempt))
    if not ok: log(f"FAIL {s['title']}")
    time.sleep(45)
log("PASS_DONE")
