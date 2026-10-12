"""Sultana et al. 'Fresh and Rotten Fruits' ORIGINALS via Hugging Face
Project-AgML/fresh_rotten_fruit_classification (config 'raw' = originals, no augmented copies).

Idempotent + resumable: skips files that already exist with non-zero size; writes a
sha256 checksum log. Signed image URLs from the datasets-server expire (~20 min), so
URLs are refreshed page by page right before downloading.

Usage:
  python ml/data/sources/sultana_agml.py --out $NUTRISOLE_DATA/raw/sultana --fruits apple banana guava orange pomegranate
Env: NUTRISOLE_DATA (default /workspace/work/cv/g1data). No credentials needed.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import urllib.request

DS = "Project-AgML/fresh_rotten_fruit_classification"
ROWS = "https://datasets-server.huggingface.co/rows?dataset={ds}&config=raw&split=train&offset={o}&length=100"
LABELS = {0: "fresh", 1: "rotten"}  # verified from the dataset's ClassLabel names


def page(offset: int) -> list:
    with urllib.request.urlopen(ROWS.format(ds=DS, o=offset), timeout=60) as r:
        d = json.load(r)
    return [(x["row_idx"], x["row"]["label"], x["row"]["fruit_type"], x["row"]["image"]["src"]) for x in d["rows"]]


def fetch(row, out):
    idx, lab, fruit, url = row
    p = os.path.join(out, f"{fruit}_{lab}_{idx:05d}.jpg")
    if os.path.exists(p) and os.path.getsize(p) > 0:
        return p, "skip"
    data = urllib.request.urlopen(url, timeout=120).read()
    with open(p + ".part", "wb") as fh:
        fh.write(data)
    os.replace(p + ".part", p)
    return p, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.environ.get("NUTRISOLE_DATA", "/workspace/work/cv/g1data"), "sultana/raw"))
    ap.add_argument("--fruits", nargs="+", default=["apple", "banana", "guava", "orange", "pomegranate"])
    ap.add_argument("--total", type=int, default=3200)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for off in range(0, a.total, 100):
        rows = [r for r in page(off) if r[2] in a.fruits]
        with cf.ThreadPoolExecutor(16) as ex:
            list(ex.map(lambda r: fetch(r, a.out), rows))
    with open(os.path.join(a.out, "..", "SHA256SUMS"), "w") as fh:
        for f in sorted(os.listdir(a.out)):
            if f.endswith(".jpg"):
                fh.write(hashlib.sha256(open(os.path.join(a.out, f), "rb").read()).hexdigest() + "  " + f + "\n")


if __name__ == "__main__":
    main()
