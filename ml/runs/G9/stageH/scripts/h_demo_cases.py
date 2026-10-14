"""Pick the 4 demo cases from real harness outputs and write out/demo_cases.json for render_h.py.
(1) occluded apple: a CU apple whose occluded crop passed the Stage G checks (H0 graded) - H-final outcome on the same crop;
(2) wrong-ID: a CU-check approach item that Stage G graded on a wrong wide ID - H-final verification result;
(3) unsupported: an eval negative that H0 identified - H-final result; (4) user-confirm fallback on a supported item that H-final could
not verify but whose suggestions include the true class."""
import json, sys, cv2
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.verify import verify_identity, user_confirm, stageh_decision, part_agreement
from ml.eval.occlusion import occlusion_reasons
from ml.eval.closeup import quality_reasons, FROZEN_GATE
B = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"; G = "/workspace/work/nutrisole/ml/runs/G9/stageG/out"
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
NN = N + ["unknown"]
ID = json.load(open(f"{B}/identity.json")); OC = json.load(open(f"{B}/occlusion.json")); E = json.load(open(f"{B}/e2e_h.json")); PV = ID["pick"]; PO = OC["pick"]
OI = [json.loads(l) for l in open(f"{B}/occ_items.jsonl")]; CU = {}
for l in open(f"{B}/occ_cues.jsonl"): CU.update(json.loads(l))
H2 = json.load(open(f"{B}/occ_h2.json")); GR = {"A", "B", "C", "Reject"}
IT = {json.loads(l)["key"] + "|" + json.loads(l)["set"]: json.loads(l) for l in open(f"{B}/ident_items.jsonl")}
cc = json.load(open("/workspace/work/g9g/cu/cands.json")); hc = json.load(open("/workspace/work/g9h/hset/cands.json"))
def q(r): return dict(sidePx=r["side"], blurVar=r["blur"], meanV=r["meanV"], touchesEdge=r["edge"], visibleFrac=r["vis"], maxProb=r["maxP"], margin=r["margin"], blockiness=r["block"])
cases, credits = [], set()
# (1) occluded apple (hand preferred)
best = None
for it in OI:
    if it["cls"] != "apple" or it["split"] != "check": continue
    for s, d in it["sizes"].items():
        for c in ("hand_0", "hand_1", "hand_2", "g_skin50", "neigh50", "bag_side50"):
            r = d.get(c)
            if not r or not (r["grade"] in GR and not quality_reasons(q(r), FROZEN_GATE)): continue
            k = f"{it['id']}_{s}_{c}"; cu = dict(CU[k]); cu["partAgree"] = H2[k]["partAgree"]
            v = verify_identity(dict(status="identified", classId=1), None, H2[k]["probs"], PV)
            occ = occlusion_reasons(cu, PO) if v["status"] == "verified" else []
            dd = stageh_decision(v, occ, "graded", [], True)
            if dd["outcome"] != "graded" and best is None: best = (it, s, c, r, v, occ, dd, k)
if best:
    it, s, c, r, v, occ, dd, k = best; credits.add(f"cu{it['id']}: {cc['cu' + it['id']]['title']} ({cc['cu' + it['id']]['licence']}, {cc['cu' + it['id']]['artist'][:40]})")
    cases.append(dict(title="1. Occluded apple", subtitle=f"CU-check apple cu{it['id']}, {s} px crop, occluder '{c}' (synthetic). Same crop on both sides.",
                      img_h0=f"/workspace/work/g9h/occ/crops/{k}.png", img_h=f"/workspace/work/g9h/occ/crops/{k}.png", h0_bad=True,
                      h0=[f"Apple - grade {r['grade']} shown", "Passed every Stage G check: size, blur, light, visible surface, confidence"],
                      h=["Not graded" if v["status"] == "verified" else "Unable to identify", "Reason: " + ", ".join((occ or [v.get("reason", "")]))[:80], "Category price only"]))
