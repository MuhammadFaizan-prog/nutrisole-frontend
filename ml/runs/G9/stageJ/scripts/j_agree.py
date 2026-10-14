"""G9 Stage J: annotator agreement, adjudication sheet and verified manifest (standard library only; Pillow optional for review sheets).

  python3 j_agree.py agree  A.csv B.csv --batch pilot --out DIR      # kappa, confusion, disagreements, adjudication sheet (+ contact sheets)
  python3 j_agree.py verify --batch pilot --agree-dir DIR [--adjudicated DIR/adjudication_sheet.csv] --out DIR
                                                                     # verified manifest (+ sha256 freeze) and readiness counts

Inputs: CSVs exported by the labelling tool (columns item_id,label,other_produce_name,occluded_or_printed_what,cut,bag,multi,
rotten_damaged,note,annotator,...) or the fallback CSV (same names; missing columns are treated as empty). Labels are normalised
(case, spaces, a few obvious aliases); anything else is reported as invalid and treated as missing.
Rules (frozen, G9_stageJ_readiness.md):
  * An item is VERIFIED without adjudication only if both annotators gave the same label, neither said `uncertain`, and they agree on
    the `cut` and `bag` tags (these change what the item counts as). Everything else goes to the adjudicator.
  * The adjudicator writes `final_label` (one of the 9 labels, or `exclude`) and a reason. Final `uncertain` / `exclude` -> excluded.
  * Agreement is reported on items both annotators labelled: Cohen's kappa over the 9 labels (kappa(class)), one-vs-rest kappa per label,
    kappa(supported) for "one of the 5 priority classes" vs not, kappa(cut) and kappa(bag), and percent agreement.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, os, sys
from collections import Counter, defaultdict

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
    with open(path, newline="", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            iid = (r.get("item_id") or "").strip()
            if not iid: continue
            lab = norm_label(r.get("label", ""))
            if lab is None: bad.append((iid, r.get("label"))); lab = ""
            names[(r.get("annotator") or "").strip()] += 1
            out[iid] = dict(label=lab, other=(r.get("other_produce_name") or "").strip(), what=(r.get("occluded_or_printed_what") or "").strip(),
                            cut=flag(r.get("cut")), bag=flag(r.get("bag")), multi=flag(r.get("multi")), bad=flag(r.get("rotten_damaged")),
                            note=(r.get("note") or "").strip(), sheet=(r.get("contact_sheet") or "").strip())
    name = names.most_common(1)[0][0] if names else ""
    return out, bad, name

def cohen_kappa(a: list, b: list) -> float | None:
    n = len(a)
    if n == 0: return None
    cats = sorted(set(a) | set(b)); po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b); pe = sum(ca[c] * cb[c] for c in cats) / (n * n)
    if pe >= 1.0: return 1.0 if po == 1.0 else 0.0   # both annotators used one single category: kappa undefined; report 1 if identical
    return (po - pe) / (1 - pe)

def confusion(a: list, b: list, cats=LABELS) -> list:
    m = [[0] * len(cats) for _ in cats]; ix = {c: i for i, c in enumerate(cats)}
    for x, y in zip(a, b): m[ix[x]][ix[y]] += 1
    return m

def load_key(batch: str) -> dict:
    p = os.path.join(OUTD, "j_blind_key.csv")
    if not os.path.exists(p): return {}
    return {r["blind_id"]: r for r in csv.DictReader(open(p, newline="")) if r["batch"] == batch}

def agree(args):
    A, badA, nA = read_csv(args.a); B, badB, nB = read_csv(args.b); os.makedirs(args.out, exist_ok=True)
    key = load_key(args.batch); ids = sorted(set(A) | set(B) | set(key))
    both = [i for i in ids if A.get(i, {}).get("label") and B.get(i, {}).get("label")]
    la = [A[i]["label"] for i in both]; lb = [B[i]["label"] for i in both]
    per = {}
    for c in LABELS:
        xa = [x == c for x in la]; xb = [y == c for y in lb]
        per[c] = dict(kappa=None if not both else round(cohen_kappa(xa, xb), 4), n_A=sum(xa), n_B=sum(xb), both=sum(p and q for p, q in zip(xa, xb)))
    sup = lambda L: [x in PRIORITY for x in L]
    rep = dict(batch=args.batch, annotator_A=nA, annotator_B=nB, file_A=os.path.basename(args.a), file_B=os.path.basename(args.b),
               n_items_expected=len(key) or None, n_labelled_A=sum(1 for v in A.values() if v["label"]), n_labelled_B=sum(1 for v in B.values() if v["label"]),
               n_both=len(both), invalid_labels_A=badA, invalid_labels_B=badB,
               percent_agreement=round(sum(x == y for x, y in zip(la, lb)) / len(both), 4) if both else None,
               kappa_class=None if not both else round(cohen_kappa(la, lb), 4),
               kappa_supported=None if not both else round(cohen_kappa(sup(la), sup(lb)), 4),
               kappa_cut=None if not both else round(cohen_kappa([A[i]["cut"] for i in both], [B[i]["cut"] for i in both]), 4),
               kappa_bag=None if not both else round(cohen_kappa([A[i]["bag"] for i in both], [B[i]["bag"] for i in both]), 4),
               per_class=per, uncertain_A=la.count("uncertain"), uncertain_B=lb.count("uncertain"),
               confusion_labels=LABELS, confusion_A_rows_B_cols=confusion(la, lb) if both else None)
    rep["floors"] = dict(kappa_class_min=0.85, kappa_supported_min=0.80,
                         kappa_class_ok=rep["kappa_class"] is not None and rep["kappa_class"] >= 0.85,
                         kappa_supported_ok=rep["kappa_supported"] is not None and rep["kappa_supported"] >= 0.80)
    # disagreement list + adjudication sheet
    rows = []
    for i in ids:
        a, b = A.get(i, {}), B.get(i, {}); reasons = []
        if not a.get("label") or not b.get("label"): reasons.append("missing label (" + ("A" if not a.get("label") else "") + ("B" if not b.get("label") else "") + ")")
        elif a["label"] != b["label"]: reasons.append("labels differ")
        if "uncertain" in (a.get("label"), b.get("label")): reasons.append("uncertain")
        if a.get("label") and b.get("label") and (a["cut"] != b["cut"] or a["bag"] != b["bag"]): reasons.append("cut/bag tag differs")
        if not reasons: continue
        tags = lambda r: "".join(t for t, k in (("C", "cut"), ("B", "bag"), ("M", "multi"), ("X", "bad")) if r.get(k))
        rows.append(dict(item_id=i, contact_sheet=a.get("sheet") or b.get("sheet") or "", page_url=key.get(i, {}).get("page_url", ""),
                         label_A=a.get("label", ""), other_A=a.get("other", ""), what_A=a.get("what", ""), tags_A=tags(a), note_A=a.get("note", ""),
                         label_B=b.get("label", ""), other_B=b.get("other", ""), what_B=b.get("what", ""), tags_B=tags(b), note_B=b.get("note", ""),
                         reason="; ".join(reasons), final_label="", final_other_produce_name="", final_cut="", final_bag="", adjudicator="", adjudicator_reason=""))
    cols = ["item_id", "contact_sheet", "page_url", "label_A", "other_A", "what_A", "tags_A", "note_A", "label_B", "other_B", "what_B", "tags_B", "note_B",
            "reason", "final_label", "final_other_produce_name", "final_cut", "final_bag", "adjudicator", "adjudicator_reason"]
    with open(os.path.join(args.out, "adjudication_sheet.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    with open(os.path.join(args.out, "disagreements.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols[:14]); w.writeheader(); w.writerows([{k: r[k] for k in cols[:14]} for r in rows])
    with open(os.path.join(args.out, "confusion.csv"), "w", newline="") as f:
        w = csv.writer(f); w.writerow(["A \\ B"] + LABELS)
        for c, r in zip(LABELS, rep["confusion_A_rows_B_cols"] or [[0] * 9] * 9): w.writerow([c] + r)
    rep["n_to_adjudicate"] = len(rows); rep["adjudication_reasons"] = Counter(x for r in rows for x in r["reason"].split("; "))
    json.dump(dict(A=A, B=B), open(os.path.join(args.out, "labels_AB.json"), "w"))
    json.dump(rep, open(os.path.join(args.out, "agreement.json"), "w"), indent=1)
    open(os.path.join(args.out, "agreement.md"), "w").write(agreement_md(rep))
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
        for p in (f"/workspace/work/g9i/cands/img/{k}.jpg", f"/workspace/work/g9j/train/img/{k}.jpg"):
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
    AB = json.load(open(os.path.join(args.agree_dir, "labels_AB.json"))); A, B = AB["A"], AB["B"]
    adj = {}
    if args.adjudicated and os.path.exists(args.adjudicated):
        for r in csv.DictReader(open(args.adjudicated, newline="", encoding="utf-8-sig")):
            fl = (r.get("final_label") or "").strip().lower()
            if fl: adj[r["item_id"]] = dict(label="exclude" if fl == "exclude" else norm_label(fl), other=(r.get("final_other_produce_name") or "").strip(),
                                           cut=r.get("final_cut", ""), bag=r.get("final_bag", ""), who=r.get("adjudicator", ""), why=r.get("adjudicator_reason", ""))
    key = load_key(args.batch); ids = sorted(set(A) | set(B) | set(key)); lic = {}
    for lp in ("j_licence.csv", "j_licence_train.csv"):
        p = os.path.join(OUTD, lp)
        if os.path.exists(p): lic.update({r["key"]: r for r in csv.DictReader(open(p, newline=""))})
    out, cnt = [], Counter()
    for i in ids:
        a, b = A.get(i, {}), B.get(i, {}); k = key.get(i, {})
        same = a.get("label") and a.get("label") == b.get("label") and a["label"] != "uncertain" and a["cut"] == b["cut"] and a["bag"] == b["bag"]
        if same:
            lab, cut, bag, other, status, by = a["label"], a["cut"], a["bag"], a.get("other") or b.get("other") or "", "verified_agree", ""
            if lab == "other_produce" and a.get("other") != b.get("other"): other = a.get("other") if a.get("other") == b.get("other") else (a.get("other") or b.get("other") or "")
        elif i in adj:
            d = adj[i]; lab = d["label"] or "uncertain"
            cut = flag(d["cut"]) if d["cut"] != "" else (a.get("cut", 0) if a.get("label") == lab else b.get("cut", 0))
            bag = flag(d["bag"]) if d["bag"] != "" else (a.get("bag", 0) if a.get("label") == lab else b.get("bag", 0))
            other, status, by = d["other"] or (a.get("other") if a.get("label") == lab else b.get("other", "")) or "", "verified_adjudicated", d["who"]
            if lab in ("uncertain", "exclude"): status = "excluded_by_adjudicator"
        else:
            lab, cut, bag, other, status, by = "", 0, 0, "", "pending_adjudication", ""
        role, c13 = role_of(lab, cut, bag, other) if status.startswith("verified") else ("excluded" if status.startswith("excluded") else "pending", "")
        img = next((p for p in (f"/workspace/work/g9i/cands/img/{k.get('key')}.jpg", f"/workspace/work/g9j/train/img/{k.get('key')}.jpg") if os.path.exists(p)), None) if k else None
        L = lic.get(k.get("key", ""), {})
        out.append(dict(item_id=i, cand_key=k.get("key", ""), batch=args.batch, split=k.get("split", ""), source=k.get("source", ""), uploader=k.get("uploader", ""),
                        status=status, final_label=lab if status.startswith("verified") else "", class13=c13, role=role, cut=cut, bag=bag, other_produce_name=other,
                        label_A=a.get("label", ""), label_B=b.get("label", ""), adjudicator=by, licence=L.get("licence", ""), author=L.get("author", ""),
                        source_url=L.get("source_url", ""), image_sha256=sha256_file(img) if img else ""))
        cnt[status] += 1
    os.makedirs(args.out, exist_ok=True); mp = os.path.join(args.out, f"verified_manifest_{args.batch}.csv")
    with open(mp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
    digest = sha256_file(mp); open(mp + ".sha256", "w").write(f"{digest}  {os.path.basename(mp)}\n")
    ver = [r for r in out if r["status"].startswith("verified")]
    sup = Counter(r["class13"] for r in ver if r["role"] == "supported")
    neg = Counter(r["role"] for r in ver if r["role"] in ("unsupported", "other_class", "printed", "occluded", "cut", "supported_packaged"))
    gates = readiness_counts(args.batch, sup, neg, cnt)
    summ = dict(batch=args.batch, manifest=os.path.basename(mp), sha256=digest, status=cnt, supported_clean_by_class=sup, negatives_by_role=neg,
                n_verified=len(ver), complete=cnt.get("pending_adjudication", 0) == 0, gates=gates)
    json.dump(summ, open(os.path.join(args.out, f"verified_summary_{args.batch}.json"), "w"), indent=1)
    print(json.dumps(summ, indent=1)); return summ

def readiness_counts(batch, sup, neg, cnt):
    """Frozen count gates (G9_stageJ_readiness.md R2 / T1). Packaged supported items and cut items count as negatives (must not be graded)."""
    if batch == "pilot":
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
    a = sp.add_parser("agree"); a.add_argument("a"); a.add_argument("b"); a.add_argument("--batch", required=True, choices=["pilot", "train"])
    a.add_argument("--out", required=True); a.add_argument("--sheets", action="store_true", help="also draw adjudication contact sheets")
    v = sp.add_parser("verify"); v.add_argument("--batch", required=True, choices=["pilot", "train"]); v.add_argument("--agree-dir", required=True)
    v.add_argument("--adjudicated"); v.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    return agree(args) if args.cmd == "agree" else verify(args)

if __name__ == "__main__":
    main()
