#!/usr/bin/env python3
"""G6.2 external real-video benchmark manifest ("web-mandi", Wikimedia Commons only). Re-runnable; split is
deterministic and computed over ALL selected clips (downloaded or not) so later downloads do not move clips between splits.
Rules: per-file licence CC0 / PD / CC BY / CC BY-SA only; split by UPLOADER (recording identity proxy); holdout >= 40% of
clips; no uploader > 25% of the holdout; clips already used for training anything (G5 hard-negative mining) -> 'train_only'.
Outputs: ml/runs/G6/video_benchmark/manifest.csv, manifest.json, locked_hashes.json (sha256 of downloaded holdout+dev files).
Never labels external footage as Lahore footage."""
import json, csv, os, hashlib, subprocess, re, collections, random
SRC = "/workspace/work/cv/g6src"; OUT = "/workspace/work/nutrisole/ml/runs/G6/video_benchmark"; os.makedirs(OUT, exist_ok=True)
S = json.load(open(f"{SRC}/meta/commons_selected.json"))
G5 = {x["title"] for x in json.load(open("/workspace/work/cv/g5data/video/sources.json"))}
OKLIC = re.compile(r"^(CC0|CC BY(-SA)? [234]\.0|Public domain|PD)", re.I)
KW = {"banana": r"banana|kela", "apple": r"apple", "tomato": r"tomato", "citrus": r"orange|citrus|kinnow|malta|mandarin|tangerine",
      "lemon_lime": r"lemon|lime", "capsicum": r"capsicum|bell pepper|pepper|shimla", "carrot": r"carrot", "cucumber": r"cucumber",
      "guava": r"guava", "mango": r"mango", "pomegranate": r"pomegranate", "potato": r"potato"}


def probe(p):
    try:
        j = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", p],
                                      capture_output=True, text=True, timeout=60).stdout)
        v = [s for s in j["streams"] if s["codec_type"] == "video"][0]
        n, d = v.get("avg_frame_rate", "0/1").split("/")
        return dict(dur_s=round(float(j["format"]["duration"]), 2), fps=round(float(n) / float(d), 2) if float(d) else None,
                    w=v["width"], h=v["height"], codec=v["codec_name"])
    except Exception as e:
        return dict(probe_error=str(e)[:100])


rows = []
for s in S:
    h = hashlib.md5(s["title"].encode()).hexdigest()[:8]; f = f"{SRC}/raw/c{h}.webm"
    text = " ".join([s["title"], s.get("desc", "") or "", " ".join(s.get("cats", []))]).lower()
    cls = [k for k, r in KW.items() if re.search(r, text)]
    lic_ok = bool(OKLIC.match(s["licence"]))
    r = dict(clip_id=f"c{h}", title=s["title"], page=s["page"], uploader=s["uploader"], creator=s.get("artist", ""),
             licence=s["licence"], licence_url=s.get("licence_url", ""), licence_ok=lic_ok, region=s.get("region", ""),
             upload_date=s.get("date", ""), meta_dur_s=s.get("dur"), meta_w=s.get("w"), meta_h=s.get("h"),
             classes_from_metadata="|".join(cls) or "unknown", lighting="unannotated", location_note="from Commons metadata only; NOT Lahore",
             downloaded=os.path.exists(f) and os.path.getsize(f) > 10000, file=f if os.path.exists(f) else "",
             used_in_training=s["title"] in G5, annotation_status="unlabelled (needs human boxes + class + quality per segment)")
    if r["downloaded"]:
        r.update(probe(f)); r["sha256"] = hashlib.sha256(open(f, "rb").read()).hexdigest()
    rows.append(r)

# ---- uploader-grouped split (deterministic, seed 6)
ups = collections.Counter(r["uploader"] for r in rows if r["licence_ok"] and not r["used_in_training"])
n_ok = sum(ups.values()); cap = 0.25
order = sorted(ups, key=lambda u: (hashlib.md5(f"g6{u}".encode()).hexdigest()))
hold, n_hold = set(), 0
target = 0.4 * n_ok
for u in order:
    if n_hold >= target: break
    if ups[u] > cap * max(target, 1): continue  # a big uploader would dominate the holdout -> dev
    hold.add(u); n_hold += ups[u]
for r in rows:
    r["split"] = ("rejected_licence" if not r["licence_ok"] else "train_only(G5 hardneg source)" if r["used_in_training"]
                  else "holdout" if r["uploader"] in hold else "dev")
keys = list(rows[0].keys()) + [k for k in ["dur_s", "fps", "w", "h", "codec", "sha256", "probe_error"] if k not in rows[0]]
with open(f"{OUT}/manifest.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
summ = dict(n_selected=len(rows), n_downloaded=sum(r["downloaded"] for r in rows),
            split_counts=dict(collections.Counter(r["split"] for r in rows)),
            split_downloaded=dict(collections.Counter(r["split"] for r in rows if r["downloaded"])),
            n_uploaders=len({r["uploader"] for r in rows}), holdout_uploaders=sorted(hold),
            max_uploader_share_holdout=round(max([ups[u] for u in hold] or [0]) / max(1, n_hold), 3),
            dev_uploaders=dict(collections.Counter(r["uploader"] for r in rows if r["split"] == "dev")),
            classes_from_metadata=dict(collections.Counter(c for r in rows for c in r["classes_from_metadata"].split("|"))),
            regions=dict(collections.Counter(r["region"] for r in rows)), licences=dict(collections.Counter(r["licence"] for r in rows)),
            total_downloaded_minutes=round(sum(r.get("dur_s", 0) or 0 for r in rows) / 60, 1),
            target_independent_clips=60, note="38 selected Commons files < 60 target; clips are not labelled; uploader is the recording-identity proxy")
json.dump(dict(summary=summ, clips=rows), open(f"{OUT}/manifest.json", "w"), indent=1)
lock = {r["clip_id"]: dict(split=r["split"], sha256=r.get("sha256")) for r in rows if r["split"] in ("holdout", "dev")}
json.dump(lock, open(f"{OUT}/locked_hashes.json", "w"), indent=1)
print(json.dumps(summ, indent=1))
