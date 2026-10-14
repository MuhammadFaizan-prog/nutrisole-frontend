"""G9 Stage G price display contract. EXACT mirror: native/src/cv/prices/display.ts. Built on reference.py; never computes a price.
Shown only for a verified category with a current (non-stale) official row; always source, list date, location, unit; labelled an
official reference, never a seller's price or a grade-adjusted value of the item. C / Reject -> no price; Not graded -> category line."""
from ml.prices.reference import price_reference

PRICE_LOCATION = {"Market Committee Lahore / PAMRA retail rate list": "Lahore",
                  "Punjab AMIS (amis.pk) average wholesale prices": "Lahore (Punjab AMIS wholesale)",
                  "PBS weekly SPI (national weekly average)": "Pakistan (national average)"}
PRICE_LABEL = "Official reference price, not this seller's price"


def _fmt(r, kind, loc, mn, mx, lg):
    rng = f"Rs {mn}" if mn == mx else f"Rs {mn}-{mx}"
    what = "official list range" if kind == "category_reference" else f"official list price, {lg}"
    return dict(kind=kind, text=f"{rng} per {r['unit']} ({what}; {r['source']}, {loc}, {r['list_date']})", source=r["source"], sourceUrl=r["source_url"],
                listDate=r["list_date"], location=loc, unit=r["unit"], minRs=mn, maxRs=mx, listGrade=lg, label=PRICE_LABEL)


def category_price(identified, app_class, sources, today):
    if not identified: return dict(show=False, reason="not_identified")
    ok = [r for r in (price_reference(app_class, g, sources, today) for g in ("A", "B")) if r["status"] == "ok" and not r["stale"] and r["list_date"]]
    cur = [r for r in ok if r["source"] == ok[0]["source"]] if ok else []
    if not cur: return dict(show=False, reason="no_current_official_price")
    loc = PRICE_LOCATION.get(cur[0]["source"])
    if not loc: return dict(show=False, reason="unknown_location")
    return dict(show=True, line=_fmt(cur[0], "category_reference", loc, min(r["min_rs"] for r in cur), max(r["max_rs"] for r in cur), None))


def graded_price(identified, app_class, grade, sources, today):
    if not identified: return dict(show=False, reason="not_identified")
    if grade not in ("A", "B"):
        return category_price(identified, app_class, sources, today) if grade is None else dict(show=False, reason="grade_below_list")
    r = price_reference(app_class, grade, sources, today)
    if r["status"] != "ok" or r["stale"] or not r["list_date"]: return dict(show=False, reason="no_current_official_price")
    loc = PRICE_LOCATION.get(r["source"])
    if not loc: return dict(show=False, reason="unknown_location")
    return dict(show=True, line=_fmt(r, "list_grade_reference", loc, r["min_rs"], r["max_rs"], r["list_grade"]))
