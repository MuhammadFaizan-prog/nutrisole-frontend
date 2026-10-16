"""Price reference for one graded item. EXACT mirror: native/src/cv/prices/reference.ts
(parity fixture ml/prices/fixtures/reference_parity.json, replayed by native/tests/cvPrices.test.ts).

Rules (G3_next.md item 5):
  grade A -> grade-1 retail price, grade B -> grade-2 retail price; C / Reject / ungradable -> no price + note.
  Source priority: Lahore retail list (stale when list_date is more than 2 days old) -> AMIS wholesale
  (no grade split, labelled wholesale) -> PBS SPI (stale after 7 days; not implemented in G4).
  The range covers every variety row of that class with the same unit (varieties are listed, never merged silently).
  A class with no matching row gets no price. Always returns the source name, URL, list date and staleness.
  A reference, never an offer or a valuation."""
from __future__ import annotations

import datetime as dt

STALE_DAYS = {"retail": 2, "wholesale": 2, "national weekly average": 7}
GRADE_COL = {"A": "grade1_rs", "B": "grade2_rs"}
NOTE_LOW = "Below market grade; expect a discount. No reference price shown."


def _age(list_date: str | None, today: str) -> int | None:
    if not list_date:
        return None
    return (dt.date.fromisoformat(today) - dt.date.fromisoformat(list_date)).days


def price_reference(app_class: str, app_grade: str, sources: list[dict], today: str) -> dict:
    """sources: parsed source dicts in priority order (retail lists first, then AMIS, then SPI)."""
    if app_grade not in GRADE_COL:
        return dict(status="no_price", reason="grade_below_market" if app_grade in ("C", "Reject") else "ungradable",
                    note=NOTE_LOW if app_grade in ("C", "Reject") else "No grade, so no reference price.")
    fallback = None
    for src in sources:
        ptype = src.get("price_type", "retail")
        age = _age(src.get("list_date"), today)
        stale = age is None or age > STALE_DAYS.get(ptype, 2)
        col = GRADE_COL[app_grade] if ptype == "retail" else "wholesale_rs"
        rows = [r for r in src.get("rows", []) if r.get("app_class") == app_class and r.get(col) is not None]
        if not rows:
            continue
        unit = rows[0]["unit"]  # first row's unit; rows in another unit are listed separately
        same = [r for r in rows if r["unit"] == unit]
        vals = [r[col] for r in same]
        ref = dict(status="ok", app_class=app_class, app_grade=app_grade, price_type=ptype, list_grade=("grade 1" if app_grade == "A" else "grade 2") if ptype == "retail" else None,
                   min_rs=min(vals), max_rs=max(vals), unit=unit, varieties=[r.get("item_en") for r in same],
                   other_unit_rows=[dict(item_en=r.get("item_en"), unit=r["unit"], rs=r[col]) for r in rows if r["unit"] != unit],
                   source=src.get("source"), source_url=src.get("source_url"), list_date=src.get("list_date"), age_days=age, stale=stale,
                   disclaimer="Official reference price, not an offer or a valuation.")
        if not stale:
            return ref
        fallback = fallback or ref
    return fallback or dict(status="no_price", reason="class_not_listed", note="This item is not on today's official lists.")
