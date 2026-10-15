"""G9 Stage J5 tests: HUMAN_REVIEWED_AI_ASSISTED provenance tier, record integrity, orange training sessions, candidate pool rules.
Synthetic fixtures + read-only checks of committed files. No training, no labels invented."""
import csv, json, sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "h3"))
import j_agree as JA
import j_gates as G
import j_team_phone as T
import j5_human_review as HR
import h3_guard as GU
from test_j4 import _img, _sessions, _tiny_refs
sys.path.insert(0, str(HERE.parent / "h3" / "kernel"))
import test_h3 as FX

REC = HERE.parent / "out/j5/human_review_ai_assisted_v1"


def test_tiers_explicit_and_only_independent_counts():
    assert set(JA.PROVENANCE_TIERS) == {"HUMAN_INDEPENDENT", "HUMAN_REVIEWED_AI_ASSISTED", "AI_ASSISTED_NOT_HUMAN"}
    for use in ("kappa_evidence", "independent_double_annotation", "verified_manifest", "counts_for_eval_gates", "counts_for_training_gates"):
        assert JA.tier_allows("HUMAN_INDEPENDENT", use)
        assert not JA.tier_allows("HUMAN_REVIEWED_AI_ASSISTED", use)
        assert not JA.tier_allows("AI_ASSISTED_NOT_HUMAN", use)
        assert not JA.tier_allows("something_else", use)
    assert JA.tier_allows("HUMAN_REVIEWED_AI_ASSISTED", "human") and not JA.tier_allows("HUMAN_REVIEWED_AI_ASSISTED", "blind")


def test_tier_gate_report_never_unlocks_h3_for_reviewed_tier():
    r = G.tier_gate_report("HUMAN_REVIEWED_AI_ASSISTED")
    for g in ("R1", "R2", "R3", "R4", "T1", "T2", "T3", "T4", "GO"):
        assert r[g]["verdict"] == "FAIL", g
    s = r["summary"]
    assert s["can_unlock_h3_eval_gate"] is False and s["kappa_evidence"] is False and s["can_feed_training_gates"] is False
    assert s["frozen_gates_allow_single_reviewer_tier"] is False
    assert G.tier_gate_report("HUMAN_INDEPENDENT")["summary"]["can_unlock_h3_eval_gate"] is True  # eligibility only, data counts still apply


def test_agree_refuses_reviewed_tier_csv_as_kappa_input(tmp_path):
    src = REC / "reviewed_labels_pilot.csv"
    with pytest.raises(ValueError, match="not independent double annotation"):
        JA.main(["agree", str(src), str(src), "--batch", "pilot", "--evidence", str(tmp_path / "none.json"), "--out", str(tmp_path / "o")])
    assert not (tmp_path / "o").exists()


def test_guard_refuses_reviewed_tier_manifest(tmp_path):
    inp = FX.good_inputs(tmp_path)
    sp = Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_summary_pilot.json"
    s = json.loads(sp.read_text()); s["provenance"] = "HUMAN_REVIEWED_AI_ASSISTED"; sp.write_text(json.dumps(s))
    res = GU.evaluate(inp)
    assert not res["ready"] and any("HUMAN_REVIEWED_AI_ASSISTED" in p and "not double annotation" in p for p in res["problems"])


def test_record_binds_unmodified_ai_csvs_and_flags_p729():
    rec = json.loads((REC / "human_review_record.json").read_text())
    assert (REC / "human_review_record.json.sha256").read_text().split()[0] == HR.sha(REC / "human_review_record.json")
    assert rec["provenance"] == "HUMAN_REVIEWED_AI_ASSISTED" and rec["reviewer"]["count"] == 1
    assert rec["review_mode"]["blind"] is False and rec["review_mode"]["independent_double_annotation"] is False
    assert rec["stated_at"] == "2026-10-15T22:53:00+05:00" and "not as fabricated independent blind annotation" in rec["source"]["verbatim"]
    for b, s in HR.SOURCES.items():
        assert HR.sha(s["csv"]) == s["sha256"] == rec["reviewed_files"][b]["sha256"]   # originals untouched
    assert [c["item_id"] for c in rec["hark_v2_corrections"]["changed_rows"]] == ["P729"]
    assert rec["hark_v2_corrections"]["acceptance"].startswith("UNCONFIRMED")
    assert rec["problems"] == [] and rec["gates"]["summary"]["can_unlock_h3_eval_gate"] is False
    ind = rec["train_eval_independence"]
    assert ind["cand_key_overlap"] == [] and ind["commons_uploader_overlap"] == [] and ind["eval_only_sources_in_train"] == []


def test_reviewed_label_tables_preserve_ai_labels_and_ids():
    for b, s in HR.SOURCES.items():
        orig = {r["item_id"]: r for r in HR.rows(s["csv"])}
        rv = list(csv.DictReader(open(REC / f"reviewed_labels_{b}.csv", encoding="utf-8")))
        assert [r["item_id"] for r in rv] == list(orig) and len(rv) == s["n"]
        assert all(r["label"] == orig[r["item_id"]]["label"] and r["provenance"] == "HUMAN_REVIEWED_AI_ASSISTED" and r["independent"] == "no" for r in rv)
        assert {r["split"] for r in rv} == {"J-eval"}   # eval items: never training labels (T5)


def test_orange_training_sessions_accepted_carrot_still_refused(tmp_path):
    _sessions(tmp_path, [["S20261021-GH-01", "Sara G", "2026-10-21", "home", "train", "internal-FYP", "yes"]])
    for n, c in enumerate(("citrus_orange", "apple", "banana", "tomato"), 1):
        _img(tmp_path / f"TP_S20261021-GH-01_{c}_open_{n:03d}.jpg", 400 + n)
    res = T.ingest(tmp_path, ref_manifest=_tiny_refs(tmp_path))
    assert {i["intended_by_photographer"] for i in res["items"]} == {"citrus_orange", "apple", "banana", "tomato"}
    assert all(i["split"] == "J-train" and i["human_verified"] is False for i in res["items"])
    _img(tmp_path / "TP_S20261021-GH-01_carrot_open_009.jpg", 499)
    with pytest.raises(ValueError, match="train sessions this round cover"):
        T.ingest(tmp_path, ref_manifest=_tiny_refs(tmp_path))


def test_candidate_pool_is_training_only_unverified_and_licence_clean():
    p = HERE.parent / "out/j5/candidates/j5_candidate_pool.csv"
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    assert rows
    import re
    for r in rows:
        assert r["split"] == "J-train-candidate" and r["eval_eligible"] == "no" and r["human_verified"] == "no" and r["provenance"] == "NONE"
        assert not re.search(r"\bNC\b|\bND\b|-nc|-nd", r["licence"], re.I)
        assert not re.search(r"pexels|pixabay|mixkit|unsplash", " ".join(r[k] for k in ("title", "credit", "author", "page_url")), re.I)
        if r["status"] == "CANDIDATE_UNVERIFIED": assert int(r["ref_dmin"]) > 10
        else: assert r["status"] == "DROPPED" and r["drop_reason"]
