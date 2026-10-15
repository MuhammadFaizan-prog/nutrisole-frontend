"""G9 Stage J: annotator agreement, adjudication sheet and verified manifest (standard library only; Pillow optional for review sheets).

  python3 j_agree.py agree A.csv B.csv --batch pilot --evidence E.json --out DIR  # original independent agreement and adjudication sheet
  python3 j_agree.py verify --batch pilot --agree-dir DIR [--adjudicated DIR/adjudication_sheet.csv] --out DIR
                                                                     # verified manifest (+ sha256 freeze) and readiness counts

Inputs: CSVs exported by the original labelling tool or fallback CSV, plus --evidence with hash-bound independent-human
self-attestations. Primary labels must use the original nine strings. Missing tag columns remain unknown and need adjudication.
Known AI payloads, smoke-test identities, duplicate IDs and invalid values are rejected before any report is written.
Rules (frozen, G9_stageJ_readiness.md):
  * An item is VERIFIED without adjudication only if both annotators gave the same label, neither said `uncertain`, and they agree on
    the `cut` and `bag` tags (these change what the item counts as). Everything else goes to the adjudicator.
  * The adjudicator writes `final_label` (one of the 9 labels, or `exclude`) and a reason. Final `uncertain` / `exclude` -> excluded.
  * Agreement is reported on items both annotators labelled: Cohen's kappa over the 9 labels (kappa(class)), one-vs-rest kappa per label,
    kappa(supported) for "one of the 5 priority classes" vs not, kappa(cut) and kappa(bag), and percent agreement.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys, shutil
from collections import Counter, defaultdict
from pathlib import Path
import j_annotation as V

LABELS = ["apple", "banana", "citrus_orange", "tomato", "carrot", "other_produce", "printed_or_screen", "occluded", "uncertain"]
PRIORITY = LABELS[:5]
ALIAS = {"orange": "citrus_orange", "citrus": "citrus_orange", "kinnow": "citrus_orange", "mandarin": "citrus_orange", "other": "other_produce",
         "printed": "printed_or_screen", "screen": "printed_or_screen", "unsure": "uncertain", "unknown": "uncertain", "1": "apple", "2": "banana",
         "3": "citrus_orange", "4": "tomato", "5": "carrot", "6": "other_produce", "7": "printed_or_screen", "8": "occluded", "9": "uncertain"}
# 13-way app class for an other_produce name (G9 H2 class map: ml/eval/h2_labels.py)
OTHER13 = {"lemon_or_lime": "lemon_lime", "mango": "mango", "guava": "guava", "pomegranate": "pomegranate", "potato": "potato",
           "cucumber": "cucumber", "capsicum_bell_pepper": "capsicum"}
CLASS13 = {"apple": "apple", "banana": "banana", "citrus_orange": "citrus", "tomato": "tomato", "carrot": "carrot"}
HERE = os.path.dirname(os.path.abspath(__file__)); OUTD = os.path.normpath(os.path.join(HERE, "..", "out"))

def norm_label(s: str) -> str | None:
    s = (s or "").strip().lower().replace(" ", "_").replace("-", "_")
    if not s: return ""
    s = ALIAS.get(s, s)
    return s if s in LABELS else None

def flag(v) -> int: return 1 if str(v or "").strip().lower() in ("1", "true", "yes", "y", "x") else 0

def read_csv(path: str) -> tuple[dict, list, str]:
    """Returns ({item_id: row}, invalid_rows, annotator_name)."""
    out, bad, names = {}, [], Counter()
    for r in V.load_table(path):
            iid = (r.get("item_id") or "").strip()
            if not iid: continue
            lab = norm_label(r.get("label", ""))
            if lab is None: bad.append((iid, r.get("label"))); lab = ""
            names[(r.get("annotator") or "").strip()] += 1
            out[iid] = dict(label=lab, other=(r.get("other_produce_name") or "").strip(), what=(r.get("occluded_or_printed_what") or "").strip(),
                            cut=V.boolean(r.get("cut"), missing="cut" not in r), bag=V.boolean(r.get("bag"), missing="bag" not in r),
                            multi=V.boolean(r.get("multi"), missing="multi" not in r), bad=V.boolean(r.get("rotten_damaged"), missing="rotten_damaged" not in r),
                            note=(r.get("note") or "").strip(), sheet=(r.get("contact_sheet") or "").strip())
    name = names.most_common(1)[0][0] if names else ""
    return out, bad, name

def cohen_kappa(a: list, b: list) -> float | None:
    if len(a) != len(b): raise ValueError("kappa inputs must have equal lengths")
    n = len(a)
    if n == 0: return None
    cats = sorted(set(a) | set(b)); po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b); pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    if pe >= 1.0: return None  # undefined, never a passing agreement score
    return (po - pe) / (1 - pe)

def confusion(a: list, b: list, cats=LABELS) -> list:
    m = [[0] * len(cats) for _ in cats]; ix = {c: i for i, c in enumerate(cats)}
    for x, y in zip(a, b): m[ix[x]][ix[y]] += 1
    return m

def key_path(batch: str) -> str:
    """Frozen blind key for a batch: pilot/train -> out/j_blind_key.csv; Stage J2 supplementary pilot2/train2 -> out/gaps/j2_blind_key.csv."""
    return os.path.join(OUTD, "gaps", "j2_blind_key.csv") if batch in ("pilot2", "train2") else os.path.join(OUTD, "j_blind_key.csv")

def load_key(batch: str) -> dict:
    p = key_path(batch)
    with open(p, newline="", encoding="utf-8-sig") as f:
        rows = [r for r in csv.DictReader(f) if r["batch"] == batch]
    if len({r["blind_id"] for r in rows}) != len(rows): raise ValueError("duplicate blind IDs in frozen key")
    return {r["blind_id"]: r for r in rows}

def disagreement_reasons(a, b):
    reasons = []
    if not a.get("label") or not b.get("label"): reasons.append("missing label (" + ("A" if not a.get("label") else "") + ("B" if not b.get("label") else "") + ")")
    elif a["label"] != b["label"]: reasons.append("labels differ")
    if "uncertain" in (a.get("label"), b.get("label")): reasons.append("uncertain")
    if a.get("label") and b.get("label"):
        if a["label"] == b["label"] == "other_produce" and a.get("other") != b.get("other"): reasons.append("subtype differs")
        if a["label"] == b["label"] and a["label"] in ("occluded", "printed_or_screen") and a.get("what") != b.get("what"): reasons.append("underlying item differs")
        if any(a.get(k) is None or b.get(k) is None for k in ("cut", "bag", "multi", "bad")): reasons.append("missing tag evidence")
        if any(a.get(k) != b.get(k) for k in ("cut", "bag")): reasons.append("cut/bag tag differs")
        if any(a.get(k) != b.get(k) for k in ("multi", "bad")): reasons.append("multi/bad tag differs")
    return reasons

def agree(args):
    key = load_key(args.batch)
    A, badA, nA = read_csv(args.a); B, badB, nB = read_csv(args.b)
    pair = V.validate_human_pair(args.a, args.b, args.evidence, args.batch, set(key) or (set(A) | set(B)), args.ai_csv)
    os.makedirs(args.out, exist_ok=False)  # version every run; never overwrite disagreement history
    inputs = Path(args.out) / "inputs"; inputs.mkdir()
    for path, name in ((args.a, "annotator1.csv"), (args.b, "annotator2.csv")):
        shutil.copyfile(path, inputs / name)
    (inputs / "human_evidence.json").write_text(json.dumps(pair["evidence"], ensure_ascii=False, indent=2), encoding="utf-8")
    ids = sorted(set(A) | set(B) | set(key))
    both = [i for i in ids if A.get(i, {}).get("label") and B.get(i, {}).get("label")]
    la = [A[i]["label"] for i in both]; lb = [B[i]["label"] for i in both]
    per = {}
    for c in LABELS:
        xa = [x == c for x in la]; xb = [y == c for y in lb]
        per[c] = dict(kappa=cohen_kappa(xa, xb), n_A=sum(xa), n_B=sum(xb), both=sum(p and q for p, q in zip(xa, xb)))
    sup = lambda L: [x in PRIORITY for x in L]
    rep = dict(batch=args.batch, annotator_A=nA, annotator_B=nB, file_A=os.path.basename(args.a), file_B=os.path.basename(args.b),
               n_items_expected=len(key) or None, n_labelled_A=sum(1 for v in A.values() if v["label"]), n_labelled_B=sum(1 for v in B.values() if v["label"]),
               n_both=len(both), invalid_labels_A=badA, invalid_labels_B=badB,
               percent_agreement=round(sum(x == y for x, y in zip(la, lb)) / len(both), 4) if both else None,
               kappa_class=cohen_kappa(la, lb),
               kappa_supported=cohen_kappa(sup(la), sup(lb)),
               kappa_cut=cohen_kappa([A[i]["cut"] for i in both if A[i]["cut"] is not None and B[i]["cut"] is not None], [B[i]["cut"] for i in both if A[i]["cut"] is not None and B[i]["cut"] is not None]),
               kappa_bag=cohen_kappa([A[i]["bag"] for i in both if A[i]["bag"] is not None and B[i]["bag"] is not None], [B[i]["bag"] for i in both if A[i]["bag"] is not None and B[i]["bag"] is not None]),
               per_class=per, uncertain_A=la.count("uncertain"), uncertain_B=lb.count("uncertain"),
               confusion_labels=LABELS, confusion_A_rows_B_cols=confusion(la, lb) if both else None)
    rep.update(provenance=pair["provenance"], human_evidence=pair["evidence_kind"], csv_sha256=pair["sha256"], complete_independent_coverage=pair["complete"],
               frozen_key_sha256=V.frozen_digest(key_path(args.batch)), evidence_sha256=sha256_file(inputs / "human_evidence.json"))
    rep["floors"] = dict(kappa_class_min=0.85, kappa_supported_min=0.80,
                         kappa_class_ok=rep["kappa_class"] is not None and rep["kappa_class"] >= 0.85,
                         kappa_supported_ok=rep["kappa_supported"] is not None and rep["kappa_supported"] >= 0.80)
    # disagreement list + adjudication sheet
    rows = []
    for i in ids:
        a, b = A.get(i, {}), B.get(i, {}); reasons = disagreement_reasons(a, b)
        if not reasons: continue
        tags = lambda r: "".join(t for t, k in (("C", "cut"), ("B", "bag"), ("M", "multi"), ("X", "bad")) if r.get(k))
        rows.append(dict(item_id=i, contact_sheet=a.get("sheet") or b.get("sheet") or "", page_url=key.get(i, {}).get("page_url", ""),
                         label_A=a.get("label", ""), other_A=a.get("other", ""), what_A=a.get("what", ""), tags_A=tags(a), note_A=a.get("note", ""),
                         label_B=b.get("label", ""), other_B=b.get("other", ""), what_B=b.get("what", ""), tags_B=tags(b), note_B=b.get("note", ""),
                         reason="; ".join(reasons), final_label="", final_other_produce_name="", final_cut="", final_bag="", final_multi="", final_rotten_damaged="",
                         final_occluded_or_printed_what="", adjudicator="", adjudicator_reason=""))
    cols = ["item_id", "contact_sheet", "page_url", "label_A", "other_A", "what_A", "tags_A", "note_A", "label_B", "other_B", "what_B", "tags_B", "note_B",
            "reason", "final_label", "final_other_produce_name", "final_cut", "final_bag", "final_multi", "final_rotten_damaged", "final_occluded_or_printed_what", "adjudicator", "adjudicator_reason"]
    with open(os.path.join(args.out, "adjudication_sheet.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    with open(os.path.join(args.out, "disagreements.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols[:14]); w.writeheader(); w.writerows([{k: r[k] for k in cols[:14]} for r in rows])
    with open(os.path.join(args.out, "confusion.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["A \\ B"] + LABELS)
        for c, r in zip(LABELS, rep["confusion_A_rows_B_cols"] or [[0] * 9] * 9): w.writerow([c] + r)
    rep["n_to_adjudicate"] = len(rows); rep["adjudication_reasons"] = Counter(x for r in rows for x in r["reason"].split("; "))
    abpath = Path(args.out) / "labels_AB.json"
    abpath.write_text(json.dumps(dict(A=A, B=B), ensure_ascii=False), encoding="utf-8")
    rep["labels_AB_sha256"] = sha256_file(abpath)
    report = Path(args.out) / "agreement.json"
    report.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    Path(str(report) + ".sha256").write_text(sha256_file(report) + "  agreement.json\n", encoding="utf-8")
    open(os.path.join(args.out, "agreement.md"), "w", encoding="utf-8").write(agreement_md(rep))
    if args.sheets: review_sheets(rows, args.batch, args.out)
    print(json.dumps({k: rep[k] for k in ("n_both", "percent_agreement", "kappa_class", "kappa_supported", "n_to_adjudicate", "floors")}, indent=1))
    return rep

def agreement_md(r: dict) -> str:
    L = [f"# Annotator agreement: {r['batch']}", "", f"- Annotator A: **{r['annotator_A']}** ({r['file_A']}), B: **{r['annotator_B']}** ({r['file_B']})",
         f"- Items expected {r['n_items_expected']}, labelled by A {r['n_labelled_A']}, by B {r['n_labelled_B']}, by both **{r['n_both']}**",
         f"- Percent agreement **{r['percent_agreement']}**; Cohen's kappa(class, 9 labels) **{r['kappa_class']}** (floor 0.85: "
         f"{'OK' if r['floors']['kappa_class_ok'] else 'NOT MET'}); kappa(supported) **{r['kappa_supported']}** (floor 0.80: "
         f"{'OK' if r['floors']['kappa_supported_ok'] else 'NOT MET'}); kappa(cut) {r['kappa_cut']}, kappa(bag) {r['kappa_bag']}",
         f"- Uncertain: A {r['uncertain_A']}, B {r['uncertain_B']}. Items sent to adjudication: **{r['n_to_adjudicate']}** {dict(r['adjudication_reasons'])}",
         f"- Invalid labels: A {len(r['invalid_labels_A'])}, B {len(r['invalid_labels_B'])}", "", "| Label | kappa (one-vs-rest) | A | B | both |", "|---|---|---|---|---|"]
    L += [f"| {c} | {v['kappa']} | {v['n_A']} | {v['n_B']} | {v['both']} |" for c, v in r["per_class"].items()]
    if r["confusion_A_rows_B_cols"]:
        L += ["", "Confusion (rows A, columns B):", "", "| A \\ B | " + " | ".join(LABELS) + " |", "|---" * 10 + "|"]
        L += [f"| {c} | " + " | ".join(str(x) for x in row) + " |" for c, row in zip(LABELS, r["confusion_A_rows_B_cols"])]
    return "\n".join(L) + "\n"

def review_sheets(rows, batch, out):
    """Contact sheets of the items to adjudicate, with both labels printed under each photo (needs Pillow + the local image store)."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception: return
    key = load_key(batch); os.makedirs(os.path.join(out, "adjudication_sheets"), exist_ok=True)
    def path(k):
        for p in (f"/workspace/work/g9i/cands/img/{k}.jpg", f"/workspace/work/g9j/train/img/{k}.jpg", f"/workspace/work/g9j2/eval2/img/{k}.jpg", f"/workspace/work/g9j2/train2/img/{k}.jpg"):
            if os.path.exists(p): return p
    try: F = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 15)
    except Exception: F = ImageFont.load_default()
    for s in range(0, len(rows), 12):
        sh = Image.new("RGB", (4 * 320, 3 * 380), "white"); d = ImageDraw.Draw(sh)
        for j, r in enumerate(rows[s:s + 12]):
            p = path(key.get(r["item_id"], {}).get("key", ""))
            x, y = (j % 4) * 320, (j // 4) * 380
            if p:
                im = Image.open(p).convert("RGB"); im.thumbnail((310, 300)); sh.paste(im, (x + 5, y + 5))
            d.text((x + 6, y + 310), r["item_id"], fill=(180, 0, 0), font=F)
            d.text((x + 6, y + 330), f"A: {r['label_A']} {r['tags_A']}"[:38], fill="black", font=F)
            d.text((x + 6, y + 350), f"B: {r['label_B']} {r['tags_B']}"[:38], fill="black", font=F)
        sh.save(os.path.join(out, "adjudication_sheets", f"adjudicate_{batch}_{s // 12 + 1:02d}.jpg"), quality=82)

def role_of(label: str, cut: int, bag: int, other: str) -> tuple[str, str]:
    """(role, class13). Roles: supported (clean whole priority item), supported_packaged, cut, other_class, unsupported, printed, occluded."""
    if label in PRIORITY:
        if cut: return "cut", CLASS13[label]
        return ("supported_packaged" if bag else "supported"), CLASS13[label]
    if label == "other_produce":
        c13 = OTHER13.get(other, "unknown"); return ("other_class" if c13 != "unknown" else "unsupported"), c13
    if label == "printed_or_screen": return "printed", "unknown"
    if label == "occluded": return "occluded", "unknown"
    return "excluded", ""

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 16), b""): h.update(ch)
    return h.hexdigest()

