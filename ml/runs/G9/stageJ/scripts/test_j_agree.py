"""Tests for j_agree.py with synthetic annotator CSVs (no real labels involved). Run: python3 -m pytest -q test_j_agree.py"""
import csv, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import j_agree as J

COLS = ["pack_id", "copy", "annotator", "item_id", "order_index", "label", "other_produce_name", "occluded_or_printed_what", "cut", "bag", "multi", "rotten_damaged", "note", "seconds", "labelled_at"]
def write(path, name, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(COLS)
        for k, (iid, lab, *rest) in enumerate(rows):
            other = rest[0] if rest else ""; cut = rest[1] if len(rest) > 1 else 0; bag = rest[2] if len(rest) > 2 else 0
            w.writerow(["G9J-test", "x", name, iid, k + 1, lab, other, "", cut, bag, 0, 0, "", 3, ""])

def test_kappa_known_2x2():
    # table [[20,5],[10,15]]: po=0.7, pe=0.5 -> kappa=0.4
    a = [1] * 25 + [0] * 25; b = [1] * 20 + [0] * 5 + [1] * 10 + [0] * 15
    assert abs(J.cohen_kappa(a, b) - 0.4) < 1e-9

def test_kappa_perfect_and_chance():
    assert J.cohen_kappa(list("aabbc"), list("aabbc")) == 1.0
    assert abs(J.cohen_kappa(list("abab"), list("aabb"))) < 1e-9   # po=0.5=pe
    assert J.cohen_kappa([], []) is None

def test_norm_label_aliases_and_invalid():
    assert J.norm_label(" Citrus Orange ") == "citrus_orange" and J.norm_label("orange") == "citrus_orange" and J.norm_label("3") == "citrus_orange"
    assert J.norm_label("") == "" and J.norm_label("pineapple") is None

def test_role_mapping_13way():
    assert J.role_of("citrus_orange", 0, 0, "") == ("supported", "citrus")
    assert J.role_of("apple", 0, 1, "") == ("supported_packaged", "apple")
    assert J.role_of("tomato", 1, 0, "") == ("cut", "tomato")
    assert J.role_of("other_produce", 0, 0, "lemon_or_lime") == ("other_class", "lemon_lime")
    assert J.role_of("other_produce", 0, 0, "capsicum_bell_pepper") == ("other_class", "capsicum")
    assert J.role_of("other_produce", 0, 0, "chili") == ("unsupported", "unknown")    # chili is not capsicum
    assert J.role_of("printed_or_screen", 0, 0, "") == ("printed", "unknown")
    assert J.role_of("uncertain", 0, 0, "")[0] == "excluded"

def _pair(tmp, rows_a, rows_b):
    pa, pb = os.path.join(tmp, "a.csv"), os.path.join(tmp, "b.csv"); write(pa, "Ann A", rows_a); write(pb, "Ann B", rows_b); return pa, pb

def test_agree_and_verify_flow(monkeypatch):
    monkeypatch.setattr(J, "load_key", lambda batch: {})
    tmp = tempfile.mkdtemp()
    ra = [("P001", "apple"), ("P002", "banana"), ("P003", "citrus_orange"), ("P004", "tomato"), ("P005", "carrot"), ("P006", "uncertain"),
          ("P007", "other_produce", "lemon_or_lime"), ("P008", "apple", "", 0, 1), ("P009", "printed_or_screen"), ("P010", "occluded")]
    rb = [("P001", "apple"), ("P002", "banana"), ("P003", "other_produce", "lemon_or_lime"), ("P004", "tomato"), ("P005", "carrot"), ("P006", "apple"),
          ("P007", "other_produce", "lemon_or_lime"), ("P008", "apple", "", 0, 0), ("P009", "printed_or_screen")]          # P010 missing in B
    pa, pb = _pair(tmp, ra, rb); out = os.path.join(tmp, "agree")
    rep = J.main(["agree", pa, pb, "--batch", "pilot", "--out", out])
    assert rep["n_both"] == 9 and rep["annotator_A"] == "Ann A" and rep["annotator_B"] == "Ann B"
    assert abs(rep["percent_agreement"] - 7 / 9) < 1e-3
    sheet = list(csv.DictReader(open(os.path.join(out, "adjudication_sheet.csv"))))
    ids = {r["item_id"]: r["reason"] for r in sheet}
    assert set(ids) == {"P003", "P006", "P008", "P010"}
    assert "labels differ" in ids["P003"] and "uncertain" in ids["P006"] and "cut/bag" in ids["P008"] and "missing" in ids["P010"]
    m = rep["confusion_A_rows_B_cols"]; L = J.LABELS
    assert m[L.index("citrus_orange")][L.index("other_produce")] == 1 and sum(map(sum, m)) == 9
    assert rep["per_class"]["apple"]["n_A"] == 2 and rep["per_class"]["apple"]["n_B"] == 3
    # verify before adjudication: disputed items pending
    s0 = J.main(["verify", "--batch", "pilot", "--agree-dir", out, "--out", os.path.join(tmp, "v0")])
    assert s0["status"]["pending_adjudication"] == 4 and not s0["complete"] and s0["status"]["verified_agree"] == 6
    # adjudicate
    for r in sheet:
        r["final_label"] = {"P003": "citrus_orange", "P006": "exclude", "P008": "apple", "P010": "occluded"}[r["item_id"]]
        if r["item_id"] == "P008": r["final_bag"] = "1"
        r["adjudicator"] = "Adj"
    adjp = os.path.join(tmp, "adj.csv")
    with open(adjp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(sheet[0])); w.writeheader(); w.writerows(sheet)
    s1 = J.main(["verify", "--batch", "pilot", "--agree-dir", out, "--adjudicated", adjp, "--out", os.path.join(tmp, "v1")])
    assert s1["complete"] and s1["status"]["excluded_by_adjudicator"] == 1 and s1["n_verified"] == 9
    assert s1["supported_clean_by_class"]["citrus"] == 1 and s1["supported_clean_by_class"]["apple"] == 1
    assert s1["negatives_by_role"]["supported_packaged"] == 1 and s1["negatives_by_role"]["other_class"] == 1 and s1["negatives_by_role"]["occluded"] == 1
    assert s1["gates"]["R2_met"] is False                                              # far too few items
    man = list(csv.DictReader(open(os.path.join(tmp, "v1", "verified_manifest_pilot.csv"))))
    assert len(man) == 10 and open(os.path.join(tmp, "v1", "verified_manifest_pilot.csv.sha256")).read().split()[0] == s1["sha256"]

def test_gate_counts_met():
    sup = {c: 20 for c in ("apple", "banana", "citrus", "tomato", "carrot")}
    neg = {"unsupported": 30, "printed": 10, "supported_packaged": 10, "occluded": 10}
    g = J.readiness_counts("pilot", sup, neg, {"verified_agree": 160})
    assert g["R2_met"] and g["R2_subquotas_met"]
    g2 = J.readiness_counts("pilot", dict(sup, citrus=19), neg, {})
    assert not g2["R2_met"]

def test_fallback_csv_minimal_columns(monkeypatch):
    monkeypatch.setattr(J, "load_key", lambda batch: {})
    tmp = tempfile.mkdtemp()
    for n, labs in (("a", ["apple", "Banana"]), ("b", ["apple", "9"])):
        with open(os.path.join(tmp, n + ".csv"), "w", newline="") as f:
            w = csv.writer(f); w.writerow(["item_id", "label", "annotator"]); [w.writerow([f"T00{i+1}", l, n]) for i, l in enumerate(labs)]
    rep = J.main(["agree", os.path.join(tmp, "a.csv"), os.path.join(tmp, "b.csv"), "--batch", "train", "--out", os.path.join(tmp, "o")])
    assert rep["n_both"] == 2 and rep["n_to_adjudicate"] == 1

def test_wilson_and_gate_rules():
    import j_gates as G
    lo, hi = G.wilson(60, 100); assert 0.50 < lo < 0.51 and 0.69 < hi < 0.70
    assert G.at_least(70, 100, 0.60) == "PASS"           # point 0.70, lower ~0.60
    assert G.at_least(61, 100, 0.60) == "PASS"           # point 0.61, lower ~0.51 >= 0.50
    assert G.at_least(12, 20, 0.60) == "UNCERTAIN"       # point 0.60 but lower 0.39 < 0.50
    assert G.at_least(14, 100, 0.60) == "FAIL"           # Stage H H2-like abstention: 0.14
    assert G.at_most(1, 100, 0.02, 0.06) == "PASS" and G.at_most(0, 30, 0.02, 0.06) == "UNCERTAIN" and G.at_most(10, 100, 0.02, 0.06) == "FAIL"
    assert G.zero_required(0) == "PASS" and G.zero_required(1) == "FAIL"
