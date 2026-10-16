"""H3 launch guard / kernel dry run / comparison tests. Synthetic fixtures only; no real labels, no training of the real model."""
import csv, hashlib, json, sys
from pathlib import Path

import pytest

H3 = Path(__file__).resolve().parent
sys.path.insert(0, str(H3)); sys.path.insert(0, str(H3 / "kernel"))
import h3_guard as GU
import h3_compare as CP
import run_h3 as K

COLS = ["item_id", "cand_key", "batch", "split", "source", "status", "class13", "role", "provenance"]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def batch(tmp, name, rows, kappa=0.9, ks=0.9):
    vd, ad = tmp / f"v_{name}", tmp / f"a_{name}"; vd.mkdir(); ad.mkdir()
    mp = vd / f"verified_manifest_{name}.csv"
    with open(mp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS); w.writeheader(); w.writerows(rows)
    Path(str(mp) + ".sha256").write_text(sha(mp) + "  x\n")
    ap = ad / "agreement.json"; ap.write_text(json.dumps(dict(provenance="HUMAN_INDEPENDENT", kappa_class=kappa, kappa_supported=ks)))
    Path(str(ap) + ".sha256").write_text(sha(ap) + "  agreement.json\n")
    (vd / f"verified_summary_{name}.json").write_text(json.dumps(dict(provenance="HUMAN_INDEPENDENT", sha256=sha(mp), agreement_sha256=sha(ap), complete=True)))
    return dict(verify_dir=str(vd), agree_dir=str(ad))


def rows_eval(prefix, per=12, src="commons"):
    r = []
    for c in ("apple", "banana", "citrus", "tomato", "carrot"):
        r += [dict(item_id=f"{prefix}{c}{k}", cand_key=f"{prefix}k{c}{k}", batch="x", split="J-eval", source=src, status="verified_agree", class13=c,
                   role="supported", provenance="HUMAN_INDEPENDENT") for k in range(per)]
    for role, n in (("unsupported", 14), ("printed", 6), ("supported_packaged", 6), ("occluded", 6)):
        r += [dict(item_id=f"{prefix}{role}{k}", cand_key=f"{prefix}k{role}{k}", batch="x", split="J-eval", source=src, status="verified_agree", class13="unknown",
                   role=role, provenance="HUMAN_INDEPENDENT") for k in range(n)]
    return r


def rows_train(prefix, per=80, src=("commons", "mendeley")):
    r = []
    for c in ("apple", "banana", "citrus", "tomato", "carrot"):
        for k in range(per):
            r.append(dict(item_id=f"{prefix}{c}{k}", cand_key=f"{prefix}t{c}{k}", batch="x", split="J-train", source=src[k % 2], status="verified_agree",
                          class13=c, role="supported", provenance="HUMAN_INDEPENDENT"))
        r += [dict(item_id=f"{prefix}d{c}{k}", cand_key=f"{prefix}d{c}{k}", batch="x", split="J-dev", source=src[0], status="verified_agree", class13=c,
                   role="supported", provenance="HUMAN_INDEPENDENT") for k in range(5)]
    r += [dict(item_id=f"{prefix}n{k}", cand_key=f"{prefix}n{k}", batch="x", split="J-train", source=src[0], status="verified_agree", class13="unknown",
               role="unsupported", provenance="HUMAN_INDEPENDENT") for k in range(80)]
    return r


def good_inputs(tmp):
    return dict(batches=dict(pilot=batch(tmp, "pilot", rows_eval("P")), pilot2=batch(tmp, "pilot2", rows_eval("Q")),
                             train=batch(tmp, "train", rows_train("T")), train2=batch(tmp, "train2", rows_train("U"))))


def test_guard_refuses_today_without_any_human_evidence(tmp_path):
    rc = GU.main(["--inputs", str(tmp_path / "missing.json"), "--go", str(tmp_path / "nogo.json"), "--report", str(tmp_path / "r.json")])
    r = json.loads((tmp_path / "r.json").read_text())
    assert rc == 2 and r["verdict"] == "REFUSED" and any("no verified human manifests" in p for p in r["problems"])
    assert any("training-go" in p for p in r["training_go_problems"])


def test_guard_passes_gates_but_refuses_without_user_go(tmp_path):
    inp = good_inputs(tmp_path); ip = tmp_path / "in.json"; ip.write_text(json.dumps(inp))
    res = GU.evaluate(inp)
    assert res["ready"], res["problems"]
    assert GU.main(["--inputs", str(ip), "--go", str(tmp_path / "nogo.json")]) == 2


def test_guard_pass_requires_go_naming_plan_and_manifests(tmp_path):
    inp = good_inputs(tmp_path); ip = tmp_path / "in.json"; ip.write_text(json.dumps(inp)); res = GU.evaluate(inp)
    go = dict(go=True, experiment="H3", given_by="M Faizan", given_at="2026-11-01T18:00:00+05:00", plan_sha256=sha(GU.PLAN), manifest_sha256=res["manifests"])
    gp = tmp_path / "go.json"; gp.write_text(json.dumps(go))
    assert GU.main(["--inputs", str(ip), "--go", str(gp)]) == 0
    gp.write_text(json.dumps(dict(go, plan_sha256="0" * 64)))
    assert GU.main(["--inputs", str(ip), "--go", str(gp)]) == 2
    gp.write_text(json.dumps(dict(go, given_by="AI_ASSISTED_NOT_HUMAN")))
    assert GU.main(["--inputs", str(ip), "--go", str(gp)]) == 2


