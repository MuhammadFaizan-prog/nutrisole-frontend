"""Strict Stage J CSV validation and hash-bound human self-attestation (stdlib only).

Self-attestation is evidence supplied by people, not proof of a person's identity. Never
generate completed attestations on someone's behalf. AI and smoke-test labels are excluded.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

LABELS = ["apple", "banana", "citrus_orange", "tomato", "carrot", "other_produce",
          "printed_or_screen", "occluded", "uncertain"]
COLUMNS = ["pack_id", "copy", "annotator", "item_id", "order_index", "label",
           "other_produce_name", "occluded_or_printed_what", "cut", "bag", "multi",
           "rotten_damaged", "note", "seconds", "labelled_at"]
TAGS = ["cut", "bag", "multi", "rotten_damaged"]
AI_MARKER = "AI_ASSISTED_NOT_HUMAN"
NONHUMAN = re.compile(r"\bai\b|ai[_ -]?assisted|not[_ -]?human|gpt|claude|llm|synthetic|testannotator|smoke.?test", re.I)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def frozen_digest(path):
    """Git-LF content hash for frozen TEXT manifests/gates, portable across checkouts.

    Never use this for images, submitted human/AI CSVs, or final frozen output evidence.
    Those require byte-exact digest(), with -text Git attributes for evidence storage.
    """
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def boolean(value, *, missing=False):
    if missing:
        return None
    v = str(value or "").strip().lower()
    if v in ("0", "false", ""):
        return 0
    if v in ("1", "true"):
        return 1
    raise ValueError(f"invalid boolean {value!r}")


def iso_time(value):
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if t.tzinfo is None:
            raise ValueError("timezone required")
        return t
    except (ValueError, AttributeError) as e:
        raise ValueError(f"invalid timestamp {value!r}") from e


def load_table(path, *, exact_schema=False):
    """Return raw string rows; reject duplicate IDs/columns, malformed CSV and bad values.

    Blank labels are allowed for partial human exports; AI import requires full coverage.
    Missing tag columns remain unknown. Blank fallback tag cells mean no tag, per guide.
    """
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, strict=True)
        fields = reader.fieldnames or []
        if len(set(fields)) != len(fields):
            raise ValueError("duplicate CSV columns")
        if exact_schema and fields != COLUMNS:
            raise ValueError(f"schema must be exactly {','.join(COLUMNS)}")
        if not {"item_id", "label"} <= set(fields):
            raise ValueError("schema requires item_id and label")
        rows, seen, order = [], set(), set()
        for r in reader:
            if None in r or any(v is None for v in r.values()):
                raise ValueError(f"CSV row {reader.line_num} has wrong field count")
            iid = r["item_id"].strip()
            if not iid or not re.fullmatch(r"[PT][0-9]{3,}", iid):
                raise ValueError(f"invalid or missing item_id {iid!r}")
            if iid in seen:
                raise ValueError(f"duplicate item_id {iid}")
            seen.add(iid)
            lab = r["label"].strip()
            if lab and lab not in LABELS:
                raise ValueError(f"invalid label {lab!r} for {iid}")
            for tag in TAGS:
                boolean(r.get(tag), missing=tag not in r)
                if exact_schema and r[tag].strip().lower() not in ("0", "1", "true", "false"):
                    raise ValueError(f"missing boolean {tag} for {iid}")
            if r.get("order_index", ""):
                v = r["order_index"]
                if not v.isdigit() or int(v) < 1 or int(v) in order:
                    raise ValueError(f"invalid/duplicate order_index {v!r}")
                order.add(int(v))
            elif exact_schema:
                raise ValueError(f"missing order_index for {iid}")
            if r.get("seconds", ""):
                try:
                    n = float(r["seconds"])
                    if not math.isfinite(n) or n < 0:
                        raise ValueError()
                except ValueError as e:
                    raise ValueError(f"invalid seconds for {iid}") from e
            if r.get("labelled_at"):
                iso_time(r["labelled_at"])
            r["item_id"], r["label"] = iid, lab
            rows.append(r)
    if not rows:
        raise ValueError("empty annotation CSV")
    return rows


def coverage(rows, expected, *, complete=False):
    actual = {r["item_id"] for r in rows}
    unexpected = actual - set(expected)
    missing = set(expected) - actual
    unlabelled = [r["item_id"] for r in rows if not r["label"]]
    if unexpected or (complete and (missing or unlabelled)):
        raise ValueError(f"coverage: missing={sorted(missing)}, unexpected={sorted(unexpected)}, unlabelled={unlabelled}")
    return not missing and not unlabelled


def label_fingerprint(rows):
    """Recognise a known AI payload even if name, copy, note, time or order were changed."""
    fields = ["item_id", "label", "other_produce_name", "occluded_or_printed_what"] + TAGS
    payload = [[boolean(r.get(k), missing=k not in r) if k in TAGS else r.get(k, "").strip()
                for k in fields] for r in sorted(rows, key=lambda r: r["item_id"])]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


AI_NEAR_COPY_MIN_ITEMS = 20
AI_NEAR_COPY_FRACTION = 0.95


def ai_near_copy(rows, ai_rows):
    """Fraction of shared item_ids whose label/name/what/tags payload equals a known AI table (None if too few shared)."""
    fields = ["label", "other_produce_name", "occluded_or_printed_what"] + TAGS
    key = lambda r: tuple(boolean(r.get(k), missing=k not in r) if k in TAGS else r.get(k, "").strip() for k in fields)
    ai = {r["item_id"]: key(r) for r in ai_rows}
    shared = [r for r in rows if r.get("item_id") in ai and r.get("label", "").strip()]
    if len(shared) < AI_NEAR_COPY_MIN_ITEMS:
        return None
    return sum(key(r) == ai[r["item_id"]] for r in shared) / len(shared)


def validate_ai(path, expected, *, batch="pilot"):
    """Validate one AI batch without accepting another batch's pack identity."""
    rows = load_table(path, exact_schema=True)
    coverage(rows, expected, complete=True)
    if any(r["pack_id"] != f"G9J-{batch}" for r in rows):
        raise ValueError(f"AI CSV pack_id must be G9J-{batch}")
    return dict(provenance=AI_MARKER, rows=rows, counts=dict(Counter(r["label"] for r in rows)),
                sha256=digest(path), label_fingerprint=label_fingerprint(rows))


