"""G9 Stage A FP error register (ANALYSIS ONLY: all 74 tiles come from VB8-holdout clips; forbidden for training/tuning).
Human verdicts/notes: ml/runs/G8/review/absence/absence_check.csv (Faizi 2026-10-13 23:49 PKT). Where the human left no note,
the category and visual group were assigned by the agent from the absence sheets (basis column says which)."""
import csv, os
R = "/workspace/work/nutrisole"
# tile -> (category, visual_group, agent_note) ; categories: correct | real_produce_wrong_class | out_of_taxonomy_produce |
# unrelated_object | printed_produce | uncertain
A = {
 1: ("correct", "produce (citrus)", ""), 2: ("real_produce_wrong_class", "mango (as apple)", ""), 3: ("correct", "produce (banana)", ""),
 4: ("correct", "produce (capsicum)", ""), 5: ("unrelated_object", "umbrella", "yellow market umbrella"), 6: ("correct", "produce (carrot)", ""),
 7: ("uncertain", "unclear small produce", "small yellowish items in a basin; object type not determinable from tile"),
 8: ("unrelated_object", "equipment/other", "small item on a vehicle roof"),
 9: ("out_of_taxonomy_produce", "oil palm", "agent sees red/spring onions (clip is 'Fresh onion market video'); out-of-taxonomy either way"),
 10: ("uncertain", "unclear", "tiny object on the ground among onion heaps"),
 11: ("out_of_taxonomy_produce", "oil palm", "agent sees red/spring onions; out-of-taxonomy either way"),
 12: ("out_of_taxonomy_produce", "oil palm", "agent sees red/spring onions; out-of-taxonomy either way"),
 13: ("unrelated_object", "clothing", "yellow shirt in a clothing stall"), 14: ("unrelated_object", "bag/luggage", "dark bag on a luggage stall"),
 15: ("out_of_taxonomy_produce", "chili", ""), 16: ("unrelated_object", "clothing", "dark clothing at frame edge (night street)"),
 17: ("out_of_taxonomy_produce", "melon", "round green-yellow fruit on a boat (pomelo/melon-like)"),
 18: ("uncertain", "round green fruit (maybe guava)", ""), 19: ("uncertain", "round green fruit (maybe guava)", ""),
 20: ("unrelated_object", "equipment/other", "orange boat seen from above"), 21: ("unrelated_object", "packaging/printed", "plastic bag held by a shopper"),
 22: ("unrelated_object", "clothing", "headscarf / clothing at frame edge"), 23: ("out_of_taxonomy_produce", "leafy greens", "chopped greens on a tray"),
 24: ("out_of_taxonomy_produce", "leafy greens", "chopped greens on a tray"), 25: ("uncertain", "pod", "green pea/bean pods"),
 26: ("correct", "produce (carrot)", ""), 27: ("out_of_taxonomy_produce", "pod", "pods/beans in hand"), 28: ("uncertain", "pod", "blurry green pod"),
 29: ("unrelated_object", "sack", "sacks on a truck"), 30: ("uncertain", "unclear", "tiny orange item on grass"),
 31: ("unrelated_object", "sign", "on-screen news caption"), 32: ("unrelated_object", "clothing", "yellow shirt in mist"),
 33: ("unrelated_object", "packaging/printed", "printed virus graphic (not produce)"), 34: ("unrelated_object", "equipment/other", "orange object in a crowd"),
 35: ("out_of_taxonomy_produce", "other produce", "green grapes in punnets"), 36: ("correct", "produce (banana)", ""),
 37: ("out_of_taxonomy_produce", "melon", ""), 38: ("unrelated_object", "sign", "map graphic with red hand icon"),
 39: ("unrelated_object", "meat/fish", "raw meat"), 40: ("uncertain", "unclear", "small item in an overhead market shot"),
 41: ("correct", "produce (citrus)", ""), 42: ("uncertain", "unclear", "produce in an overhead market shot, type not determinable"),
 43: ("correct", "produce (lemon_lime)", "human: subtype uncertain"), 44: ("unrelated_object", "meat/fish", "fish cutting scene"),
 45: ("unrelated_object", "meat/fish", "raw fish/meat pieces"), 46: ("unrelated_object", "meat/fish", "red fish/meat"),
 47: ("unrelated_object", "equipment", ""), 48: ("out_of_taxonomy_produce", "leafy greens", "lettuce/cabbage at frame edge"),
 49: ("uncertain", "unclear", ""), 50: ("printed_produce", "packaging/printed", ""), 51: ("unrelated_object", "background/blur", "motion-blurred floor"),
 52: ("unrelated_object", "clothing", "light shirt"), 53: ("unrelated_object", "clothing", "red fabric edge (blur)"),
 54: ("unrelated_object", "equipment/other", "dark object in a food stall"), 55: ("unrelated_object", "sign", "shop sign with characters"),
 56: ("unrelated_object", "person/hand", "hand with utensil"), 57: ("unrelated_object", "sign", "drink-machine display/poster"),
 58: ("unrelated_object", "clothing", "green bag/garment"), 59: ("unrelated_object", "clothing", "green/red fabric item on the ground"),
 60: ("unrelated_object", "clothing", "striped sleeve"), 61: ("unrelated_object", "clothing", "green skirt"),
 62: ("unrelated_object", "background/blur", "grass and legs"), 63: ("unrelated_object", "clothing", "beige clothing"),
 64: ("unrelated_object", "background/blur", "grass and person"), 65: ("unrelated_object", "clothing", "red fabric / hand (blur)"),
 66: ("unrelated_object", "packaging/printed", "sachet with orange print"), 67: ("uncertain", "unclear", ""),
 68: ("out_of_taxonomy_produce", "grain/seed", "bowl of grains/seeds"), 69: ("unrelated_object", "sack", "stacked white/yellow sacks"),
 70: ("unrelated_object", "person/hand", "hand/arm"), 71: ("unrelated_object", "packaging/printed", "plastic food container"),
 72: ("unrelated_object", "background/blur", "paper litter on the floor"), 73: ("unrelated_object", "equipment", "lamp fixture"),
 74: ("unrelated_object", "equipment", "ceiling light"),
}
HUMAN = {"mango not apple": "real_produce_wrong_class", "oil-palm fruit": "out_of_taxonomy_produce", "green chili, not capsicum": "out_of_taxonomy_produce",
         "melon": "out_of_taxonomy_produce", "utensil handle": "unrelated_object", "printed tomato on packaging": "printed_produce"}
