"""Lahore Market Committee / PAMRA daily RETAIL rate lists (grade 1 = اول, grade 2 = دوم), fruit and vegetable.

Pages (official, District Lahore, Government of Punjab):
  https://lahore.punjab.gov.pk/fruits-rate-list
  https://lahore.punjab.gov.pk/vegetables-rate-list
Each page lists one row per date with a "Retail Price" link to a JPEG. We OCR the JPEG table
(ml/prices/grid.py), match each OCR'd Urdu name to the hand-built lexicon (ml/prices/lexicon.py)
with a one-to-one assignment, and DROP rows whose name does not match or whose numbers do not read.
Fetch at most once a day (respect the site)."""
from __future__ import annotations

import datetime as dt
import difflib
import html
import re
import unicodedata
import urllib.parse
import urllib.request

import numpy as np

from .grid import parse_table
from .lexicon import LEXICON, POSITION

PAGES = {"fruit": "https://lahore.punjab.gov.pk/fruits-rate-list", "vegetable": "https://lahore.punjab.gov.pk/vegetables-rate-list"}
BASE = "https://lahore.punjab.gov.pk"
UA = {"User-Agent": "NutriSole-FYP-price-reference/0.1 (once-daily; research)"}
MIN_NAME_SCORE = 0.45   # below this an OCR'd name is "unmatched" -> row dropped ...
MIN_NAME_SCORE_AT_POS = 0.25  # ... unless the row also sits where the item sat on the reference layout
POS_BONUS = 0.35
MIN_NUM_CONF = 0.60     # tesseract word confidence floor for a price cell


def _get(url: str, timeout: int = 60) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()


def parse_index(page_html: str) -> list[dict]:
    """[{date: 'YYYY-MM-DD', retail_url, wholesale_url|None}] newest first, from the listing page HTML."""
    out = []
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", page_html, flags=re.S | re.I):
        row = m.group(1)
        d = re.search(r"([A-Z][a-z]{2}) (\d{1,2}), (\d{4})", row)
        links = re.findall(r'href="(/system/files\?file=[^"]+)"', row)
        if not d or not links:
            continue
        date = dt.datetime.strptime(" ".join(d.groups()), "%b %d %Y").date().isoformat()
        out.append(dict(date=date, retail_url=BASE + html.unescape(links[0]), wholesale_url=BASE + html.unescape(links[1]) if len(links) > 1 else None))
    return sorted(out, key=lambda r: r["date"], reverse=True)


def norm_ur(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ه": "ہ", "ة": "ہ", "ۀ": "ہ", "ھ": "ھ", "أ": "ا", "آ": "ا", "ئ": "ی", "ۓ": "ے"}))
    s = re.sub(r"[\u064B-\u065F\u0670\u06D6-\u06ED]", "", s)  # diacritics
    return re.sub(r"[^\u0600-\u06FF]", "", s)


def name_score(a: str, b: str) -> float:
    a, b = norm_ur(a), norm_ur(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def match_rows(rows: list[dict], kind: str) -> list[dict]:
    """One-to-one assignment of OCR rows to lexicon items maximising name similarity (Hungarian)."""
    from scipy.optimize import linear_sum_assignment
    lex = LEXICON[kind]
    pos = POSITION[kind]
    S = np.array([[name_score(r["name_ocr"], e[0]) for e in lex] for r in rows]) if rows else np.zeros((0, len(lex)))
    P = np.array([[float((r["block"], r["row"]) == pos[j]) for j in range(len(lex))] for r in rows]) if rows else np.zeros((0, len(lex)))
    ri, ci = linear_sum_assignment(-(S + POS_BONUS * P)) if len(rows) else ([], [])
    best = {int(i): (int(j), float(S[i, j]), bool(P[i, j])) for i, j in zip(ri, ci)}
    out = []
    for i, r in enumerate(rows):
        j, s, at_pos = best.get(i, (None, 0.0, False))
        ok = j is not None and (s >= MIN_NAME_SCORE or (at_pos and s >= MIN_NAME_SCORE_AT_POS))
        e = lex[j] if ok else None
        out.append({**r, "item_ur": e[0] if e else None, "item_en": e[1] if e else None, "app_class": e[2] if e else None,
                    "unit": e[3] if e else None, "name_score": round(s, 3), "at_layout_pos": at_pos})
    return out


def parse_list(img_bgr, kind: str, list_date: str, source_url: str) -> dict:
    t = parse_table(img_bgr)
    rows = match_rows(t["rows"], kind) if t["ok"] else []
    kept, dropped = [], []
    for r in rows:
        why = None
        if r["item_ur"] is None:
            why = "name_unmatched"
        elif r["grade1"] is None and r["grade1_raw"] not in ("-", "") or r["grade2"] is None and r["grade2_raw"] not in ("-", ""):
            why = "number_unreadable"
        elif r["num_conf"] < MIN_NUM_CONF and (r["grade1"] is not None or r["grade2"] is not None):
            why = "low_ocr_confidence"
        elif r["grade1"] is not None and r["grade2"] is not None and r["grade2"] > r["grade1"]:
            why = "grade2_above_grade1"  # sanity rule: grade 2 is never dearer than grade 1 on these lists
        rec = dict(item_ur=r["item_ur"], item_en=r["item_en"], app_class=r["app_class"], unit=r["unit"],
                   grade1_rs=r["grade1"], grade2_rs=r["grade2"], name_ocr=r["name_ocr"], name_score=r["name_score"],
                   ocr_confidence=round(min(r["num_conf"], 1.0), 3), confidence=round(min(r["num_conf"], r["name_score"] + 0.3, 1.0), 3))
        (dropped if why else kept).append({**rec, **({"dropped": why} if why else {})})
    return dict(source="Market Committee Lahore / PAMRA retail rate list", source_page=PAGES[kind], source_url=source_url, kind=kind,
                list_date=list_date, price_type="retail", currency="PKR", grid_ok=t["ok"], grid_error=t.get("error"),
                rows=kept, dropped_rows=dropped)


def fetch_latest(kind: str, workdir: str) -> dict:
    """Download the newest retail JPEG for `kind` and parse it. Network: two GETs."""
    import cv2
    idx = parse_index(_get(PAGES[kind]).decode("utf-8", "ignore"))
    if not idx:
        return dict(source_page=PAGES[kind], error="no dated rows on the listing page", rows=[])
    top = idx[0]
    p = f"{workdir}/{kind}_{top['date']}.jpeg"
    open(p, "wb").write(_get(top["retail_url"]))
    res = parse_list(cv2.imread(p), kind, top["date"], top["retail_url"])
    res["fetched_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    return res
