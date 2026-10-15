"""G9 Stage J6 tests: P729 amendment (versioned, v1 untouched, tier unchanged), candidate pool v2 rules. Read-only + synthetic."""
import csv, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j_agree as JA
import j5_human_review as HR
import j6_p729_amendment as AM

V2 = HERE.parent / "out/j5/human_review_ai_assisted_v2"


def test_v1_and_original_ai_csvs_unchanged():
    for f, v in AM.v1_hashes().items():
        assert v["sha256_file_matches"], f
    assert HR.sha(HR.SOURCES["pilot2"]["csv"]) == HR.SOURCES["pilot2"]["sha256"]
    assert HR.sha(HR.V2["csv"]) == HR.V2["sha256"]
    v1 = {r["item_id"]: r for r in HR.rows(HR.REC_DIR / "reviewed_labels_pilot2.csv")}
    assert v1["P729"]["label"] == "uncertain" and v1["P729"]["disputed"]


def test_amendment_record_and_only_p729_changed():
    am = json.loads((V2 / "amendment_001_P729.json").read_text())
    assert (V2 / "amendment_001_P729.json.sha256").read_text().split()[0] == HR.sha(V2 / "amendment_001_P729.json")
    assert (V2 / "reviewed_labels_pilot2.csv.sha256").read_text().split()[0] == HR.sha(V2 / "reviewed_labels_pilot2.csv")
    assert am["provenance"] == "HUMAN_REVIEWED_AI_ASSISTED" and am["blind"] is False and am["independent"] is False
    assert am["approval_source"]["at"].startswith("Fri 2026-10-16 12:06 AM PKT")
    assert am["after"] == dict(label="carrot", cut="0", bag="1", multi="1", rotten_damaged="0", role_if_accepted="supported_packaged", class13_if_accepted="carrot")
    assert am["occluded"] is False and am["matches_hark_v2_row"] is True and am["problems"] == []
    for k in ("kappa_evidence", "verified_manifest", "counts_for_eval_gates", "training_label", "can_unlock_h3"):
        assert am["effect"][k] is False
    v1 = HR.rows(HR.REC_DIR / "reviewed_labels_pilot2.csv"); v2 = HR.rows(V2 / "reviewed_labels_pilot2.csv")
    assert [r["item_id"] for r in v1] == [r["item_id"] for r in v2]
    diff = [b["item_id"] for a, b in zip(v1, v2) if {k: a[k] for k in a} != {k: b[k] for k in a}]
    assert diff == ["P729"]
    assert all(r["provenance"] == "HUMAN_REVIEWED_AI_ASSISTED" and r["blind"] == "no" and r["independent"] == "no" for r in v2)
    assert sum(r["label"] == "uncertain" for r in v2) == 118


def test_amendment_refuses_overwrite_and_check_is_clean():
    import pytest
    am, _ = AM.build(check_only=True)
    assert am["problems"] == []
    with pytest.raises(FileExistsError):
        AM.build(check_only=False)


def test_amended_table_still_refused_as_kappa_input(tmp_path):
    import pytest
    src = V2 / "reviewed_labels_pilot2.csv"
    with pytest.raises(ValueError, match="not independent double annotation"):
        JA.main(["agree", str(src), str(src), "--batch", "pilot2", "--evidence", str(tmp_path / "none.json"), "--out", str(tmp_path / "o")])


def test_j6_candidate_pool_rules():
    import re
    P = HERE.parent / "out/j6/candidates/j6_candidate_pool.csv"
    rows = list(csv.DictReader(open(P, encoding="utf-8")))
    j5 = list(csv.DictReader(open(HERE.parent / "out/j5/candidates/j5_candidate_pool.csv", encoding="utf-8")))
    assert rows and all(r["cand_id"].startswith("j6c") for r in rows)
    assert not ({r["cand_id"] for r in rows} & {r["cand_id"] for r in j5}) and not ({r["title"] for r in rows} & {r["title"] for r in j5})
    for r in rows:
        assert r["status"] in ("CANDIDATE_UNVERIFIED", "DROPPED") and r["eval_eligible"] == "no" and r["provenance"] == "NONE" and r["human_verified"] == "no"
        assert r["split"] == "J-train-candidate"
        assert re.match(r"^(CC BY(-SA)? ?\d(\.\d)?|CC0|Public domain|PD.*)", r["licence"], re.I) and not re.search(r"\bNC\b|\bND\b", r["licence"])
        assert not re.search(r"unsplash|pixabay|pexels|mixkit", " ".join((r["title"], r["credit"], r["author"])), re.I)
        if r["status"] == "CANDIDATE_UNVERIFIED": assert int(r["ref_dmin"]) > 10
    cov = json.loads((HERE.parent / "out/j6/candidates/j6_coverage_vs_quota.json").read_text())
    assert all(c["t1_human_verified_now"] == 0 for c in cov["classes"])