def validate_human_pair(a, b, evidence, batch, expected, ai_paths=()):
    if not evidence:
        raise ValueError("independent human evidence is required (--evidence)")
    ev = json.loads(Path(evidence).read_text(encoding="utf-8-sig")) if not isinstance(evidence, dict) else evidence
    if ev.get("schema_version") != 1 or ev.get("provenance") != "HUMAN_INDEPENDENT" or ev.get("batch") != batch:
        raise ValueError("invalid independent human evidence provenance or batch")
    att = ev.get("annotators", [])
    if len(att) != 2:
        raise ValueError("evidence must contain two independent annotators")
    hashes = [digest(a), digest(b)]
    if hashes[0] == hashes[1]:
        raise ValueError("duplicate annotation files cannot establish independent humans")
    imported = Path(__file__).resolve().parents[1] / "out/handoff"
    known_ai = set(Path(p) for p in ai_paths)
    if imported.exists():
        known_ai.update(imported.glob("*/AI_ASSISTED_NOT_HUMAN/*.csv"))
    ai_tables = [load_table(p) for p in sorted(known_ai)]
    ai_fingerprints = {label_fingerprint(t) for t in ai_tables}
    names, tables = [], []
    complete = True
    for p, who, copy, h in zip((a, b), att, ("annotator1", "annotator2"), hashes):
        name = str(who.get("name", "")).strip()
        if not name or NONHUMAN.search(name) or who.get("copy") != copy:
            raise ValueError("honest human annotator name and original copy are required")
        if who.get("csv_sha256") != h:
            raise ValueError("evidence hash does not match CSV")
        if who.get("independently_labelled") is not True or who.get("no_ai_or_peer_labels_seen") is not True:
            raise ValueError("independence and no-AI/peer-exposure attestations are required")
        iso_time(who.get("attested_at", ""))
        rows = load_table(p)
        complete = coverage(rows, expected) and complete
        for r in rows:
            if r.get("annotator", "").strip() != name or NONHUMAN.search(r.get("annotator", "")):
                raise ValueError("CSV annotator differs from human evidence or contains AI/test identity")
            if "copy" in r and r["copy"] != copy:
                raise ValueError("CSV copy differs from original annotator pack")
            if "pack_id" in r and r["pack_id"] != f"G9J-{batch}":
                raise ValueError("CSV pack_id differs from requested batch")
            if r["label"] and "labelled_at" in r and not r["labelled_at"]:
                raise ValueError("labelled export row lacks timestamp")
        if label_fingerprint(rows) in ai_fingerprints:
            raise ValueError("known AI annotation payload cannot pass as independent human evidence")
        for t in ai_tables:
            frac = ai_near_copy(rows, t)
            if frac is not None and frac >= AI_NEAR_COPY_FRACTION:
                raise ValueError(f"near-copy of a known AI annotation payload ({frac:.0%} identical) cannot pass as independent human evidence")
        names.append(name)
        tables.append(rows)
    if names[0].casefold() == names[1].casefold():
        raise ValueError("two distinct human annotators are required")
    return dict(provenance="HUMAN_INDEPENDENT", complete=complete, names=names, sha256=hashes,
                tables=tables, evidence=ev, evidence_kind="hash-bound human self-attestation; identity not independently authenticated")