rows = []
for r in csv.DictReader(open(f"{R}/ml/runs/G8/review/absence/absence_check.csv")):
    if not r["tile"]: continue
    k = int(r["tile"].split("@")[0]); cat, grp, an = A[k]; note = r["verdict_note"]
    if r["verdict"] == "real": basis = "human verdict real"
    elif note in HUMAN: assert HUMAN[note] == cat, (k, note, cat); basis = "human note"
    elif r["provisional"] == "yes" or "maybe" in note or "?" in note or "unsure" in note: basis = "human note (uncertain/provisional)"; assert cat == "uncertain", k
    else: basis = "human verdict false; category + group by agent from tile (no human type note)"
    rows.append(dict(tile=r["tile"], holdout_n=r["n"], clip=r["clip_id"], split=r["split"], t_s=r["t_s"], claimed_class=r["claimed_class"],
                     score=r["score"], source=r["source"], human_verdict=r["verdict"], human_note=note, provisional=r["provisional"],
                     category=cat, category_basis=basis, visual_group=grp, agent_note=an,
                     use="ANALYSIS ONLY (VB8-holdout); FORBIDDEN for training/tuning/selection"))
os.makedirs(f"{R}/ml/runs/G9/fp", exist_ok=True)
with open(f"{R}/ml/runs/G9/fp/error_register.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
import collections
print(len(rows), collections.Counter(r["category"] for r in rows))
print(collections.Counter(r["visual_group"] for r in rows if r["category"] != "correct").most_common())
print("G3 only:", collections.Counter(r["category"] for r in rows if r["source"] == "G3"))
# ---- after the DEV freeze: would A1's frozen threshold have removed the tile's box? (analysis only; G3 boxes only)
import json
thr = json.load(open(f"{R}/ml/runs/G9/fp/thresholds_A1.json"))["thresholds"]
for r in rows:
    if r["source"] != "G3": r["A1_threshold"] = ""; r["A1_suppresses_box"] = "n/a (OWLv2 proposal, not a G3 box)"; continue
    r["A1_threshold"] = thr[r["claimed_class"]]; r["A1_suppresses_box"] = "yes" if float(r["score"]) < thr[r["claimed_class"]] else "no"
with open(f"{R}/ml/runs/G9/fp/error_register.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
g3 = [r for r in rows if r["source"] == "G3"]
for cat in sorted({r["category"] for r in g3}):
    S = [r for r in g3 if r["category"] == cat]; print("A1 suppression", cat, sum(r["A1_suppresses_box"] == "yes" for r in S), "/", len(S))
