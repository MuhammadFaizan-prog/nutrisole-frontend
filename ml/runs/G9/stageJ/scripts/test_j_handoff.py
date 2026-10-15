"""Synthetic regression fixtures only: these tests never supply real human evidence."""
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import j_annotation as V
import j_agree as J
import j_handoff as H


def table(path, name="Reviewer One", copy="annotator1", labels=("apple", "banana")):
    rows = []
    for i, label in enumerate(labels, 1):
        r = dict.fromkeys(V.COLUMNS, "")
        r.update(pack_id="G9J-pilot", copy=copy, annotator=name, item_id=f"P{i:03}",
                 order_index=str(i), label=label, cut="0", bag="0", multi="0",
                 rotten_damaged="0", seconds="3", labelled_at="2026-10-15T10:00:00Z")
        rows.append(r)
    save(path, rows)
    return rows


def save(path, rows):
    with Path(path).open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, V.COLUMNS)
        w.writeheader()
        w.writerows(rows)


def evidence(a, b):
    return {"schema_version": 1, "provenance": "HUMAN_INDEPENDENT", "batch": "pilot",
            "annotators": [dict(name=name, copy=copy, csv_sha256=V.digest(path),
                                independently_labelled=True, no_ai_or_peer_labels_seen=True,
                                attested_at="2026-10-15T11:00:00Z")
                           for path, name, copy in [(a, "Reviewer One", "annotator1"),
                                                    (b, "Reviewer Two", "annotator2")]]}


def test_csv_unicode_quotes_and_newlines_roundtrip(tmp_path):
    p = tmp_path / "a.csv"
    rows = table(p)
    rows[0]["note"] = 'ملٹا, "centre"\nsecond line'
    save(p, rows)
    data = V.load_table(p)
    assert data[0]["note"] == rows[0]["note"]
    assert [r["item_id"] for r in data] == ["P001", "P002"]


def test_frozen_text_digest_is_portable_between_git_checkouts(tmp_path):
    a,b=tmp_path/"windows.txt",tmp_path/"unix.txt"
    a.write_bytes(b"a\r\nb\r\n"); b.write_bytes(b"a\nb\n")
    assert V.frozen_digest(a)==V.frozen_digest(b)


@pytest.mark.parametrize("field,value", [("label", "lemon"), ("cut", "maybe"),
                                        ("seconds", "nan"), ("order_index", "1.5")])
def test_invalid_csv_values_fail_closed(tmp_path, field, value):
    p = tmp_path / "a.csv"
    rows = table(p)
    rows[0][field] = value
    save(p, rows)
    with pytest.raises(ValueError):
        V.load_table(p)


def test_duplicate_ids_are_never_silently_overwritten(tmp_path):
    p = tmp_path / "a.csv"
    rows = table(p)
    rows[1]["item_id"] = rows[0]["item_id"]
    save(p, rows)
    with pytest.raises(ValueError, match="duplicate"):
        J.read_csv(str(p))


def test_ai_exact_schema_and_coverage(tmp_path):
    p = tmp_path / "ai.csv"
    table(p, name="AI_ASSISTED_NOT_HUMAN")
    r = V.validate_ai(p, {"P001", "P002"})
    assert r["provenance"] == "AI_ASSISTED_NOT_HUMAN"
    assert r["counts"] == {"apple": 1, "banana": 1}
    with pytest.raises(ValueError, match="coverage"):
        V.validate_ai(p, {"P001", "P002", "P003"})
    p.write_text("item_id,label\nP001,apple\n", encoding="utf-8")
    with pytest.raises(ValueError, match="schema"):
        V.validate_ai(p, {"P001"})


