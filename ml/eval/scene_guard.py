"""G3 app-side detection guard. EXACT mirror of sceneGuard() in native/src/cv/pipeline/postprocess.ts
(parity: native/tests/cvSceneGuard.test.ts replays ml/eval/fixtures/scene_guard_parity.json made here).

Applied per frame AFTER decode + score threshold + mapping to normalised frame coords, BEFORE the tracker:
  1. drop boxes whose area is < minAreaFrac of the frame (tiny far-away boxes are never gradable);
  2. the app grades ONE item: if more than maxSameClass boxes of one class survive, the frame is a
     scene/pile/texture for that class (stadium seats -> 'tomato' x30) and ALL boxes of that class
     are dropped for this frame. maxSameClass <= 0 disables rule 2.
Order of the surviving detections is preserved.
"""
from __future__ import annotations

import collections

DEFAULT_GUARD = dict(maxSameClass=0, minAreaFrac=0.01)  # G4: rule 2 OFF (0). DEV preferred off in G3; the G4 deterministic TEST replay agrees (G3 yolo11n@480: det segments 0.625 -> 0.667, same FA on both neg clips; ml/runs/G4/gauntlet_ff_*). 0.01 = DEV guard-tune optimum (ml/runs/G3/guard_tune_*)


def scene_guard(dets: list[dict], maxSameClass: int = DEFAULT_GUARD["maxSameClass"], minAreaFrac: float = DEFAULT_GUARD["minAreaFrac"]) -> list[dict]:
    keep = [d for d in dets if (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1]) >= minAreaFrac]
    if maxSameClass <= 0:
        return keep
    n = collections.Counter(d["classId"] for d in keep)
    return [d for d in keep if n[d["classId"]] <= maxSameClass]


def fa_episodes(shown: list[list], fps: float, merge_gap_s: float = 0.5) -> int:
    """Episodes = maximal runs of frames with >=1 displayed box, runs separated by <= merge_gap_s merged.
    One stadium frame that mints 30 tracks counts as ONE episode."""
    eps, last_on, gap_frames = 0, None, int(round(merge_gap_s * fps))
    for i, st in enumerate(shown):
        if st:
            if last_on is None or i - last_on > gap_frames + 1:
                eps += 1
            last_on = i
    return eps


if __name__ == "__main__":  # write the parity fixture
    import json
    import os
    import random
    rnd = random.Random(7)
    cases = []
    for k in range(60):
        dets = []
        for _ in range(rnd.choice([0, 1, 2, 3, 7, 9, 12])):
            x, y = rnd.uniform(0, 0.9), rnd.uniform(0, 0.9)
            w, h = rnd.choice([rnd.uniform(0.01, 0.06), rnd.uniform(0.05, 0.5)]), rnd.uniform(0.01, 0.5)
            dets.append(dict(box=[x, y, min(1.0, x + w), min(1.0, y + h)], classId=rnd.choice([0, 7, 7, 7, 3]), score=round(rnd.uniform(0.35, 0.99), 4)))
        p = dict(maxSameClass=rnd.choice([0, 4, 6, 8]), minAreaFrac=rnd.choice([0.0, 0.002, 0.005, 0.01]))
        cases.append(dict(params=p, dets=dets, expected=scene_guard(dets, **p)))
    shown = [[], [1], [1], [], [], [1], [], [], [], [], [], [], [], [], [1], [1, 2], []]
    out = dict(cases=cases, episodes=dict(shown_flags=[bool(s) for s in shown], fps=10, merge_gap_s=0.5, expected=fa_episodes(shown, 10, 0.5)))
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "scene_guard_parity.json")
    json.dump(out, open(p, "w"), indent=1)
    print("wrote", p, "episodes", out["episodes"]["expected"])