def test_guard_refuses_low_kappa_short_counts_and_leaks(tmp_path):
    inp = good_inputs(tmp_path)
    inp["batches"]["pilot"] = batch(tmp_path, "pilotlow", rows_eval("P"), kappa=0.70)
    (Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_summary_pilotlow.json").rename(Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_summary_pilot.json")
    (Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_manifest_pilotlow.csv").rename(Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_manifest_pilot.csv")
    (Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_manifest_pilotlow.csv.sha256").rename(Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_manifest_pilot.csv.sha256")
    res = GU.evaluate(inp)
    assert not res["ready"] and res["gates"]["R1_pilot"] is False
    tmp2 = tmp_path / "b"; tmp2.mkdir(); inp2 = good_inputs(tmp2)
    inp2["batches"]["train2"] = batch(tmp2, "train2x", rows_train("U", per=10))
    for suf in ("verified_summary_{}.json", "verified_manifest_{}.csv", "verified_manifest_{}.csv.sha256"):
        d = Path(inp2["batches"]["train2"]["verify_dir"]); (d / suf.format("train2x")).rename(d / suf.format("train2"))
    r2 = GU.evaluate(inp2)
    assert r2["gates"]["T1_volume_ge150_per_class"] is False
    tmp3 = tmp_path / "c"; tmp3.mkdir(); inp3 = good_inputs(tmp3)
    leak = rows_train("T") + [dict(rows_eval("P")[0], split="J-train")]                 # an eval item reused for training
    inp3["batches"]["train"] = batch(tmp3, "trainleak", leak)
    for suf in ("verified_summary_{}.json", "verified_manifest_{}.csv", "verified_manifest_{}.csv.sha256"):
        d = Path(inp3["batches"]["train"]["verify_dir"]); (d / suf.format("trainleak")).rename(d / suf.format("train"))
    assert GU.evaluate(inp3)["gates"]["T5_separation"] is False


def test_guard_rejects_tampered_manifest(tmp_path):
    inp = good_inputs(tmp_path)
    mp = Path(inp["batches"]["pilot"]["verify_dir"]) / "verified_manifest_pilot.csv"
    mp.write_text(mp.read_text().replace("verified_agree", "verified_adjudicated", 1))
    res = GU.evaluate(inp)
    assert not res["ready"] and any("hash mismatch" in p for p in res["problems"])


def test_kernel_dry_run_cpu_seconds_pt_before_onnx(tmp_path):
    rep = K.main(["--dry-run", "--out", str(tmp_path)])
    assert rep["mode"] == "dry_run" and rep["eval_split_read"] is False and rep["artefact_order"][0] == "pt_saved"
    assert (tmp_path / "h3_mnv3s.pt").exists() and rep["seconds"] < 60 and rep["n_train"] > 0 and rep["n_dev"] > 0


def test_kernel_refuses_eval_rows_in_real_manifest(tmp_path):
    m = tmp_path / "m.csv"
    with open(m, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["path", "class13", "role", "split", "source"]); w.writerow(["x.jpg", "apple", "supported", "J-eval", "commons"])
    with pytest.raises(SystemExit, match="J-eval must never be read"):
        K.main(["--manifest", str(m), "--out", str(tmp_path)])


def test_compare_known_values_and_grading_safety():
    truth = {"a": dict(class13="apple", role="supported"), "b": dict(class13="banana", role="supported"),
             "c": dict(class13="unknown", role="printed"), "d": dict(class13="unknown", role="occluded")}
    preds = [dict(item_id="a", arm="H3", pred_class13="apple", accepted=1, graded=0, latency_ms=30),
             dict(item_id="b", arm="H3", pred_class13="apple", accepted=1, graded=1, latency_ms=40),
             dict(item_id="c", arm="H3", pred_class13="unknown", accepted=0, graded=0, latency_ms=20),
             dict(item_id="d", arm="H3", pred_class13="tomato", accepted=1, graded=0, latency_ms=70)]
    m = CP.metrics(truth, preds)["H3"]; g = CP.gates({"H3": m}, None)["H3"]
    assert m["genuine_acceptance"] == (1, 2) and m["wrong_id"] == (1, 2) and m["wrong_id_graded"] == 1
    assert m["occluded_accept"] == (1, 1) and m["any_graded"] == 1
    assert g["grading_safety_zero_graded"] == "FAIL" and g["E2_zero_graded"] == "FAIL" and g["E6_latency"] == "FAIL"


def test_compare_dry_run_is_marked_synthetic(tmp_path):
    CP.main(["--dry-run", "--out", str(tmp_path / "t.md")])
    assert (tmp_path / "t.md").read_text().startswith("# SYNTHETIC DRY RUN - not results")