def test_human_evidence_required_even_for_perfect_labels(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    table(a)
    table(b, "Reviewer Two", "annotator2")
    with pytest.raises(ValueError, match="evidence"):
        V.validate_human_pair(a, b, None, "pilot", {"P001", "P002"})


def test_independent_pair_joins_by_id_not_row_order(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    table(a)
    rb = table(b, "Reviewer Two", "annotator2")
    save(b, list(reversed(rb)))
    r = V.validate_human_pair(a, b, evidence(a, b), "pilot", {"P001", "P002"})
    assert r["complete"] and r["provenance"] == "HUMAN_INDEPENDENT"


def test_duplicate_ai_cannot_be_two_independent_humans(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    table(a, "AI_ASSISTED_NOT_HUMAN")
    b.write_bytes(a.read_bytes())
    with pytest.raises(ValueError):
        V.validate_human_pair(a, b, evidence(a, b), "pilot", {"P001", "P002"})


def test_known_ai_labels_rejected_even_after_renaming_annotators(tmp_path):
    ai, a, b = [tmp_path / n for n in ("ai.csv", "a.csv", "b.csv")]
    table(ai, "AI_ASSISTED_NOT_HUMAN")
    table(a)
    table(b, "Reviewer Two", "annotator2")
    with pytest.raises(ValueError, match="AI"):
        V.validate_human_pair(a, b, evidence(a, b), "pilot", {"P001", "P002"}, [ai])


def test_hash_bound_evidence_cannot_be_reused_after_edit(tmp_path):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    table(a)
    table(b, "Reviewer Two", "annotator2")
    ev = evidence(a, b)
    table(a, labels=("tomato", "banana"))
    with pytest.raises(ValueError, match="hash"):
        V.validate_human_pair(a, b, ev, "pilot", {"P001", "P002"})


def test_missing_tags_remain_unknown(tmp_path):
    p = tmp_path / "minimal.csv"
    p.write_text("item_id,label,annotator\nP001,apple,Reviewer One\n", encoding="utf-8")
    rows, _, _ = J.read_csv(p)
    assert rows["P001"]["cut"] is None


def test_subtype_and_all_tag_mismatches_need_adjudication():
    a = dict(label="other_produce", other="capsicum_bell_pepper", what="", cut=0, bag=0, multi=0, bad=0)
    b = dict(a, other="chili", multi=1)
    assert "subtype differs" in J.disagreement_reasons(a, b)
    assert "multi/bad tag differs" in J.disagreement_reasons(a, b)


def test_constant_kappa_is_undefined_and_cannot_pass():
    assert J.cohen_kappa(["apple"] * 10, ["apple"] * 10) is None
    with pytest.raises(ValueError):
        J.cohen_kappa(["apple"], [])


def agreement_fixture(tmp_path, monkeypatch, tag_mismatch=False):
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    table(a)
    rb=table(b, "Reviewer Two", "annotator2", ("tomato", "banana"))
    if tag_mismatch:
        rb[0]["cut"]="1"
        save(b,rb)
    ev = tmp_path / "evidence.json"
    ev.write_text(json.dumps(evidence(a,b)), encoding="utf-8")
    monkeypatch.setattr(J, "load_key", lambda batch: {i:dict(split="J-eval") for i in ("P001","P002")})
    out = tmp_path / "agreement"
    J.main(["agree",str(a),str(b),"--batch","pilot","--evidence",str(ev),"--out",str(out)])
    return out


def adjudicate(out, who="Reviewer Three", why="Synthetic test: whole apple verified from original photo"):
    p = out / "adjudication_sheet.csv"
    with p.open(encoding="utf-8",newline="") as f: rows=list(csv.DictReader(f))
    for r in rows:
        r.update(final_label="apple",adjudicator=who,adjudicator_reason=why)
    dst=out / "completed.csv"
    with dst.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,list(rows[0])); w.writeheader(); w.writerows(rows)
    return dst


@pytest.mark.parametrize("who,why", [("Reviewer One","reason"),("Reviewer Two","reason"),("AI_ASSISTED_NOT_HUMAN","reason"),("Reviewer Three","")])
def test_adjudication_requires_distinct_real_human_and_reason(tmp_path, monkeypatch, who, why):
    out=agreement_fixture(tmp_path,monkeypatch)
    adj=adjudicate(out,who,why)
    with pytest.raises(ValueError,match="third human"):
        J.main(["verify","--batch","pilot","--agree-dir",str(out),"--adjudicated",str(adj),"--out",str(tmp_path/"verified")])


def test_adjudication_preserves_original_agreement_and_input_history(tmp_path,monkeypatch):
    out=agreement_fixture(tmp_path,monkeypatch)
    before=V.digest(out/"agreement.json")
    adj=adjudicate(out)
    verified=tmp_path/"verified"
    result=J.main(["verify","--batch","pilot","--agree-dir",str(out),"--adjudicated",str(adj),"--out",str(verified)])
    assert result["complete"] and result["n_verified"] == 2 and result["n_release_eligible"] == 0
    assert V.digest(out/"agreement.json")==before
    assert result["original_kappa_class"] == json.loads((out/"agreement.json").read_text())["kappa_class"]
    assert (out/"inputs/annotator1.csv").read_bytes()==(tmp_path/"a.csv").read_bytes()
    assert (verified/"inputs/adjudicated.csv").read_bytes()==adj.read_bytes()
    assert result["input_sha256"]["adjudicated.csv"]==V.digest(adj)
    with pytest.raises(FileExistsError):
        J.main(["verify","--batch","pilot","--agree-dir",str(out),"--adjudicated",str(adj),"--out",str(verified)])


def test_tampered_label_snapshot_is_rejected(tmp_path,monkeypatch):
    out=agreement_fixture(tmp_path,monkeypatch)
    (out/"labels_AB.json").write_text('{}',encoding="utf-8")
    with pytest.raises(ValueError,match="history hash"):
        J.main(["verify","--batch","pilot","--agree-dir",str(out),"--out",str(tmp_path/"verified")])


def test_whitespace_adjudication_flag_cannot_resolve_a_tag_disagreement(tmp_path,monkeypatch):
    out=agreement_fixture(tmp_path,monkeypatch,tag_mismatch=True)
    adj=adjudicate(out)
    with adj.open(encoding="utf-8",newline="") as f: rows=list(csv.DictReader(f))
    rows[0]["final_cut"]=" "
    with adj.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,list(rows[0]));w.writeheader();w.writerows(rows)
    result=J.main(["verify","--batch","pilot","--agree-dir",str(out),"--adjudicated",str(adj),"--out",str(tmp_path/"verified")])
    assert not result["complete"] and result["status"]["pending_adjudication"]==1


def test_unsafe_archive_member_is_rejected(tmp_path):
    p = tmp_path / "bad.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("../escape.txt", "bad")
    with pytest.raises(ValueError, match="unsafe"):
        H.inspect_pack(p)


def test_cross_role_person_and_phash_leaks_are_quarantined():
    items = {"a": dict(split="J-eval", source="commons", uploader="One", artist="Two", phash="0f0f0f0f0f0f0f0f", group="a"),
             "b": dict(split="J-train", source="commons_t", uploader="Two", artist="Three", phash="0f0f0f0f0f0f0f0f", group="b")}
    r = H.audit_splits(items)
    assert r["conflicts"] and r["quarantine_keys"] == ["b"]
    assert items["b"]["split"] == "J-train"  # report quarantine; do not rewrite membership


def test_h3_blocked_without_authentic_human_evidence():
    fake = {"complete": True, "kappa_class": 1, "n_verified": 99999,
            "supported_clean_by_class": {c: 999 for c in J.CLASS13.values()}}
    r = H.assess_readiness(fake, fake, fake, fake, {"conflicts": []}, True)
    assert r["status"] == "BLOCKED" and r["training_authorized"] is False
    assert any(x["id"] == "R1" and x["status"] == "BLOCKED" for x in r["requirements"])


def test_readiness_cannot_substitute_another_batch_or_agreement_run():
    agreement=dict(batch="train",provenance="HUMAN_INDEPENDENT",csv_sha256=["a"*64,"b"*64],
                   evidence_sha256="c"*64,document_sha256="d"*64,kappa_class=1,kappa_supported=1,
                   complete_independent_coverage=True)
    verified=dict(batch="train",provenance="HUMAN_INDEPENDENT",evidence_sha256="c"*64,agreement_sha256="e"*64,
                  original_kappa_class=1,complete=True,gates=dict(R2_met=True),sha256="f"*64)
    r=H.assess_readiness(agreement,verified,agreement,verified,{"conflicts":[]},False)
    gates={g["id"]:g["status"] for g in r["requirements"]}
    assert gates["R1"]==gates["R2"]==gates["R3"]==gates["T4"]=="BLOCKED"


def test_frozen_dataset_membership_is_preserved():
    root = Path(__file__).resolve().parents[5]
    baseline = json.loads((root / "ml/runs/G9/stageJ/out/handoff/20261015/G9J_frozen_inputs.json").read_text())
    for name, expected in baseline["git_lf_sha256"].items():
        assert V.frozen_digest(root / name) == expected, name


REAL_AI = Path(__file__).resolve().parents[1] / "out/handoff/20261015_visual_review/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_AI_visual_review_265.csv"


def _renamed_real_ai(path, name, copy, edit=0):
    rows = V.load_table(REAL_AI)
    for r in rows:
        r.update(annotator=name, copy=copy)
    for r in rows[:edit]:
        r["label"] = "banana" if r["label"] != "banana" else "apple"
    save(path, rows)
    return {r["item_id"] for r in rows}


@pytest.mark.parametrize("edit", [0, 5])
def test_committed_ai_review_refused_as_human_without_ai_csv_flag(tmp_path, edit):
    """G9-J2 guard: the committed AI_ASSISTED_NOT_HUMAN review (auto-discovered, no --ai-csv), renamed as a person
    and optionally lightly edited, must never pass as an independent human annotator."""
    if not REAL_AI.exists():
        pytest.skip("committed AI review not present")
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    ids = _renamed_real_ai(a, "Reviewer One", "annotator1", edit)
    rb = V.load_table(a)
    for r in rb:
        r.update(annotator="Reviewer Two", copy="annotator2", label="uncertain")
    save(b, rb)
    with pytest.raises(ValueError, match="near-copy" if edit else "known AI annotation payload"):
        V.validate_human_pair(a, b, evidence(a, b), "pilot", ids)


def test_unmodified_ai_marker_rows_refused(tmp_path):
    if not REAL_AI.exists():
        pytest.skip("committed AI review not present")
    a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    a.write_bytes(REAL_AI.read_bytes())
    table(b, "Reviewer Two", "annotator2")
    with pytest.raises(ValueError):
        V.validate_human_pair(a, b, evidence(a, b), "pilot", {r["item_id"] for r in V.load_table(a)})


def test_near_copy_threshold_allows_genuinely_different_labels(tmp_path):
    ai = [dict(item_id=f"P{i:03}", label="apple", cut="0", bag="0", multi="0", rotten_damaged="0") for i in range(1, 41)]
    hum = [dict(r, label=("apple" if i < 30 else "banana")) for i, r in enumerate(ai)]
    assert V.ai_near_copy(hum, ai) == 0.75
    assert V.ai_near_copy(hum[:5], ai) is None


def test_j2_batches_use_their_own_frozen_key():
    """G9-J2: pilot2/train2 load out/gaps/j2_blind_key.csv; the frozen Stage J key is untouched and ids never collide."""
    k1, k2 = J.load_key("pilot"), J.load_key("pilot2")
    if not k2:
        pytest.skip("j2 key not present")
    assert J.key_path("pilot").endswith("out/j_blind_key.csv") and J.key_path("train2").endswith("out/gaps/j2_blind_key.csv")
    assert not set(k1) & set(k2) and not set(J.load_key("train")) & set(J.load_key("train2"))
    assert all(r["split"] == "J-eval" for r in k2.values()) and all(r["split"] == "J-train" for r in J.load_key("train2").values())
    assert all(V.re.fullmatch(r"[PT][0-9]{3,}", i) for i in list(k2) + list(J.load_key("train2")))
    pilot1_keys = {r["key"] for r in k1.values()}
    assert not pilot1_keys & {r["key"] for r in k2.values()}