def verify(args):
    based = Path(args.agree_dir); rp = based / "agreement.json"
    if sha256_file(rp) != Path(str(rp) + ".sha256").read_text().split()[0]: raise ValueError("agreement history hash mismatch")
    report = json.loads(rp.read_text(encoding="utf-8"))
    key = load_key(args.batch)
    if report["batch"] != args.batch or report["frozen_key_sha256"] != V.frozen_digest(Path(key_path(args.batch))): raise ValueError("batch or frozen key changed")
    ABp = based / "labels_AB.json"
    if sha256_file(ABp) != report["labels_AB_sha256"]: raise ValueError("original label history hash mismatch")
    AB = json.loads(ABp.read_text(encoding="utf-8")); A, B = AB["A"], AB["B"]
    pair = V.validate_human_pair(based / "inputs/annotator1.csv", based / "inputs/annotator2.csv", based / "inputs/human_evidence.json", args.batch, set(key) or (set(A) | set(B)))
    if pair["sha256"] != report["csv_sha256"]: raise ValueError("original human input hashes changed")
    if read_csv(based / "inputs/annotator1.csv")[0] != A or read_csv(based / "inputs/annotator2.csv")[0] != B: raise ValueError("original human label history differs")
    adj, seen_adjudications = {}, set()
    if args.adjudicated and os.path.exists(args.adjudicated):
        for r in csv.DictReader(open(args.adjudicated, newline="", encoding="utf-8-sig")):
            fl = (r.get("final_label") or "").strip().lower()
            iid = r["item_id"]
            if iid in seen_adjudications: raise ValueError("duplicate adjudication item_id")
            seen_adjudications.add(iid)
            if iid not in set(A) | set(B) | set(key): raise ValueError("unexpected adjudication item_id")
            if fl:
                who = r.get("adjudicator", "").strip(); why = r.get("adjudicator_reason", "").strip()
                if not who or V.NONHUMAN.search(who) or who.casefold() in {n.casefold() for n in pair["names"]} or not why: raise ValueError("a third human adjudicator and reason are required")
                if fl not in LABELS + ["exclude"]: raise ValueError("invalid final label")
                adj[iid] = dict(label=fl, other=(r.get("final_other_produce_name") or "").strip(), cut=r.get("final_cut", ""), bag=r.get("final_bag", ""),
                                multi=r.get("final_multi", ""), bad=r.get("final_rotten_damaged", ""), what=r.get("final_occluded_or_printed_what", ""), who=who, why=why)
                for k in ("cut", "bag", "multi", "bad"):
                    adj[iid][k] = str(adj[iid][k] or "").strip()
                    if adj[iid][k] != "": V.boolean(adj[iid][k])
    key = load_key(args.batch); ids = sorted(set(A) | set(B) | set(key)); lic = {}
    for lp in ("j_licence.csv", "j_licence_train.csv", "gaps/j2_licence.csv"):
        p = os.path.join(OUTD, lp)
        if os.path.exists(p):
            with open(p, newline="", encoding="utf-8-sig") as f: lic.update({r["key"]: r for r in csv.DictReader(f)})
    identity = {}
    if args.identity_manifest:
        with open(args.identity_manifest, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                if row["key"] in identity: raise ValueError("duplicate original-identity key")
                identity[row["key"]] = row
    out, cnt = [], Counter()
    for i in ids:
        a, b = A.get(i, {}), B.get(i, {}); k = key.get(i, {})
        same = not disagreement_reasons(a, b)
        multi, damaged, what, why = a.get("multi"), a.get("bad"), a.get("what", ""), ""
        if same:
            lab, cut, bag, other, status, by = a["label"], a["cut"], a["bag"], a.get("other") or b.get("other") or "", "verified_agree", ""
        elif i in adj:
            d = adj[i]; lab = d["label"] or "uncertain"
            resolved = {}
            for tag in ("cut", "bag", "multi", "bad"):
                resolved[tag] = V.boolean(d[tag]) if d[tag] != "" else (a.get(tag) if a.get(tag) == b.get(tag) else None)
            cut, bag, multi, damaged = (resolved[t] for t in ("cut", "bag", "multi", "bad"))
            other = d["other"] if d["other"] else (a.get("other", "") if a.get("other") == b.get("other") else "")
            what = d["what"] if d["what"] else (a.get("what", "") if a.get("what") == b.get("what") else "")
            status, by, why = "verified_adjudicated", d["who"], d["why"]
            if lab in ("uncertain", "exclude"): status = "excluded_by_adjudicator"
            elif any(v is None for v in resolved.values()) or (lab == "other_produce" and not other): status = "pending_adjudication"
            elif lab in ("occluded", "printed_or_screen") and a.get("what") != b.get("what") and not d["what"]: status = "pending_adjudication"
        else:
            lab, cut, bag, other, status, by = "", 0, 0, "", "pending_adjudication", ""
        role, c13 = role_of(lab, cut, bag, other) if status.startswith("verified") else ("excluded" if status.startswith("excluded") else "pending", "")
        locations = [str(Path(d) / f"{k.get('key')}.jpg") for d in args.image_root]
        locations += [f"/workspace/work/g9i/cands/img/{k.get('key')}.jpg", f"/workspace/work/g9j/train/img/{k.get('key')}.jpg",
                      f"/workspace/work/g9j2/eval2/img/{k.get('key')}.jpg", f"/workspace/work/g9j2/train2/img/{k.get('key')}.jpg"]
        img = next((p for p in locations if os.path.exists(p)), None) if k else None
        L = lic.get(k.get("key", ""), {})
        image_hash = sha256_file(img) if img else ""
        original = identity.get(k.get("key", ""), {})
        identity_ok = bool(image_hash and original.get("image_sha256") == image_hash and original.get("source_url") == L.get("source_url") and original.get("file_url") == L.get("file_url"))
        out.append(dict(item_id=i, cand_key=k.get("key", ""), batch=args.batch, split=k.get("split", ""), source=k.get("source", ""), uploader=k.get("uploader", ""),
                        status=status, final_label=lab if status.startswith(("verified", "excluded")) else "", adjudicated_decision=adj.get(i, {}).get("label", ""), class13=c13, role=role, cut=cut, bag=bag, other_produce_name=other,
                        multi=multi, rotten_damaged=damaged, occluded_or_printed_what=what,
                        label_A=a.get("label", ""), label_B=b.get("label", ""), other_A=a.get("other", ""), other_B=b.get("other", ""),
                        adjudicator=by, adjudicator_reason=why, provenance="HUMAN_INDEPENDENT", licence=L.get("licence", ""), author=L.get("author", ""),
                        source_url=L.get("source_url", ""), image_sha256=image_hash, original_identity_verified=identity_ok,
                        release_eligible=bool(identity_ok and L.get("compliant") == "yes" and status.startswith("verified"))))
        cnt[status] += 1
    os.makedirs(args.out, exist_ok=False); mp = os.path.join(args.out, f"verified_manifest_{args.batch}.csv")
    saved_inputs = Path(args.out) / "inputs"; saved_inputs.mkdir()
    input_hashes = {}
    for p, name in ((args.adjudicated, "adjudicated.csv"), (args.identity_manifest, "original_identity_manifest.csv")):
        if p:
            shutil.copyfile(p, saved_inputs / name)
            input_hashes[name] = sha256_file(saved_inputs / name)
    with open(mp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    digest = sha256_file(mp); open(mp + ".sha256", "w").write(f"{digest}  {os.path.basename(mp)}\n")
    ver = [r for r in out if r["status"].startswith("verified")]
    eligible_split = "J-eval" if args.batch.startswith("pilot") else "J-train"
    sup = Counter(r["class13"] for r in ver if r["role"] == "supported" and r["split"] == eligible_split)
    neg = Counter(r["role"] for r in ver if r["split"] == eligible_split and r["role"] in ("unsupported", "other_class", "printed", "occluded", "cut", "supported_packaged"))
    gates = readiness_counts(args.batch, sup, neg, cnt)
    summ = dict(batch=args.batch, manifest=os.path.basename(mp), sha256=digest, status=cnt, supported_clean_by_class=sup, negatives_by_role=neg,
                provenance="HUMAN_INDEPENDENT", evidence_sha256=sha256_file(based / "inputs/human_evidence.json"), agreement_sha256=sha256_file(rp), input_sha256=input_hashes,
                original_kappa_class=report["kappa_class"], n_verified=len(ver), n_release_eligible=sum(r["release_eligible"] for r in ver),
                complete=pair["complete"] and cnt.get("pending_adjudication", 0) == 0, gates=gates,
                dev_clean_by_class=dict(Counter(r["class13"] for r in ver if r["split"] == "J-dev" and r["role"] == "supported")),
                train_sources_by_class={c: sorted({r["source"] for r in ver if r["split"] == "J-train" and r["role"] == "supported" and r["class13"] == c}) for c in CLASS13.values()})
    if not pair["complete"]:
        summ["gates"]["adjudication_complete"] = False
        summ["gates"]["R2_met" if args.batch.startswith("pilot") else "T1_met"] = False
    json.dump(summ, open(os.path.join(args.out, f"verified_summary_{args.batch}.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1)); return summ

def readiness_counts(batch, sup, neg, cnt):
    """Frozen count gates (G9_stageJ_readiness.md R2 / T1). Packaged supported items and cut items count as negatives (must not be graded)."""
    if batch.startswith("pilot"):   # pilot2 alone is reported with the same gates; R2 is judged on pilot + pilot2 combined (G9_stageJ_gaps.md)
        negs = sum(neg.values()); g = dict(
            supported_per_class_ge20={c: sup.get(c, 0) >= 20 for c in ("apple", "banana", "citrus", "tomato", "carrot")},
            supported_total_ge100=sum(sup.get(c, 0) for c in ("apple", "banana", "citrus", "tomato", "carrot")) >= 100, negatives_ge60=negs >= 60,
            unsupported_ge25=neg.get("unsupported", 0) + neg.get("other_class", 0) >= 25, printed_ge10=neg.get("printed", 0) >= 10,
            packaging_ge10=neg.get("supported_packaged", 0) >= 10, occluded_ge10=neg.get("occluded", 0) >= 10, adjudication_complete=cnt.get("pending_adjudication", 0) == 0)
        g["R2_met"] = all(v if not isinstance(v, dict) else all(v.values()) for k, v in g.items() if k in ("supported_per_class_ge20", "supported_total_ge100", "negatives_ge60", "adjudication_complete"))
        g["R2_subquotas_met"] = all(g[k] for k in ("unsupported_ge25", "printed_ge10", "packaging_ge10", "occluded_ge10"))
        return g
    g = dict(train_supported_per_class_ge150={c: sup.get(c, 0) >= 150 for c in ("apple", "banana", "citrus", "tomato", "carrot")},
             adjudication_complete=cnt.get("pending_adjudication", 0) == 0)
    g["T1_met"] = all(g["train_supported_per_class_ge150"].values()) and g["adjudication_complete"]; return g

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter); sp = ap.add_subparsers(dest="cmd", required=True)
    a = sp.add_parser("agree"); a.add_argument("a"); a.add_argument("b"); a.add_argument("--batch", required=True, choices=["pilot", "train", "pilot2", "train2"])
    a.add_argument("--out", required=True); a.add_argument("--sheets", action="store_true", help="also draw adjudication contact sheets")
    a.add_argument("--evidence", required=True, help="hash-bound independent-human self-attestations JSON")
    a.add_argument("--ai-csv", action="append", default=[], help="known AI CSV to reject even if annotator names were changed")
    v = sp.add_parser("verify"); v.add_argument("--batch", required=True, choices=["pilot", "train", "pilot2", "train2"]); v.add_argument("--agree-dir", required=True)
    v.add_argument("--adjudicated"); v.add_argument("--out", required=True)
    v.add_argument("--image-root", action="append", default=[], help="original image directory (source keys as filenames), repeatable")
    v.add_argument("--identity-manifest", help="ingestion provenance CSV: key,image_sha256,source_url,file_url; missing chain never release-eligible")
    args = ap.parse_args(argv)
    return agree(args) if args.cmd == "agree" else verify(args)

if __name__ == "__main__":
    main()