# (2) wrong ID from the Stage G approach
ap = ID["cu_check_approach"].get("with_H_final", {}).get("items", [])
w = [x for x in ap if x["graded_stageG"] and not x["wide_correct"]]
A = json.load(open(f"{G}/e2e_approach.json"))
if w:
    x = next((x for x in w if not x["verified"]), w[0]); r = IT["cu" + x["id"] + "|cu"]; credits.add(f"cu{x['id']}: {cc['cu' + x['id']]['title']} ({cc['cu' + x['id']]['licence']}, {cc['cu' + x['id']]['artist'][:40]})")
    top = max(range(13), key=lambda i: r["h2"][i])
    cases.append(dict(title="2. Wrong identity", subtitle=f"CU-check cu{x['id']} (true: {x['truth']}). Stage G move-closer simulation named it {x['wide']}.",
                      img_h0=r["crop"], img_h=r["crop"], h0_bad=True, h0=[f"{x['wide'].capitalize()} - grade {A[x['id']]['grade']} shown", f"Grade issued on a wrong identity (true: {x['truth']})"],
                      h=["Unable to identify" if not x["verified"] else f"{x['wide']} (verified)", f"Close-up check: {NN[top]} p={r['h2'][top]:.2f}; reason: {x['reason']}", "No grade, no price"]))
# (3) unsupported item H0 identified
neg = [x for x in E["rows"] if x["group"] in ("unsupported", "printed", "cut") and x["wide"]]
if neg:
    x = next((y for y in neg if y["group"] == "unsupported" and not y["verified"]), next((y for y in neg if not y["verified"]), neg[0])); r = IT[x["key"] + "|" + x["set"]]
    t = (hc.get(x["key"]) or cc.get(x["key"]) or {}); credits.add(f"{x['key']}: {t.get('title', '')} ({t.get('licence', '')}, {t.get('artist', '')[:40]})")
    cases.append(dict(title="3. Unsupported item", subtitle=f"{x['key']} ({x['group']}: {t.get('title', '')[5:60]})", img_h0=r["crop"], img_h=r["crop"], h0_bad=True,
                      h0=[f"Identified as {x['wide']}" + (" - graded" if x["h0_graded"] else ""), "Name and category price shown for an item we do not support"],
                      h=["Unable to identify" if not x["verified"] else f"{x['verified']} (verified)", f"Reason: {x['reason']}", "No name, no grade, no price"]))
# (4) user-confirm fallback
sup = [x for x in E["rows"] if x["group"] in ("item", "crowd") and x["truth"] in N and not x["verified"] and x["truth"] in x["suggestions"]]
if sup:
    x = sup[0]; r = IT[x["key"] + "|" + x["set"]]; t = (hc.get(x["key"]) or cc.get(x["key"]) or {}); credits.add(f"{x['key']}: {t.get('title', '')} ({t.get('licence', '')}, {t.get('artist', '')[:40]})")
    sg = " / ".join(s.capitalize() for s in x["suggestions"])
    cases.append(dict(title="4. User-confirm fallback", subtitle=f"{x['key']} (true: {x['truth']}). Not verified automatically ({x['reason']}).", img_h0=r["crop"], img_h=r["crop"], h0_bad=x["wide"] != x["truth"],
                      h0=[(f"{x['wide']} shown" if x["wide"] else "Unable to identify") + (" - graded" if x["h0_graded"] else ""), "No way for the user to help"],
                      h=["Unable to identify -> 'Is this: " + sg + " / something else?'", f"User taps {x['truth'].capitalize()} -> '{x['truth'].capitalize()} (confirmed by you)'", "Category reference price only; quality not checked; not counted as accuracy"]))
json.dump(dict(cases=cases, credits=sorted(credits)), open(f"{B}/demo_cases.json", "w"), indent=1)
print(len(cases), [c["title"] for c in cases])
