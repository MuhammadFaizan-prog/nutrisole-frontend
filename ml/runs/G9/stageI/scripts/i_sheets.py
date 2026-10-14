"""I2 review material: numbered contact sheets (5 x 4 tiles, group representatives only) + BLIND annotator CSV (no source label) +
adjudicator key CSV (source metadata, kept apart from annotators). Sheets -> /workspace/work/g9i/sheets/I_sheet_NN.jpg."""
import json, csv, os, random, cv2, numpy as np
O = "/workspace/work/nutrisole/ml/runs/G9/stageI/out"; D = "/workspace/work/g9i/cands"; SH = "/workspace/work/g9i/sheets"; os.makedirs(SH, exist_ok=True)
B = "/workspace/work/nutrisole/ml/runs/G9/stageI"
L = json.load(open(f"{O}/i_leak_split.json"))["items"]; C = json.load(open(f"{D}/cands.json"))
reps = [k for k, v in L.items() if v["group_rep"] == k]; random.seed(19); random.shuffle(reps)  # shuffled: sheets do not reveal source/class blocks
ids = {k: f"I{i + 1:04d}" for i, k in enumerate(reps)}; T = 210
for s in range(0, len(reps), 20):
    can = np.full((4 * (T + 24), 5 * T, 3), 255, np.uint8)
    for j, k in enumerate(reps[s:s + 20]):
        im = cv2.imread(f"{D}/img/{k}.jpg"); h, w = im.shape[:2]; sc = T / max(h, w); im = cv2.resize(im, (max(1, round(w * sc)), max(1, round(h * sc))))
        r, c = divmod(j, 5); y, x = r * (T + 24), c * T; can[y + (T - im.shape[0]) // 2:y + (T - im.shape[0]) // 2 + im.shape[0], x + (T - im.shape[1]) // 2:x + (T - im.shape[1]) // 2 + im.shape[1]] = im
        cv2.putText(can, ids[k], (x + 4, y + T + 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.imwrite(f"{SH}/I_sheet_{s // 20 + 1:02d}.jpg", can, [cv2.IMWRITE_JPEG_QUALITY, 85])
COLS = ["item_id", "sheet", "image_file", "page_url", "licence", "split", "annotator", "class", "unknown_name", "whole_or_cut", "supported", "is_real_produce",
        "printed_or_screen", "packaging", "occluder", "visible_fraction_est", "truncated_by_frame", "overlap_other_produce", "multiple_items", "condition",
        "ripeness", "lighting", "blur", "phone_style_closeup", "confidence", "notes"]
with open(f"{B}/review_annotator_blind.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(COLS)
    for i, k in enumerate(reps):
        v = C[k]; w.writerow([ids[k], f"I_sheet_{i // 20 + 1:02d}.jpg", f"img/{ids[k]}.jpg", v.get("page", ""), v.get("licence", ""), L[k]["split"]] + [""] * (len(COLS) - 6))
with open(f"{B}/review_adjudicator_key.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["item_id", "cand_key", "source", "uploader", "source_label", "source_group", "src_quality", "camera", "phone_exif", "dup_group_size", "ref_dmin", "page_url", "mirror", "query"])
    for k in reps:
        v = C[k]; w.writerow([ids[k], k, v["source"], v.get("uploader", ""), v["label"], v["group"], v.get("src_quality", ""), v.get("camera", ""), L[k]["phone_exif"], L[k]["dup_group_size"], L[k]["ref_dmin"], v.get("page", ""), v.get("mirror", ""), v.get("query", "")])
json.dump(ids, open(f"{O}/review_ids.json", "w"))
print(len(reps), "items,", (len(reps) + 19) // 20, "sheets")
