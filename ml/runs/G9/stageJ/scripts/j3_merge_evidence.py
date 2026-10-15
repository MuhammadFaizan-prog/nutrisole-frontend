"""G9 Stage J3: merge the two per-annotator attestation files into the combined evidence JSON that j_agree.py agree --evidence expects.

Each annotator fills attestation_annotatorN.json THEMSELVES (never generated on their behalf):
  {"schema_version":1,"provenance":"HUMAN_INDEPENDENT","copy":"annotator1","name":"<real name>","batches":{"pilot":"<csv file name>", ...},
   "independently_labelled":true,"no_ai_or_peer_labels_seen":true,"attested_at":"2026-10-20T18:00:00+05:00"}
The lead runs:  j3_merge_evidence.py --batch pilot --a attestation_annotator1.json --a-csv A.csv --b attestation_annotator2.json --b-csv B.csv --out evidence_pilot.json
The CSV sha256 is computed here from the exact exported bytes and bound into the evidence; nothing is filled in for a person.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import j_annotation as V


def merge(batch, att_a, csv_a, att_b, csv_b):
    out = dict(schema_version=1, provenance="HUMAN_INDEPENDENT", batch=batch, annotators=[])
    for att, csvp, copy in ((att_a, csv_a, "annotator1"), (att_b, csv_b, "annotator2")):
        a = json.loads(Path(att).read_text(encoding="utf-8-sig")) if not isinstance(att, dict) else att
        if a.get("schema_version") != 1 or a.get("provenance") != "HUMAN_INDEPENDENT": raise ValueError(f"{copy}: invalid attestation header")
        if a.get("copy") != copy: raise ValueError(f"{copy}: attestation is for copy {a.get('copy')!r}")
        name = str(a.get("name", "")).strip()
        if not name or V.NONHUMAN.search(name): raise ValueError(f"{copy}: a real human name is required")
        if batch not in (a.get("batches") or {}): raise ValueError(f"{copy}: attestation does not cover batch {batch}")
        if Path(csvp).name != a["batches"][batch]: raise ValueError(f"{copy}: CSV file name differs from the one the annotator attested")
        if a.get("independently_labelled") is not True or a.get("no_ai_or_peer_labels_seen") is not True:
            raise ValueError(f"{copy}: independence / no-AI attestations must be true, set by the annotator")
        V.iso_time(a.get("attested_at", ""))
        out["annotators"].append(dict(name=name, copy=copy, csv_sha256=V.digest(csvp), independently_labelled=True,
                                      no_ai_or_peer_labels_seen=True, attested_at=a["attested_at"]))
    if out["annotators"][0]["name"].casefold() == out["annotators"][1]["name"].casefold(): raise ValueError("two distinct annotators required")
    return out


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("batch", "a", "a-csv", "b", "b-csv", "out"): p.add_argument("--" + k, required=True)
    x = p.parse_args()
    ev = merge(x.batch, x.a, x.a_csv, x.b, x.b_csv)
    Path(x.out).write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8"); print(json.dumps(ev, indent=1))
