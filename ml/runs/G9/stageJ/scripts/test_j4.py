"""G9 Stage J4 tests (synthetic fixtures + read-only checks of committed keys). No training, no labels."""
import csv, hashlib, io, json, sys, zipfile
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j4_verify_handoff as VH
import j_team_phone as T

HDR = ["session_id", "photographer", "date", "place", "purpose", "licence", "consent_confirmed"]


def _zip(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for n, b in members: z.writestr(n, b)
    return buf.getvalue()


def _handoff(tmp, inner_extra=b"", outer_extra=None):
    inner = _zip([("START_HERE.txt", b"hi"), ("tool.html", b"<html>" + inner_extra + b"</html>"),
                  ("fallback/fallback_pilot_annotator1.csv", b"item_id,label\nP001,\nP002,\nP003,\n")])
    outer_members = [("nutrisole_G9J_pilot_annotator1.zip", inner), ("annotation_guide.md", b"guide")] + (outer_extra or [])
    outer = _zip(outer_members)
    adj = _zip([("ADJUDICATION_INSTRUCTIONS.md", b"after both exports you receive the AI_ASSISTED_NOT_HUMAN zip")])
    h = tmp / "handoff"; h.mkdir()
    (h / "NutriSole_G9J_ANNOTATOR_A.zip").write_bytes(outer); (h / "NutriSole_G9J_ADJUDICATOR.zip").write_bytes(adj)
    sha = lambda b: hashlib.sha256(b).hexdigest()
    man = dict(zips={"NutriSole_G9J_ANNOTATOR_A.zip": dict(sha256=sha(outer), members=[n for n, _ in outer_members]),
                     "NutriSole_G9J_ADJUDICATOR.zip": dict(sha256=sha(adj), members=["ADJUDICATION_INSTRUCTIONS.md"])},
               inner_packs={"nutrisole_G9J_pilot_annotator1.zip": dict(sha256=sha(inner), recorded_sha256=sha(inner), items=3)})
    mp = tmp / "manifest.json"; mp.write_text(json.dumps(man)); (h / "HANDOFF_MANIFEST.json").write_text(json.dumps(man))
    return h, mp


def test_verify_passes_on_intact_handoff(tmp_path):
    h, mp = _handoff(tmp_path)
    r = VH.verify(h, mp)
    assert r["result"] == "PASS", r["failures"]
    assert r["inner_packs"]["nutrisole_G9J_pilot_annotator1.zip"]["items"] == 3
    assert r["ai_leak"]["NutriSole_G9J_ADJUDICATOR.zip"] == "instruction-text only (expected)"


def test_verify_fails_on_tampered_zip(tmp_path):
    h, mp = _handoff(tmp_path)
    p = h / "NutriSole_G9J_ANNOTATOR_A.zip"; p.write_bytes(p.read_bytes() + b"x")
    r = VH.verify(h, mp)
    assert r["result"] == "FAIL" and any("zip sha" in f for f in r["failures"])


def test_verify_flags_ai_material_inside_annotator_pack(tmp_path):
    h, mp = _handoff(tmp_path, inner_extra=b"G9J_AI_per_image_review")
    r = VH.verify(h, mp)
    assert r["result"] == "FAIL" and any("AI leak" in f for f in r["failures"])


def test_committed_manifest_covers_all_four_batches_with_expected_sizes():
    man = json.loads(VH.MANIFEST.read_text())
    items = {k: v["items"] for k, v in man["inner_packs"].items()}
    for copy in ("annotator1", "annotator2"):
        assert items[f"nutrisole_G9J_pilot_{copy}.zip"] == 265 and items[f"nutrisole_G9J_pilot2_{copy}.zip"] == 335
        assert items[f"nutrisole_G9J_train_{copy}.zip"] == 461 and items[f"nutrisole_G9J_train2_{copy}.zip"] == 646


def test_frozen_eval_and_training_keys_are_disjoint():
    """Phase-2 leakage rule: no evaluation item (pilot, pilot2) may appear in a training batch (train, train2)."""
    out = HERE.parent / "out"
    rows = list(csv.DictReader(open(out / "j_blind_key.csv", encoding="utf-8"))) + \
        list(csv.DictReader(open(out / "gaps/j2_blind_key.csv", encoding="utf-8")))
    ev = [r for r in rows if r["batch"] in ("pilot", "pilot2")]
    tr = [r for r in rows if r["batch"] in ("train", "train2")]
    assert len(ev) == 600 and len(tr) == 1107
    assert all(r["split"] == "J-eval" for r in ev) and all(r["split"] in ("J-train", "J-dev") for r in tr)
    assert not ({r["key"] for r in ev} & {r["key"] for r in tr})
    assert not ({r["blind_id"] for r in ev} & {r["blind_id"] for r in tr})
    commons_up = lambda rs: {r["uploader"] for r in rs if r["source"] == "commons"}
    assert not (commons_up(ev) & commons_up(tr))


def _img(path, seed):
    rng = np.random.default_rng(seed)
    Image.fromarray((rng.random((8, 8, 3)) * 255).astype("uint8")).resize((256, 256), Image.NEAREST).save(path, quality=95)


def _tiny_refs(tmp):
    tmp = tmp.parent / (tmp.name + "_refs"); tmp.mkdir(exist_ok=True)
    sets = {"synthetic_train": dict(role="train_source", count=0, hashes=[])}
    p = tmp / "refs.json"; txt = json.dumps(dict(sets=sets)); p.write_text(txt)
    Path(str(p) + ".sha256").write_text(hashlib.sha256(txt.encode()).hexdigest() + "  refs.json\n")
    return p


def _sessions(root, rows):
    with open(root / "sessions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(HDR); w.writerows(rows)


def test_train_sessions_accept_shortage_classes_apple_banana_tomato(tmp_path):
    _sessions(tmp_path, [["S20261020-EF-01", "Omar F", "2026-10-20", "market", "train", "internal-FYP", "yes"]])
    for n, c in enumerate(("apple", "banana", "tomato"), 1):
        _img(tmp_path / f"TP_S20261020-EF-01_{c}_open_{n:03d}.jpg", 300 + n)
    res = T.ingest(tmp_path, ref_manifest=_tiny_refs(tmp_path))
    assert res["counts"] == {"J-train": 3}
    assert {i["intended_by_photographer"] for i in res["items"]} == {"apple", "banana", "tomato"}
    assert all(i["human_verified"] is False for i in res["items"])


def test_train_sessions_refuse_other_classes_and_hidden_conditions(tmp_path):
    _sessions(tmp_path, [["S20261020-EF-01", "Omar F", "2026-10-20", "market", "train", "internal-FYP", "yes"]])
    _img(tmp_path / "TP_S20261020-EF-01_carrot_open_001.jpg", 311)
    with pytest.raises(ValueError, match="train sessions this round cover"):
        T.ingest(tmp_path, ref_manifest=_tiny_refs(tmp_path))
    (tmp_path / "TP_S20261020-EF-01_carrot_open_001.jpg").unlink()
    _img(tmp_path / "TP_S20261020-EF-01_apple_bag-clear_001.jpg", 312)
    with pytest.raises(ValueError, match="condition 'open'"):
        T.ingest(tmp_path, ref_manifest=_tiny_refs(tmp_path))
