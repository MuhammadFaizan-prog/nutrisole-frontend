import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from prices.amis import parse_ticker  # noqa: E402
from prices.lexicon import LEXICON, POSITION  # noqa: E402
from prices.rate_list import match_rows, norm_ur, parse_index  # noqa: E402
from prices.reference import price_reference  # noqa: E402

FX = os.path.join(os.path.dirname(HERE), "fixtures")


def test_index_parses_dates_and_retail_links():
    idx = parse_index(open(f"{FX}/fruits_index_snippet.html").read())
    assert idx[0]["date"] == "2026-10-12" and idx[0]["retail_url"].startswith("https://lahore.punjab.gov.pk/system/files")
    assert [r["date"] for r in idx] == sorted([r["date"] for r in idx], reverse=True)


def test_amis_lahore_units_converted_from_rs_per_100kg():
    rows = {r["item_en"]: r for r in parse_ticker(open(f"{FX}/amis_ticker_snippet.html", encoding="utf-8").read())}
    assert rows["Apple (Gatcha)"]["unit"] == "kg" and rows["Apple (Gatcha)"]["wholesale_rs"] == rows["Apple (Gatcha)"]["raw_value"] / 100
    assert rows["Banana(DOZEN)"]["unit"] == "dozen"
    assert all(r["unit_stated_on_page"] for r in rows.values())


def test_parsed_lists_match_hand_check_exactly():
    gt = json.load(open(f"{FX}/handcheck_gt.json"))["lists"]
    for key, L in gt.items():
        out = json.load(open(f"{FX}/parsed_{key}.json"))
        for r in out["rows"]:
            assert [r["grade1_rs"], r["grade2_rs"]] == L["rows"][r["item_ur"]], (key, r["item_ur"])


def test_unmatched_names_are_dropped_not_guessed():
    rows = [dict(name_ocr="zzz", block="right", row=99, grade1=1, grade2=1, grade1_raw="1", grade2_raw="1", num_conf=0.9)]
    assert match_rows(rows, "fruit")[0]["item_ur"] is None


def test_lexicon_positions_and_normalisation():
    assert all(len(POSITION[k]) == len(LEXICON[k]) for k in LEXICON)
    assert norm_ur("كيلا") == norm_ur("کیلا")


def test_grade_mapping_and_staleness():
    fx = json.load(open(f"{FX}/reference_parity.json"))
    for c in fx["cases"]:
        assert price_reference(c["app_class"], c["app_grade"], fx["sources"], c["today"]) == c["expected"]
    a = price_reference("tomato", "A", fx["sources"], "2026-10-12")
    b = price_reference("tomato", "B", fx["sources"], "2026-10-12")
    assert a["list_grade"] == "grade 1" and b["list_grade"] == "grade 2" and a["min_rs"] >= b["min_rs"]
    assert price_reference("tomato", "C", fx["sources"], "2026-10-12")["status"] == "no_price"
    assert price_reference("tomato", "A", fx["sources"], "2026-10-15")["stale"] is True
