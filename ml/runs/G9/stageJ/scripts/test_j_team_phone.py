"""Synthetic fixtures only: tests for the team_phone ingestion stub (session-based split + pHash check)."""
import csv
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import j_team_phone as T

HDR = ["session_id", "photographer", "date", "place", "purpose", "licence", "consent_confirmed"]


def img(path, seed):
    rng = np.random.default_rng(seed)
    a = (rng.random((8, 8, 3)) * 255).astype("uint8")
    Image.fromarray(a).resize((256, 256), Image.NEAREST).save(path, quality=95)


def sessions(root, rows):
    with open(root / "sessions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(HDR); w.writerows(rows)


def setup(tmp_path):
    rows = [["S20261018-AB-01", "Ali B", "2026-10-18", "home kitchen", "eval", "CC-BY-4.0", "yes"],
            ["S20261019-CD-01", "Sara D", "2026-10-19", "campus", "eval", "internal-FYP", "yes"],
            ["S20261018-EF-01", "Omar F", "2026-10-18", "market", "train", "CC-BY-4.0", "yes"]]
    sessions(tmp_path, rows)
    for d in ("S20261018-AB-01", "S20261019-CD-01", "S20261018-EF-01"): (tmp_path / d).mkdir()
    img(tmp_path / "S20261018-AB-01/TP_S20261018-AB-01_citrus_orange_bag-mesh_001.jpg", 1)
    img(tmp_path / "S20261018-AB-01/TP_S20261018-AB-01_banana_hid-hand_002.jpg", 2)
    img(tmp_path / "S20261019-CD-01/TP_S20261019-CD-01_tomato_tray-film_001.jpg", 3)
    img(tmp_path / "S20261018-EF-01/TP_S20261018-EF-01_apple_open_001.jpg", 4)
    img(tmp_path / "S20261018-EF-01/TP_S20261018-EF-01_apple_open_002.jpg", 2)   # same pixels as an eval photo -> leak
    return tmp_path


def test_split_by_session_and_phash_quarantine(tmp_path):
    res = T.ingest(setup(tmp_path))
    by = {i["file"]: i for i in res["items"]}
    assert all(i["source"] == "team_phone" and i["human_verified"] is False for i in by.values())
    assert by["TP_S20261018-AB-01_citrus_orange_bag-mesh_001.jpg"]["split"] == "J-eval"
    assert by["TP_S20261018-AB-01_citrus_orange_bag-mesh_001.jpg"]["intended_by_photographer"] == "citrus_orange"
    assert by["TP_S20261018-EF-01_apple_open_001.jpg"]["split"] == "J-train"
    assert "quarantine" not in by["TP_S20261018-EF-01_apple_open_001.jpg"]
    q = by["TP_S20261018-EF-01_apple_open_002.jpg"]
    assert q["split"] == "J-train" and "eval photo" in q["quarantine"]
    assert not any("quarantine" in i for i in by.values() if i["split"] == "J-eval")   # eval never dropped
    assert res["counts"] == {"J-eval": 3, "J-train": 1, "J-train/quarantined": 1}


def test_reference_hash_quarantines_train(tmp_path):
    root = setup(tmp_path)
    ref = T.phash(root / "S20261018-EF-01/TP_S20261018-EF-01_apple_open_001.jpg")
    res = T.ingest(root, [ref])
    q = {i["file"]: i for i in res["items"]}["TP_S20261018-EF-01_apple_open_001.jpg"]
    assert "reference" in q["quarantine"]


def test_photographer_in_both_splits_is_refused(tmp_path):
    sessions(tmp_path, [["S20261018-AB-01", "Ali B", "", "", "eval", "CC-BY-4.0", "yes"],
                        ["S20261020-AB-02", "ali b", "", "", "train", "CC-BY-4.0", "yes"]])
    with pytest.raises(ValueError, match="both train and eval"):
        T.ingest(tmp_path)


def test_bad_names_consent_and_wrong_condition_rejected(tmp_path):
    sessions(tmp_path, [["S20261018-AB-01", "Ali B", "", "", "eval", "CC-BY-4.0", "no"]])
    with pytest.raises(ValueError, match="consent"):
        T.ingest(tmp_path)
    sessions(tmp_path, [["S20261018-AB-01", "Ali B", "", "", "eval", "CC-BY-4.0", "yes"]])
    img(tmp_path / "TP_S20261018-AB-01_apple_open_001.jpg", 5)          # open shot in an eval session
    with pytest.raises(ValueError, match="bagged or partly hidden"):
        T.ingest(tmp_path)
    (tmp_path / "TP_S20261018-AB-01_apple_open_001.jpg").unlink()
    img(tmp_path / "IMG_20261018_1200.jpg", 6)
    with pytest.raises(ValueError, match="bad file name"):
        T.ingest(tmp_path)


def test_eval_burst_shots_share_a_group(tmp_path):
    sessions(tmp_path, [["S20261018-AB-01", "Ali B", "", "", "eval", "CC-BY-4.0", "yes"]])
    img(tmp_path / "TP_S20261018-AB-01_apple_bag-clear_001.jpg", 7)
    img(tmp_path / "TP_S20261018-AB-01_apple_bag-clear_002.jpg", 7)
    img(tmp_path / "TP_S20261018-AB-01_carrot_hid-edge_003.jpg", 8)
    res = T.ingest(tmp_path)
    assert res["eval_groups"] == 2 and res["counts"] == {"J-eval": 3}


def test_exif_gps_refused(tmp_path):
    sessions(tmp_path, [["S20261018-AB-01", "Ali B", "", "", "eval", "CC-BY-4.0", "yes"]])
    p = tmp_path / "TP_S20261018-AB-01_apple_bag-clear_001.jpg"
    img(p, 9)
    im = Image.open(p); ex = im.getexif(); ex[34853] = {1: "N", 2: (31.0, 28.0, 0.0)}
    im.save(p, exif=ex)
    with pytest.raises(ValueError, match="GPS"):
        T.ingest(tmp_path)


def test_vocabulary_matches_revised_shot_list():
    # shot list section 6 (revision 38e6b0a): classes incl. `none`, seven eval conditions + `open` for train apples
    assert T.INTENDED == {"apple", "banana", "citrus_orange", "tomato", "carrot", "none"}
    assert T.EVAL_CONDITIONS == {"bag-clear", "bag-mesh", "tray-film", "hid-hand", "hid-fruit", "hid-edge", "hid-object"}
    assert T.CONDITIONS == T.EVAL_CONDITIONS | {"open"}
    assert T.COLUMNS == HDR


def test_none_negative_and_hid_object_in_eval_none_refused_in_train(tmp_path):
    sessions(tmp_path, [["S20261018-AB-01", "Ali B", "2026-10-18", "home kitchen", "eval", "CC-BY-4.0", "yes"]])
    img(tmp_path / "TP_S20261018-AB-01_none_bag-clear_001.jpg", 11)       # optional empty-bag negative
    img(tmp_path / "TP_S20261018-AB-01_carrot_hid-object_002.jpg", 12)
    res = T.ingest(tmp_path)
    by = {i["file"]: i for i in res["items"]}
    assert by["TP_S20261018-AB-01_none_bag-clear_001.jpg"]["intended_by_photographer"] == "none"
    assert by["TP_S20261018-AB-01_carrot_hid-object_002.jpg"]["condition"] == "hid-object"
    assert res["counts"] == {"J-eval": 2}
    sessions(tmp_path, [["S20261018-AB-01", "Omar F", "2026-10-18", "market", "train", "CC-BY-4.0", "yes"]])
    for f in list(tmp_path.glob("TP_*")): f.unlink()
    img(tmp_path / "TP_S20261018-AB-01_none_open_001.jpg", 13)
    with pytest.raises(ValueError, match="train sessions this round"):  # J4: apple/banana/tomato allowed, none refused
        T.ingest(tmp_path)


def test_sessions_csv_columns_enforced_and_values_trimmed(tmp_path):
    with open(tmp_path / "sessions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(HDR[:-1]); w.writerow(["S20261018-AB-01", "Ali B", "2026-10-18", "home", "eval", "CC-BY-4.0"])
    with pytest.raises(ValueError, match="columns must be exactly"):
        T.ingest(tmp_path)
    with open(tmp_path / "sessions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow([" " + h for h in HDR])
        w.writerow(["S20261018-AB-01", "Ali B", "2026-10-18", "home", " eval ", "CC-BY-4.0 ", "Yes"])
    img(tmp_path / "TP_S20261018-AB-01_banana_bag-mesh_001.jpg", 14)
    assert T.ingest(tmp_path)["counts"] == {"J-eval": 1}
