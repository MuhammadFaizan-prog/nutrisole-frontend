"""Punjab AMIS (Agriculture Marketing Information Service) WHOLESALE fallback, http://www.amis.pk/.
The home page carries a ticker "Avg. WholeSale Prices Of Commodities in Rs/100Kg" with one section per
city (unit confirmed on the page, 2026-10-12). Items annotated (DOZEN) or (100Pcs) are in those units.
We read only the Lahore section, convert Rs/100kg -> Rs/kg, and label everything 'wholesale'.
The ticker carries no date: list_date is the fetch date and the record says so."""
from __future__ import annotations

import datetime as dt
import html
import re
import urllib.request

URL = "http://www.amis.pk/"
# AMIS English names -> (NutriSole class, variety label). Explicit only; anything else is ignored.
AMIS_MAP = {
    "Apple (Gatcha)": ("apple", "Gacha"), "Apple Kala Kullu (Madani)": ("apple", "Kala Kulu (plains)"),
    "Apple Kala Kullu (Pahari)": ("apple", "Kala Kulu (hill)"), "Banana(DOZEN)": ("banana", None), "Guava": ("guava", None),
    "Lemon (China)": ("lemon_lime", "China"), "Musambi(100Pcs)": ("citrus", "musambi"), "Pomegranate Desi": ("pomegranate", "desi"),
    "Pomegranate(Kandhari)": ("pomegranate", "Kandhari"), "Mango(Chounsa)": ("mango", "Chaunsa"), "Capsicum (شملہ مرچ)": ("capsicum", None),
    "Carrot": ("carrot", None), "Carrot China": ("carrot", "China"), "Cucumber (Kheera)": ("cucumber", None), "Potato Sugar free": ("potato", "sugar-free"),
    "Tomato": ("tomato", None), "Kinnow": ("citrus", "kinnow"), "Malta": ("citrus", "malta"),
}


def parse_ticker(page_html: str, city: str = "Lahore") -> list[dict]:
    s = page_html
    i = s.find("Avg. WholeSale Prices")
    if i < 0:
        return []
    t = html.unescape(re.sub(r"<[^>]+>", "|", s[i:i + 20000])).replace("\xa0", " ")
    unit_ok = "Rs/100Kg" in t[:80]
    secs = re.split(r"\|\|([A-Za-z .]+)\|\|", t)
    out = []
    for k in range(1, len(secs) - 1, 2):
        if secs[k].strip() != city:
            continue
        for name, val in re.findall(r"\s{2,}([^\d|]+?)\s{2,}(\d+(?:\.\d+)?)", "  " + secs[k + 1]):
            name = name.strip()
            if name not in AMIS_MAP:
                continue
            v = float(val)
            if "(DOZEN)" in name.upper():
                unit, rs = "dozen", v
            elif "100PCS" in name.upper().replace(" ", ""):
                unit, rs = "piece", v / 100.0
            else:
                unit, rs = "kg", v / 100.0
            cls, var = AMIS_MAP[name]
            out.append(dict(item_en=name, app_class=cls, variety=var, unit=unit, wholesale_rs=round(rs, 2), raw_value=v,
                            raw_unit="Rs/100Kg" if unit == "kg" else name[name.find("("):] if "(" in name else "?", unit_stated_on_page=unit_ok))
    return out


def fetch(city: str = "Lahore") -> dict:
    h = urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "NutriSole-FYP-price-reference/0.1"}), timeout=60).read().decode("utf-8", "ignore")
    today = dt.date.today().isoformat()
    return dict(source="Punjab AMIS (amis.pk) average wholesale prices", source_url=URL, price_type="wholesale", currency="PKR",
                list_date=today, list_date_note="AMIS ticker shows no date; fetch date used", city=city, rows=parse_ticker(h, city))
