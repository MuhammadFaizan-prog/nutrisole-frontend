"""G4.5 ripeness output (unripe / ripe / overripe), SEPARATE from fresh/rotten quality and from the A/B/C grade.
EXACT mirror: native/src/cv/pipeline/ripeness.ts (parity: native/tests/cvRipeness.test.ts replays
ml/eval/fixtures/ripeness_parity.json produced by this module).

Rules:
  * Only for classes where ripeness matters to a buyer: banana, mango, tomato, guava (+ citrus colour, opt-in).
  * Abstain (status 'unknown') when the top probability < minConfidence or the margin to the runner-up < minMargin.
  * Never changes the grade: the app shows it as a separate chip until human graders validate a mapping.
  * Classes with no ripeness model get no ripeness field at all (not 'unknown')."""
from __future__ import annotations

STAGES = ["unripe", "ripe", "overripe"]
RIPENESS_CLASSES = ["banana", "mango", "tomato", "guava"]
DEFAULT_RIPENESS = dict(minConfidence=0.6, minMargin=0.15, includeCitrus=False)


def ripeness_from_probs(class_name: str, probs: list[float], params: dict | None = None):
    p = {**DEFAULT_RIPENESS, **(params or {})}
    allowed = RIPENESS_CLASSES + (["citrus"] if p["includeCitrus"] else [])
    if class_name not in allowed:
        return None
    if len(probs) != len(STAGES) or any(not (0.0 <= v <= 1.0) for v in probs):
        return dict(stage="unknown", status="unknown")
    order = sorted(range(len(STAGES)), key=lambda i: (-probs[i], i))
    top, second = probs[order[0]], probs[order[1]]
    if top < p["minConfidence"] or top - second < p["minMargin"]:
        return dict(stage="unknown", status="unknown", confidence=round(top, 4))
    return dict(stage=STAGES[order[0]], status="assessed", confidence=round(top, 4))
