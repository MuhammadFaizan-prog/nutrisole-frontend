"""Read-only Stage J handoff audit. Never trains, relabels, repartitions or opens holdout images.

Run --help for inputs. Output directories are versioned: existing reports are never replaced.
The audit/review output is for the project lead AFTER independent annotation, never for annotators.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import html as html_lib
import io
import json
import re
import shutil
import tempfile
import unicodedata
import zipfile
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path, PurePosixPath

import j_annotation as V
import j_agree as J

STAGE = Path(__file__).resolve().parents[1]
ROOT = STAGE.parents[3]
OUT = STAGE / "out"
REPORTED_AI = dict(apple=19, banana=18, citrus_orange=18, tomato=20, carrot=30,
                   other_produce=42, printed_or_screen=37, occluded=0, uncertain=81)
AI_FILES = ["nutrisole_G9J_AI_assisted_pilot_labels_265.csv", "nutrisole_G9J_AI_review_queue.csv",
            "nutrisole_G9J_AI_annotation_handoff_README.txt"]


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def read_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, strict=True))


def write_new(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as f:
        f.write(content)


def write_json(path, data):
    write_new(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def write_csv(path, fields, rows):
    b = io.StringIO(newline="")
    w = csv.DictWriter(b, fields)
    w.writeheader()
    w.writerows(rows)
    write_new(path, b.getvalue())


def inspect_pack(path):
    """Safely extract into a fresh temporary directory, decode every embedded photograph.

    Package JPEG hashes establish identity BETWEEN COPIES, not copyright or original-source identity.
    """
    from PIL import Image, ImageStat
    import imagehash

    path = Path(path)
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            p = PurePosixPath(info.filename)
            if p.is_absolute() or ".." in p.parts or "\\" in info.filename or ":" in info.filename or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"unsafe ZIP member {info.filename}")
        if len(set(z.namelist())) != len(z.namelist()):
            raise ValueError("duplicate ZIP member names")
        if sum(i.file_size for i in z.infolist()) > 512 * 1024 * 1024:
            raise ValueError("ZIP exceeds 512 MiB audit limit")
        crc = z.testzip()
        if crc:
            raise ValueError(f"corrupt ZIP member {crc}")
        with tempfile.TemporaryDirectory(prefix="nutrisole-g9j-audit-") as temp:
            target = Path(temp).resolve()
            if not target.is_relative_to(Path(tempfile.gettempdir()).resolve()):
                raise ValueError("temporary directory escaped intended root")
            z.extractall(target)
            files = list(target.glob("*.html"))
            if len(files) != 1:
                raise ValueError("expected exactly one offline HTML tool")
            text = files[0].read_text(encoding="utf-8")
            match = re.search(r'<script id="data" type="application/json">(.*?)</script>', text, re.S)
            if not match:
                raise ValueError("embedded photo data not found")
            data = json.loads(match.group(1))
            fb = next(target.glob("fallback/fallback_*.csv"))
            fallback = read_rows(fb)
            images, errors = {}, []
            ids = [r["id"] for r in data]
            duplicates = sorted(i for i, n in Counter(ids).items() if n > 1)
            for item in data:
                iid = item["id"]
                try:
                    if not item["src"].startswith("data:image/jpeg;base64,"):
                        raise ValueError("image is not an embedded JPEG")
                    raw = base64.b64decode(item["src"].split(",", 1)[1], validate=True)
                    Image.open(io.BytesIO(raw)).verify()
                    with Image.open(io.BytesIO(raw)) as im:
                        im.load()
                        images[iid] = dict(sha256=hashlib.sha256(raw).hexdigest(), width=im.width, height=im.height,
                                           phash=str(imagehash.phash(im)), mean_luminance=round(ImageStat.Stat(im.convert("L")).mean[0], 2))
                except Exception as e:
                    errors.append(dict(item_id=iid, issue=str(e)))
            external = re.findall(r'<(?:script|link|img)\b[^>]*(?:src|href)=[\'"](https?://[^\'"]+)', text, re.I)
            cols = re.search(r"const COLS = (\[.*?\]);", text)
            schema = json.loads(cols.group(1)) if cols else None
            guide = target / "annotation_guide.md"
            copy = re.search(r'COPY\s*=\s*[\'"]([^\'"]+)', text)
            pack = re.search(r'PACK\s*=\s*[\'"]([^\'"]+)', text)
            return dict(package=path.name, sha256=V.digest(path), bytes=path.stat().st_size, crc_ok=True,
                        count=len(ids), ids=ids, images=images, duplicate_ids=duplicates, corrupt_images=errors,
                        order_matches_fallback=ids == [r["item_id"] for r in fallback],
                        fallback_unlabelled=all(not r["label"] and not r["annotator"] for r in fallback),
                        export_columns=schema, offline_external_resources=external,
                        guide_sha256=V.digest(guide), copy=copy.group(1) if copy else "", pack_id=pack.group(1) if pack else "")


def normal_person(value):
    s = html_lib.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    s = "".join(c for c in unicodedata.normalize("NFKD", s.casefold()) if not unicodedata.combining(c))
    s = re.sub(r"[^\w]+", " ", s).strip()
    if len(s) < 3 or re.search(r"unknown|anonymous|unbekannt|author unknown", s) or s in ("own work", "self", "public domain"):
        return ""
    return s


def audit_splits(items):
    """Recompute separation from stored hashes and metadata; do not mutate frozen membership."""
    owners = defaultdict(list)
    conflicts, quarantine = [], set()
    rank = {"J-eval": 0, "J-dev": 1, "J-train": 2}
    for k, v in items.items():
        if v["source"] in ("commons", "commons_t"):
            # One namespace catches uploader<->artist crossings, unlike the old separate prefixes.
            groups = {"person:" + normal_person(v.get(f, "")) for f in ("uploader", "artist") if normal_person(v.get(f, ""))}
        else:
            groups = {"dataset:" + v["source"]}
        groups.add("duplicate_group:" + v.get("group", k))
        for g in groups:
            owners[g].append(k)
    for group, keys in owners.items():
        if len({items[k]["split"] for k in keys}) > 1:
            keep = min((items[k]["split"] for k in keys), key=lambda s: rank[s])
            quarantine.update(k for k in keys if items[k]["split"] != keep)
            conflicts.append(dict(kind="source_or_group", group=group, keys=sorted(keys)))
    hashes = [(k, int(v["phash"], 16)) for k, v in items.items() if re.fullmatch(r"[0-9a-fA-F]{16}", v.get("phash", ""))]
    for (ka, ha), (kb, hb) in combinations(hashes, 2):
        if items[ka]["split"] == items[kb]["split"]:
            continue
        distance = (ha ^ hb).bit_count()
        if distance <= 10:
            loser = max((ka, kb), key=lambda k: rank[items[k]["split"]])
            quarantine.add(loser)
            conflicts.append(dict(kind="phash", keys=[ka, kb], hamming=distance))
    return dict(conflicts=conflicts, quarantine_keys=sorted(quarantine),
                items_checked=len(items), stored_phashes_checked=len(hashes),
                method="person (uploader and artist unified), dataset, group, 64-bit pHash Hamming <=10",
                earlier_reference_hashes_available=False,
                limit="Original image store, video/session IDs and /workspace/work/g9h reference hashes unavailable; no earlier holdout content opened.")


def _auth(report, batch):
    sha = lambda value: isinstance(value,str) and re.fullmatch(r"[0-9a-f]{64}",value) is not None
    if not report or report.get("batch") != batch or report.get("provenance") != "HUMAN_INDEPENDENT" or not sha(report.get("evidence_sha256")):
        return False
    if "csv_sha256" in report:
        hashes=report["csv_sha256"]
        return isinstance(hashes,list) and len(hashes)==2 and hashes[0]!=hashes[1] and all(sha(h) for h in hashes) and sha(report.get("document_sha256"))
    return sha(report.get("agreement_sha256")) and sha(report.get("sha256"))


def _linked(agreement, verified, batch):
    return (_auth(agreement,batch) and _auth(verified,batch)
            and verified["agreement_sha256"]==agreement["document_sha256"]
            and verified["evidence_sha256"]==agreement["evidence_sha256"]
            and verified.get("original_kappa_class")==agreement.get("kappa_class"))


def assess_readiness(pilot_agreement=None, pilot_verified=None, train_agreement=None, train_verified=None,
                     split_audit=None, licence_pass=False, freeze=None):
    pa, pv, ta, tv = pilot_agreement or {}, pilot_verified or {}, train_agreement or {}, train_verified or {}
    requirements = []

    def gate(i, ok, missing):
        requirements.append(dict(id=i, status="READY" if ok else "BLOCKED", missing_evidence=[] if ok else [missing]))

    def kappa(r, batch, supported=False):
        v = r.get("kappa_supported" if supported else "kappa_class")
        return _auth(r,batch) and v is not None and v >= (0.80 if supported else 0.85) and r.get("complete_independent_coverage") is True

    pilot_linked,train_linked=_linked(pa,pv,"pilot"),_linked(ta,tv,"train")
    gate("R1", kappa(pa,"pilot") and kappa(pa,"pilot",True), "Two independent full pilot CSVs, hash-bound human attestations, original kappa(class)>=0.85 and kappa(supported)>=0.80.")
    gate("R2", pilot_linked and pv.get("gates", {}).get("R2_met") is True,
         "Human-verified J-eval: >=20 clean per priority class, >=100 total, >=60 negatives; no AI/source labels count.")
    gate("R3", pilot_linked and pv.get("complete") is True, "100% independent coverage and third-human decisions/reasons for all disagreements, uncertain items and subtype/tag mismatches.")
    gate("R4", bool(pilot_linked and freeze and freeze.get("committed_before_any_eval_model") is True and freeze.get("manifest_sha256") == pv.get("sha256")),
         "Commit and timestamp evidence for the final manifest + SHA256 freeze before any J-eval model run; no such freeze exists.")
    volume = train_linked and all(tv.get("supported_clean_by_class", {}).get(c, 0) >= 150 and len(tv.get("train_sources_by_class", {}).get(c, [])) >= 2 for c in J.CLASS13.values())
    gate("T1", bool(volume and tv.get("phone_style_source_evidence")), ">=150 clean independently reviewed J-train examples/class, >=2 independent sources/class and documented handheld/phone-style coverage.")
    gate("T2", train_linked and sum(tv.get("negatives_by_role", {}).values()) >= 150, ">=150 human-verified real-photo J-train negatives.")
    gate("T3", train_linked and all(tv.get("dev_clean_by_class", {}).get(c, 0) >= 10 for c in J.CLASS13.values()), ">=10 human-verified clean examples/class in J-dev, never counted as J-train.")
    gate("T4", kappa(ta,"train") and train_linked and tv.get("complete") is True, "Independent training-batch CSVs, original kappa(class)>=0.85 and completed adjudication.")
    separation = split_audit and not split_audit.get("conflicts") and split_audit.get("earlier_reference_hashes_available") is True
    gate("T5", bool(licence_pass and separation), "Per-image permission + attribution tied to downloaded identity, raw image/source/session provenance and pHash audit against earlier stored reference hashes; preserve all exclusions.")
    return dict(status="READY" if all(r["status"] == "READY" for r in requirements) else "BLOCKED",
                training_authorized=False, user_go_required_after_readiness=True, gpu_training_started=False,
                stage_j_complete=False, requirements=requirements,
                metric_subquotas=dict(status="PENDING_HUMAN_LABELS", unsupported=25, printed=10, packaging=10, occluded=10,
                                      note="R2 subquota deficits block dependent E metrics; do not fill them from training sources."),
                future_model_gates=dict(genuine_pooled_min=0.60, genuine_commons_min=0.60, genuine_phone_min=0.50,
                                        genuine_per_class_min=0.40, wrong_id_max=0.02, wrong_identity_grades=0,
                                        note="Frozen Wilson rules and remaining E1-E8 apply. These are future acceptance gates, not training permission."))


def provenance_rows(pack, blind, partitions):
    licences = read_rows(OUT / "j_licence.csv") + read_rows(OUT / "j_licence_train.csv")
    inverse = {r["key"]: r["blind_id"] for r in blind}
    result = []
    for r in licences:
        k = r["key"]
        v = partitions["items"].get(k, {})
        bid = inverse.get(k, "")
        im = pack["images"].get(bid, {})
        excluded = r.get("compliant") != "yes" or k in partitions["licence_excluded"]
        historical_q = partitions["quarantined"].get(k, "")
        reason = r.get("issue", "") or historical_q or "original downloaded-file SHA256 and byte-to-source chain unavailable"
        result.append(dict(key=k, blind_id=bid, source=r["source"], source_url=r.get("source_url", ""),
                           file_url_or_archive_member=r.get("file_url", ""), copyright_author_recorded=r.get("author", ""),
                           photographer_or_uploader=r.get("uploader", ""), credit_recorded=r.get("credit", ""),
                           licence_recorded=r.get("licence", ""), licence_url_recorded=r.get("licence_url", ""),
                           attribution_required_recorded="yes" if r.get("licence", "").upper().startswith("CC BY") else "see recorded terms",
                           redistribution_and_training="RECORDED_TERMS_ONLY_UNVERIFIED_BYTE_CHAIN", historical_compliant=r.get("compliant", ""),
                           split=v.get("split", "EXCLUDED_OR_NOT_IN_FINAL_PARTITIONS"), duplicate_group=v.get("group", ""),
                           original_sha256="", package_jpeg_sha256=im.get("sha256", ""), original_identity_verified="false",
                           human_verified="false", audit_status="EXCLUDED_PRESERVE" if excluded else "QUARANTINED_PRESERVE" if historical_q else "NEEDS_REVIEW",
                           release_quarantined="true", issue=reason))
    return result


def review_rows(blind, images, ai=None, queue=None):
    ai_by_id = {r["item_id"]: r for r in (ai or {}).get("rows", [])}
    queued = {r.get("item_id", "") for r in queue or []}
    out = []
    for r in blind:
        if r["batch"] != "pilot":
            continue
        iid = r["blind_id"]
        a = ai_by_id.get(iid, {})
        desc = (r.get("page_url", "") + " " + a.get("note", "") + " " + a.get("other_produce_name", "")).casefold()
        categories = []
        if a.get("label") == "uncertain": categories.append("no_identifiable_target_or_ambiguous")
        if r["source_label"] in ("citrus", "lemon_lime") or re.search(r"lemon|lime|orange|kinnow|malta", desc): categories.append("citrus_orange_vs_lemon_lime")
        if r["source_label"] == "apple": categories.append("apple_vs_unsupported_fruit")
        if re.search(r"pepper|capsicum|chili|chilli", desc): categories.append("bell_pepper_vs_chili")
        if r["source_kind"] == "printed" or re.search(r"painting|still.life|portrait|relief|drawing|canvas|sculpt|poster|toy", desc): categories.append("printed_or_artificial_fruit")
        if r["source_kind"] == "occluded" or a.get("label") == "occluded" or a.get("bag") in ("1", "true"):
            categories.append("potential_occlusion_verify_less_than_half_visible")
        if r["source_kind"] == "packaging": categories.append("packaging_or_occlusion")
        if re.search(r"basket|bowl|market|pile|mixed", desc) or a.get("multi") == "1": categories.append("mixed_pile_central_item")
        im = images.get(iid, {})
        if min(im.get("width", 0), im.get("height", 0)) < 256 or im.get("mean_luminance", 100) < 75:
            categories.append("poor_lighting_or_inadequate_resolution_proxy")
        if a and r["source_label"] in J.CLASS13.values() and a["label"] != next((lab for lab, cl in J.CLASS13.items() if cl == r["source_label"]), ""):
            categories.append("potential_wrong_produce_class_source_comparison_only")
        if not categories: categories.append("central_item_and_blur_visual_check_pending")
        out.append(dict(item_id=iid, priority=1 if iid in queued or a.get("label") == "uncertain" or "potential_occlusion_verify_less_than_half_visible" in categories else 2,
                        categories=";".join(categories), ai_label=a.get("label", ""), original_ai_queue="true" if iid in queued else "false" if queue is not None else "MISSING_INPUT",
                        evidence="AI_ASSISTED_NOT_HUMAN+SOURCE_METADATA_UNVERIFIED" if a else "SOURCE_METADATA_UNVERIFIED; AI_INPUT_MISSING",
                        original_full_resolution_available="false", available_view="package JPEG <=640px; not a full-resolution original", source_url=r["page_url"],
                        human_action="inspect original source after independent exports; apply authoritative guide; no confident relabeling by automation",
                        independent_annotators_must_not_see="true"))
    return sorted(out, key=lambda r: (r["priority"], r["item_id"]))


def training_preparation(dest, blind, partitions):
    import random
    rows = [r for r in blind if r["batch"] == "train"]
    ids = sorted(r["blind_id"] for r in rows)
    if len(ids) != len(set(ids)) or any(r["split"] not in ("J-train", "J-dev") for r in rows):
        raise ValueError("training blind key duplicates or contains eval")
    fields = ["item_id", "label", "other_produce_name", "occluded_or_printed_what", "cut", "bag", "multi", "rotten_damaged", "note", "annotator", "contact_sheet"]
    for copy, seed in (("annotator1", 101), ("annotator2", 202)):
        order = ids[:]
        random.Random(seed).shuffle(order)
        folder = dest / "training_preparation" / copy
        write_csv(folder / f"fallback_train_{copy}.csv", fields,
                  [dict(dict.fromkeys(fields, ""), item_id=i) for i in order])
        write_new(folder / "START_HERE.txt", f"PREPARATION ONLY: {len(ids)} frozen training-batch IDs, no labels.\nNOT DISTRIBUTABLE: original training photos/ZIP must be recovered and SHA256 checked.\nUse the original annotation guide; annotate independently, with no AI/peer suggestions.\nDo not treat J-dev as training data. No evaluation images may be added.\n")
    groups = Counter(r["split"] for r in rows)
    gap = []
    for label, cl in J.CLASS13.items():
        cands = [r for r in rows if r["split"] == "J-train" and r["source_kind"] == "supported" and r["source_label"] == cl]
        gap.append(dict(label=label, j_train_source_candidates=len(cands), human_verified_clean=0, target=150,
                        additional_clean_needed_even_if_every_candidate_passes=max(0, 150-len(cands)),
                        actual_human_verified_shortfall=150, source_collections=";".join(sorted({r["source"] for r in cands})),
                        requirements="licensed diverse phone close-ups; >=2 independent sources; exclude eval sources, video/session/near-duplicate overlap"))
    write_csv(dest / "G9J_training_gap.csv", list(gap[0]), gap)
    write_new(dest / "G9J_training_pack_status.md", f"# Training pack status\n\n**BLOCKED: original training ZIPs and image stores missing locally.**\n\nFrozen blind key: {len(rows)} representatives ({groups['J-train']} J-train, {groups['J-dev']} J-dev). The guide's 458 is stale; 461 is supported by the key, batch JSON and recorded package inventories. Physical training ZIP image count is unverified until recovered.\n\nBlank fallback preparations retain separate deterministic orders and contain no suggestions. They cannot be distributed as usable packs without the original photos. Recover the two original ZIPs; compare to the SHA256 values in j_packs.json. Do not regenerate photos from evaluation data.\n\nCandidate counts are source labels, not human verification. See G9J_training_gap.csv. All five classes still need 150 verified clean examples; apple/banana/tomato are especially short. J-train has 65 source-tagged negative representatives against 150 verified required (best-case gap 85). Dev source-candidate counts are apple 10, banana 7, citrus 15, tomato 4, carrot 9; minimum raw deficits are 0,3,0,6,1, before human rejection. Source collection names are not proof of independent photographers or phone capture.\n")
    return dict(representatives=len(rows), by_split=dict(groups), image_files_available=False, gaps=gap)


def audit(args):
    dest = Path(args.out)
    # Refuse overwrite before doing any expensive checks.
    if dest.exists() and any(p.name != "G9J_frozen_inputs.json" for p in dest.iterdir()):
        raise ValueError("use a new versioned output directory; existing audit history is immutable")
    packs = [inspect_pack(args.pack1), inspect_pack(args.pack2)]
    blind = read_rows(OUT / "j_blind_key.csv")
    expected = {r["blind_id"] for r in blind if r["batch"] == "pilot"}
    records = read_json(OUT / "j_packs.json")
    integrity = []
    for iid in sorted(expected | set(packs[0]["ids"]) | set(packs[1]["ids"])):
        ia, ib = [p["images"].get(iid, {}) for p in packs]
        problems = []
        if iid not in expected: problems.append("unexpected ID")
        if not ia or not ib: problems.append("missing or corrupt image")
        if ia and ib and ia["sha256"] != ib["sha256"]: problems.append("mismatched image hash")
        if any(iid in p["duplicate_ids"] for p in packs): problems.append("duplicate ID")
        integrity.append(dict(item_id=iid, status="PASS" if not problems else "FAIL", issue="; ".join(problems),
                              annotator1_order=packs[0]["ids"].index(iid)+1 if iid in packs[0]["ids"] else "",
                              annotator2_order=packs[1]["ids"].index(iid)+1 if iid in packs[1]["ids"] else "",
                              annotator1_sha256=ia.get("sha256", ""), annotator2_sha256=ib.get("sha256", ""),
                              width=ia.get("width", ""), height=ia.get("height", ""), package_phash=ia.get("phash", ""),
                              identity_scope="same packaged JPEG in both copies; original-source byte identity unverified"))
    write_csv(dest / "G9J_pilot_integrity_report.csv", list(integrity[0]), integrity)
    psummary = []
    for p, old, copy in zip(packs, records["pilot"], ("annotator1", "annotator2")):
        checks = dict(count_265=p["count"]==265, expected_ids=set(p["ids"])==expected, no_duplicates=not p["duplicate_ids"],
                      no_corrupt=not p["corrupt_images"], original_package_sha256=p["sha256"]==old["sha256"],
                      correct_copy=p["copy"]==copy, correct_pack=p["pack_id"]=="G9J-pilot",
                      export_schema=p["export_columns"]==V.COLUMNS, fallback_order=p["order_matches_fallback"],
                      offline_resources=not p["offline_external_resources"], authoritative_guide=p["guide_sha256"]==V.digest(ROOT / "docs/cv/gauntlet/G9_stageJ_annotation_guide.md"))
        psummary.append(dict(package=p["package"], sha256=p["sha256"], checks=checks, pass_all=all(checks.values())))
    dup = []
    for a, b in combinations(sorted(packs[0]["images"]), 2):
        ia, ib = packs[0]["images"][a], packs[0]["images"][b]
        d = (int(ia["phash"],16)^int(ib["phash"],16)).bit_count()
        if ia["sha256"]==ib["sha256"] or d<=10:
            dup.append(dict(item_id_A=a, item_id_B=b, exact_sha256=ia["sha256"]==ib["sha256"], phash_hamming=d,
                            status="AUTOMATED_CANDIDATE_NEEDS_HUMAN_REVIEW"))
    write_csv(dest / "G9J_duplicate_candidates.csv", ["item_id_A","item_id_B","exact_sha256","phash_hamming","status"], dup)
    ai, ai_errors, queue = None, [], None
    if args.ai_csv:
        try:
            ai = V.validate_ai(args.ai_csv, expected)
            folder = dest / V.AI_MARKER; folder.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.ai_csv, folder / f"{ai['sha256']}.csv")
            write_json(folder / "provenance.json", {k:v for k,v in ai.items() if k!="rows"})
        except (ValueError, UnicodeError, csv.Error) as e:
            ai_errors.append(str(e))
    if args.review_queue:
        queue = read_rows(args.review_queue)
        qids = [r.get("item_id", "") for r in queue]
        if len(set(qids)) != len(qids) or set(qids)-expected:
            raise ValueError("AI review queue contains duplicate or unexpected item IDs")
    summary = [dict(label=label, reported_unverified_count=REPORTED_AI[label],
                    imported_count=ai["counts"].get(label,0) if ai else "", comparison="MATCH" if ai and ai["counts"].get(label,0)==REPORTED_AI[label] else "DISCREPANCY" if ai else "MISSING_INPUT_NOT_VALIDATED",
                    provenance=V.AI_MARKER if ai else "MISSING_INPUT", human_verified="false") for label in V.LABELS]
    write_csv(dest / "G9J_AI_annotation_summary.csv", list(summary[0]), summary)
    reviews = review_rows(blind, packs[0]["images"], ai, queue)
    write_csv(dest / "G9J_review_priority.csv", list(reviews[0]), reviews)
    partitions = read_json(OUT / "j_partitions.json")
    split = audit_splits(partitions["items"])
    manifest = read_rows(OUT / "j_manifest_candidates.csv")
    mismatch = [r["key"] for r in manifest if r["key"] not in partitions["items"] or r["split"]!=partitions["items"][r["key"]]["split"]]
    split["manifest_mismatch_keys"] = mismatch
    historical = read_json(STAGE.parent / "stageI/out/i_leak_split.json")
    old_eval = {k for k,v in historical["items"].items() if v["split"].startswith("I-eval")}
    now_eval = {k for k,v in partitions["items"].items() if v["split"]=="J-eval"}
    split["stageI_eval_difference"] = dict(stageI=len(old_eval), stageJ=len(now_eval), removed=sorted(old_eval-now_eval), added=sorted(now_eval-old_eval))
    split["previous_quarantines_preserved"] = partitions["quarantined"]
    split["licence_exclusions_preserved"] = partitions["licence_excluded"]
    write_json(dest / "G9J_dataset_split_audit.json", split)
    write_csv(dest / "G9J_split_quarantine.csv", ["key","reason","action"], [dict(key=k,reason=";".join(str(c) for c in split["conflicts"] if k in c.get("keys",[])),action="exclude from future eligible input; preserve frozen membership") for k in split["quarantine_keys"]])
    prov = provenance_rows(packs[0], blind, partitions)
    write_csv(dest / "G9J_license_and_provenance_audit.csv", list(prov[0]), prov)
    train = training_preparation(dest, blind, partitions)
    missing = ([AI_FILES[0]] if not args.ai_csv else []) + ([AI_FILES[1]] if not args.review_queue else []) + ([AI_FILES[2]] if not args.ai_readme else [])
    if args.ai_readme:
        readme = Path(args.ai_readme).read_text(encoding="utf-8-sig")
        write_new(dest / V.AI_MARKER / "input_README_verbatim.txt", readme)
    readiness = assess_readiness(split_audit=split, licence_pass=False)
    write_json(dest / "G9J_H3_readiness.json", readiness)
    ev = dict(schema_version=1, provenance="HUMAN_INDEPENDENT", batch="pilot", annotators=[dict(name="", copy=c, csv_sha256="", independently_labelled=False,
              no_ai_or_peer_labels_seen=False, attested_at="") for c in ("annotator1","annotator2")])
    write_json(dest / "human_evidence.BLANK.template.json", ev)
    audit_summary = dict(base_commit="4d35a7c426cbb2820fa80d98e2a7a357bc0c3d36", packages=psummary,
                         image_identity_pass=all(r["status"]=="PASS" for r in integrity), different_order=packs[0]["ids"]!=packs[1]["ids"],
                         duplicate_candidates=dup, ai_imported=bool(ai), ai_imported_rows=len(ai["rows"]) if ai else 0,
                         ai_errors=ai_errors, missing_inputs=missing, review_queue_rows=len(queue) if queue is not None else None,
                         claimed_review_queue_rows_unverified=113, claimed_uncertain_rows_unverified=81,
                         human_csvs_received=0, human_kappa=None, human_verified_images=0, training=train,
                         original_source_store_available=False, weight_binaries_available_locally=False,
                         evidence_scope="AUTOMATED_CHECKS; source metadata remains unverified; no model evaluated or trained")
    write_json(dest / "G9J_audit_summary.json", audit_summary)
    write_new(dest / "G9J_dataset_split_audit.md", f"# Dataset split audit\n\n**Automated checks on recorded manifests; original-byte/reference-store verification pending.**\n\nAudited {len(partitions['items'])} items ({dict(Counter(v['split'] for v in partitions['items'].values()))}), including stored 64-bit pHashes, unified uploader/artist identity, dataset and duplicate groups. Cross-split conflicts: {len(split['conflicts'])}; manifest mismatches: {len(mismatch)}.\n\nStage I versus Stage J eval: {split['stageI_eval_difference']}. The removed c0350 was license-excluded previously; the old claim that membership was entirely unchanged needs this qualification. No membership was changed in this handoff. Pilot IDs remain {len(expected)} J-eval-only.\n\nPreserved {len(partitions['quarantined'])} previous quarantine decisions and {len(partitions['licence_excluded'])} license exclusions. Original video/session metadata and earlier /workspace/work/g9h/eval_hashes.json, hset/hhash.json and refhash.json are missing. Their claimed reference comparison cannot be reproduced locally. M-TEST images were never opened. New cross-split conflicts, if any, are listed in G9J_split_quarantine.csv; eval stays frozen.\n")
    write_new(dest / "G9J_agreement_report.md", "# Independent-human agreement — PENDING\n\nNo genuine human CSVs have been supplied. Cohen's kappa and observed agreement are **not calculated**. No confusion matrix or adjudication queue is fabricated. The checked-in TestAnnotator 3-of-265 files are smoke tests only.\n\nRun j_agree.py agree with two original-copy exports and real hash-bound independent-human attestations. It joins stable item IDs, preserves both original CSVs, compares all tags/subtypes and emits only disagreements/uncertain/missing items for a third human. Adjudication does not alter the original agreement score. Constant-category kappa is undefined.\n")
    write_new(dest / "G9J_human_annotation_status.md", "# Human annotation status\n\n**PENDING — 0 genuine human exports; 0 human-verified images.**\n\n1. Annotator 1 labels the original pilot annotator1 ZIP independently and exports CSV.\n2. A different person labels original annotator2 ZIP independently and exports CSV. Neither may see AI suggestions, source-label keys, this audit/review directory, or the peer's answers first.\n3. Each person supplies the hash-bound self-attestation in the blank template using their real name, CSV SHA256, timezone-bearing timestamp and truthful independence/no-exposure declarations. Do not let an AI complete these statements. Self-attestation is not independent authentication of identity. If already exposed to AI labels, report it; do not falsely attest independence.\n4. Run agreement. A third person fills every disputed/uncertain case, final tags/subtype and a reason; use full-resolution source originals. Preserve both original labels and the original kappa.\n5. Recover the two original training ZIPs/image store; double-annotate the separate 461-item training/dev batch. Collect additional licensed diverse close-ups from training-only sources to close the gaps.\n6. Freeze the final human manifests in Git, complete original-byte/license/source/earlier-reference checks, then reassess R1-R4 and T1-T5. H3 remains blocked and requires a later explicit go.\n\nThe supplied extracted fallback CSVs have 265 blank labels each. Work saved in a person's browser must be exported by that person. No browser storage was accessed.\n")
    write_new(dest / "G9J_AI_handoff_audit.md", f"# G9 Stage J AI handoff audit — 2026-10-15\n\n**H3: BLOCKED. Stage J human verification is pending. No training or model promotion occurred.**\n\nBoth original pilot ZIPs were extracted into temporary directories without modifying them. Package checks: {json.dumps(psummary,ensure_ascii=False)}. Stable-ID/image comparison: {audit_summary['image_identity_pass']}; different order: {audit_summary['different_order']}. All images are package JPEGs bounded to 640 pixels, not full-resolution source originals. Full-resolution difficult-case review remains pending.\n\nAI CSV imported: {audit_summary['ai_imported_rows']} rows. Missing required files: {', '.join(missing) or 'none'}. Errors: {ai_errors}. The request's distribution (including 81 uncertain) and 113-row queue are reported claims, not verified inputs. No rows were invented. A supplied valid AI CSV is preserved byte-for-byte under AI_ASSISTED_NOT_HUMAN with its SHA256.\n\nG9J_review_priority.csv covers all 265 pilot IDs for post-hoc checks, using clearly marked source metadata/quality proxies{'; actual AI queue joined by ID' if queue is not None else '; original AI queue missing'}. It is not a replacement for the missing 113-row queue. Source-tagged occlusion candidates are P020, P052, P082, P143, P197; their source titles include art/reliefs and may instead be printed/artificial/no-target. All need genuine independent labeling; source tags do not settle the answer.\n\nFound {len(dup)} exact/perceptual duplicate candidates within pilot (see separate CSV). Source-level splits rechecked on 956 stored items; no new split changes. Earlier locked-reference stores, original file hashes, video/session records and full-resolution images are absent. Historical licensing records cover 742 Stage I + 276 extra training candidates. Six license exclusions and 14 quarantines remain. Every unbound original-byte identity remains release-quarantined; recorded CC/PD metadata is not proof that a particular packaged JPEG is that licensed original.\n\nTraining inventory is 461 representatives (382 J-train + 79 J-dev) per the actual frozen key, not the stale 458 guide statement. Original training ZIPs/image files are missing; prepared blank CSVs cannot replace those photos. See training pack/gap reports.\n\nChanges extend the existing agreement workflow with strict import, provenance/independence evidence, known-AI rejection, all subtype/tag comparisons, immutable agreement history, a distinct third adjudicator and reason, missing-tag handling, and undefined-kappa handling. Human self-attestation is necessary but cannot cryptographically prove humanity or honesty.\n\nG3 champion configuration, H0/H1/H2 history, grading/ripeness, prices, nutrition, camera, backend and lifestyle modules were not edited. Model checkpoint binaries are not present in this Windows checkout; existing artifact references remain intact. No claim is made that missing binary checkpoints were locally revalidated. Frozen file hashes are recorded in G9J_frozen_inputs.json.\n\nSee G9J_human_annotation_status.md for the exact human handoff and docs/cv/gauntlet/G9J_handoff_workflow.md for reproducible commands. This directory is lead/adjudicator-only until both independent exports are complete.\n")
    print(json.dumps({k:audit_summary[k] for k in ("image_identity_pass","different_order","ai_imported_rows","missing_inputs","human_kappa")},indent=2))
    return audit_summary


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--pack1", required=True)
    p.add_argument("--pack2", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--ai-csv")
    p.add_argument("--review-queue")
    p.add_argument("--ai-readme")
    return audit(p.parse_args(argv))


if __name__ == "__main__":
    main()
