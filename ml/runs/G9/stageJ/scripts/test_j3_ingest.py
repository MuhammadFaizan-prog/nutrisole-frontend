"""Stage J3 tests (synthetic fixtures only): default earlier-reference check, eval-vs-training quarantine, provenance, blind packs
(folder -> manifest -> blind packs end to end), committed reference manifest is hashes-only, team batches in j_agree, and the v2 AI
review being in the known-AI registry."""
import csv, hashlib, json, re, sys, zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import j_team_phone as T
import j_agree as JA
import j_annotation as V

HDR = T.COLUMNS
REF = HERE.parent / "out/j3_reference_hashes.json"
V2 = HERE.parent / "out/handoff/20261015_pilot2_visual_review_v2_hark/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335_v2_hark.csv"


def img(path, seed, size=256):
    rng = np.random.default_rng(seed)
    a = (rng.random((8, 8, 3)) * 255).astype("uint8")
    Image.fromarray(a).resize((size, size), Image.NEAREST).save(path, quality=95)


def sessions(root, rows):
    with open(root / "sessions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(HDR); w.writerows(rows)


def tiny_manifest(tmp, train=(), evals=()):
    sets = {"synthetic_train": dict(role="train_source", count=len(train), hashes=sorted(train)),
            "synthetic_eval": dict(role="earlier_eval", count=len(evals), hashes=sorted(evals))}
    p = tmp / "refs.json"; txt = json.dumps(dict(sets=sets)); p.write_text(txt)
    Path(str(p) + ".sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  refs.json\n")
    return p


def folder(tmp):
    root = tmp / "drop"; root.mkdir()
    sessions(root, [["S20261018-AB-01", "Ali B", "2026-10-18", "home kitchen", "eval", "CC-BY-4.0", "yes"],
                    ["S20261019-CD-01", "Sara D", "2026-10-19", "campus", "eval", "internal-FYP", "yes"],
                    ["S20261020-EF-01", "Omar F", "2026-10-20", "market", "train", "CC-BY-4.0", "yes"]])
    for d in ("S20261018-AB-01", "S20261019-CD-01", "S20261020-EF-01"): (root / d).mkdir()
    img(root / "S20261018-AB-01/TP_S20261018-AB-01_citrus_orange_bag-mesh_001.jpg", 101)
    img(root / "S20261018-AB-01/TP_S20261018-AB-01_banana_hid-hand_002.jpg", 102)
    img(root / "S20261019-CD-01/TP_S20261019-CD-01_tomato_tray-film_001.jpg", 103)
    img(root / "S20261019-CD-01/TP_S20261019-CD-01_carrot_hid-edge_002.jpg", 104)
    img(root / "S20261020-EF-01/TP_S20261020-EF-01_apple_open_001.jpg", 105)
    img(root / "S20261020-EF-01/TP_S20261020-EF-01_apple_open_002.jpg", 106)
    return root


def test_committed_reference_manifest_is_complete_hashes_only():
    txt = REF.read_text(); m = json.loads(txt)
    assert hashlib.sha256(REF.read_bytes()).hexdigest() == Path(str(REF) + ".sha256").read_text().split()[0]
    assert m["m_test_pixels_opened"] is False and "G9_MDEV_MTEST_stored_hashes" in m["sets"]
    names = set(m["sets"])
    for need in ("G1_data__train_source", "G2_data__train_source", "G3G7D_det_v3_train_G3_train", "G4_data__train_source", "G5_data__train_source",
                 "G7_data__train_source", "G9_stageH_set_train", "G9_stageH_set_eval", "G9_stageI_candidates__mixed", "G9_stageJ_J-eval",
                 "G9_stageJ_J-train", "G9_stageJ2_J-eval", "G9_stageJ2_J-train", "G9_DEF_commons_pools_stored", "G9_stageG_CU_stored"):
        assert need in names, need
    hexre = re.compile(r"^[0-9a-f]{16}$")
    assert all(hexre.match(h) for s in m["sets"].values() for h in s["hashes"])
    assert "/workspace" not in txt and ".jpg" not in txt.lower()           # no paths or file names
    assert m["n_unique"] > 50000


def test_default_reference_check_is_on(tmp_path):
    res = T.ingest(folder(tmp_path))
    rc = res["reference_check"]
    assert rc["default_manifest"] is True and rc["n_reference_hashes"] > 50000 and rc["manifest_sha256"]
    assert all("ref_dmin" in i for i in res["items"])


def test_missing_manifest_refuses(tmp_path):
    with pytest.raises(FileNotFoundError):
        T.ingest(folder(tmp_path), ref_manifest=tmp_path / "nope.json")


def test_eval_photo_colliding_with_training_or_earlier_eval_is_quarantined(tmp_path):
    root = folder(tmp_path)
    h_train = T.phash(root / "S20261018-AB-01/TP_S20261018-AB-01_citrus_orange_bag-mesh_001.jpg")
    h_eval = T.phash(root / "S20261019-CD-01/TP_S20261019-CD-01_tomato_tray-film_001.jpg")
    res = T.ingest(root, ref_manifest=tiny_manifest(tmp_path, train=[h_train], evals=[h_eval]))
    by = {i["file"]: i for i in res["items"]}
    assert "TRAINING source" in by["TP_S20261018-AB-01_citrus_orange_bag-mesh_001.jpg"]["quarantine"]
    assert "evaluation/holdout" in by["TP_S20261019-CD-01_tomato_tray-film_001.jpg"]["quarantine"]
    assert res["counts"]["J-eval/quarantined"] == 2 and res["counts"]["J-eval"] == 2


def test_provenance_records(tmp_path):
    res = T.ingest(folder(tmp_path))
    assert len(res["provenance"]) == len(res["items"]) == 6
    for p in res["provenance"]:
        assert set(p) >= {"sha256", "session_id", "photographer", "licence", "consent_confirmed", "date", "place", "ingested_at"}
        assert p["consent_confirmed"] == "yes" and len(p["sha256"]) == 64


def test_byte_identical_recorded_and_wrong_folder_refused(tmp_path):
    root = folder(tmp_path)
    (root / "S20261018-AB-01/TP_S20261018-AB-01_apple_bag-clear_009.jpg").write_bytes((root / "S20261018-AB-01/TP_S20261018-AB-01_banana_hid-hand_002.jpg").read_bytes())
    res = T.ingest(root); by = {i["file"]: i for i in res["items"]}
    d = by["TP_S20261018-AB-01_banana_hid-hand_002.jpg"]
    e = by["TP_S20261018-AB-01_apple_bag-clear_009.jpg"]
    assert {d["exact_duplicate_of"], e["exact_duplicate_of"]} == {"", e["file"]} and e["group"] == d["group"]   # first in sort order is the original; one group
    (root / "S20261018-AB-01/TP_S20261018-AB-01_apple_bag-clear_009.jpg").unlink()
    img(root / "S20261019-CD-01/TP_S20261018-AB-01_apple_bag-clear_010.jpg", 77)
    with pytest.raises(ValueError, match="not its session folder"):
        T.ingest(root)


def test_blind_ids_do_not_depend_on_file_names(tmp_path):
    (tmp_path / "a").mkdir(); (tmp_path / "b").mkdir()
    r1 = T.ingest(folder(tmp_path / "a"))
    b1 = {i["sha256"]: i["blind_id"] for b in T.assign_blind(r1).values() for i in b}
    root2 = folder(tmp_path / "b")
    p = root2 / "S20261018-AB-01/TP_S20261018-AB-01_citrus_orange_bag-mesh_001.jpg"
    p.rename(p.with_name("TP_S20261018-AB-01_apple_tray-film_099.jpg"))            # different intent, same pixels
    b2 = {i["sha256"]: i["blind_id"] for b in T.assign_blind(T.ingest(root2)).values() for i in b}
    assert b1 == b2
    assert all(re.fullmatch(r"[QR]\d{3}", v) for v in b1.values())


def test_end_to_end_folder_to_manifest_to_blind_packs(tmp_path):
    root = folder(tmp_path)
    res = T.ingest(root)
    out = tmp_path / "run"
    rec = T.write_outputs(res, out, packs=True, lab=str(tmp_path / "packs"), stage_dir=str(tmp_path / "stage"))
    assert rec["blind"] == {"team_eval": 4, "team_train": 2}
    man = json.loads((out / "team_phone_manifest.json").read_text())
    assert all("path" not in i for i in man["items"]) and man["items"][0]["human_verified"] is False
    key = list(csv.DictReader(open(out / "team_blind_key.csv")))
    assert {r["batch"] for r in key} == {"team_eval", "team_train"} and len(key) == 6
    forbidden = ["TP_", "S20261018", "S20261019", "S20261020", "Ali B", "Sara D", "Omar F", "bag-mesh", "hid-hand", "tray-film", "hid-edge",
                 "intended", "condition_NOT", "home kitchen", "campus"]
    zips = sorted((tmp_path / "packs").glob("*.zip"))
    assert [z.name for z in zips] == ["nutrisole_G9J_team_eval_annotator1.zip", "nutrisole_G9J_team_eval_annotator2.zip",
                                      "nutrisole_G9J_team_train_annotator1.zip", "nutrisole_G9J_team_train_annotator2.zip"]
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            names = zf.namelist()
            assert any(n.endswith(".html") for n in names) and "annotation_guide.md" in names
            for n in names:
                data = zf.read(n).decode("utf-8", "ignore") if n.endswith((".html", ".csv", ".txt", ".md")) else ""
                for f in forbidden:
                    assert f not in n and f not in data, (z.name, n, f)
            html = zf.read([n for n in names if n.endswith(".html")][0]).decode()
            assert "G9J-team_" in html and ("Q001" in html or "R001" in html)
    # j_agree resolves the team key
    JA.KEY_OVERRIDE["team_eval"] = str(out / "team_blind_key.csv")
    try:
        k = JA.load_key("team_eval")
        assert sorted(k) == ["Q001", "Q002", "Q003", "Q004"] and all(v["split"] == "J-eval" for v in k.values())
        assert JA.is_eval_batch("team_eval") and not JA.is_eval_batch("team_train")
    finally:
        JA.KEY_OVERRIDE.clear()


def test_team_batch_without_key_refuses():
    with pytest.raises(ValueError, match="needs --key"):
        JA.key_path("team_train")


def test_v2_ai_review_is_in_known_ai_registry(tmp_path):
    imported = HERE.parent / "out/handoff"
    assert V2 in set(imported.glob("*/AI_ASSISTED_NOT_HUMAN/*.csv"))
    rows = V.load_table(V2, exact_schema=True)
    assert len(rows) == 335 and {r["annotator"] for r in rows} == {"AI_ASSISTED_NOT_HUMAN"}
    by = {r["item_id"]: r for r in rows}
    assert by["P729"]["label"] == "carrot" and by["P756"]["label"] == "other_produce" and by["P773"]["label"] == "apple"
    # renaming the v2 payload to a human cannot pass as independent evidence
    cols = list(rows[0]); a, b = tmp_path / "a.csv", tmp_path / "b.csv"
    for p, name, copy in ((a, "Real Person A", "annotator1"), (b, "Real Person B", "annotator2")):
        with open(p, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
            for r in rows: w.writerow(dict(r, annotator=name, copy=copy, note=""))
    ev = dict(schema_version=1, provenance="HUMAN_INDEPENDENT", batch="pilot2", annotators=[
        dict(name=n, copy=c, csv_sha256=V.digest(p), independently_labelled=True, no_ai_or_peer_labels_seen=True, attested_at="2026-10-15T20:00:00+05:00")
        for p, n, c in ((a, "Real Person A", "annotator1"), (b, "Real Person B", "annotator2"))])
    with pytest.raises(ValueError, match="AI annotation payload"):
        V.validate_human_pair(a, b, ev, "pilot2", {r["item_id"] for r in rows})


def test_v1_review_untouched():
    p = HERE.parent / "out/handoff/20261015_pilot2_visual_review/AI_ASSISTED_NOT_HUMAN/nutrisole_G9J_pilot2_AI_visual_review_335.csv"
    assert hashlib.sha256(p.read_bytes()).hexdigest() == "6c17debff4bb545bc8841abc140242d86a1fed86dc303ade4274eac35048d2aa"


def test_merge_evidence_binds_csv_hash_and_refuses_unattested(tmp_path):
    import j3_merge_evidence as M
    a, b = tmp_path / "A_pilot.csv", tmp_path / "B_pilot.csv"; a.write_text("x\n"); b.write_text("y\n")
    att = lambda copy, name, f, ok=True: dict(schema_version=1, provenance="HUMAN_INDEPENDENT", copy=copy, name=name, batches={"pilot": f},
                                              independently_labelled=ok, no_ai_or_peer_labels_seen=ok, attested_at="2026-10-20T18:00:00+05:00")
    ev = M.merge("pilot", att("annotator1", "Ann A", a.name), a, att("annotator2", "Ann B", b.name), b)
    assert ev["annotators"][0]["csv_sha256"] == V.digest(a) and ev["batch"] == "pilot"
    with pytest.raises(ValueError, match="must be true"):
        M.merge("pilot", att("annotator1", "Ann A", a.name, ok=False), a, att("annotator2", "Ann B", b.name), b)
    with pytest.raises(ValueError, match="real human name"):
        M.merge("pilot", att("annotator1", "AI_ASSISTED_NOT_HUMAN", a.name), a, att("annotator2", "Ann B", b.name), b)
    with pytest.raises(ValueError, match="distinct"):
        M.merge("pilot", att("annotator1", "Ann A", a.name), a, att("annotator2", "ann a", b.name), b)
