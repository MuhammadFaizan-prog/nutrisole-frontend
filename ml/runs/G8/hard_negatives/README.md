# G8 hard-negative list for G9 (DEV-ONLY, FORBIDDEN FOR TRAINING)

`g9_hard_negative_list.csv`: the 66 absence-check tiles the user (Faizi, 2026-10-13 23:49 PKT) marked **false** (a G3 or OWLv2 box
on something that is not the claimed supported class). Columns: tile id on `ml/runs/G8/review/absence/absence_sheet_*.jpg`, clip,
holdout number, split, clip status in `clip_level_truth.csv`, time, claimed class, score, proposing detector, reviewer note.

Object types the reviewer named across these tiles: clothing, umbrellas, signs, printed produce images, packaging (incl. a printed
tomato), sacks, equipment / utensil handle, oil-palm fruit, melons, green chilies, mango called apple, pod / plantain called banana.
Most tiles have no per-tile type note; only noted types are recorded per row. Nothing was inferred.

**Status: FORBIDDEN for any training, fine-tuning, threshold tuning or model selection** while their source clips stay in
VB8-holdout (all 66 come from `holdout (LOCKED)`, `holdout_v7_pending` or `negatives_v7` clips). Allowed use in G9: error
analysis and to design a *different*, dev-only mining pass (find similar objects in VB8-dev / train-only clips and in new
licensed footage). If a later gauntlet retires these clips from the holdout, that must be a dated prereg decision made before
any model is trained on them, and a new independent holdout must replace them first.

Breakdown by claimed class: apple 16, banana 12, potato 7, mango 6, citrus 5, carrot 5, tomato 5, lemon_lime 4, capsicum 2,
cucumber 2, pomegranate 2. By clip status: 42 from reviewed negatives, 12 from verified-positive clips (wrong-object boxes in
produce scenes), 12 from clips whose review is pending (#9, #23, #31).
