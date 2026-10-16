"""Daily job: fetch the newest official lists once and write <out>/prices_<YYYY-MM-DD>.json.
usage: python -m prices.build_daily --out <dir>   (run from ml/)"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os

from . import amis, rate_list, spi


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    sources, errors = [], []
    for kind in ("fruit", "vegetable"):
        try:
            sources.append(rate_list.fetch_latest(kind, a.out))
        except Exception as e:  # network/site errors are recorded, never papered over
            errors.append(f"{kind}: {e!r}")
    for mod in (amis, spi):
        try:
            sources.append(mod.fetch())
        except Exception as e:
            errors.append(f"{mod.__name__}: {e!r}")
    today = dt.date.today().isoformat()
    json.dump(dict(schema="nutrisole-price-ref/1", built=today, sources=sources, errors=errors), open(f"{a.out}/prices_{today}.json", "w"), ensure_ascii=False, indent=1)
    print(f"{a.out}/prices_{today}.json", [len(s.get("rows", [])) for s in sources], errors)


if __name__ == "__main__":
    main()
