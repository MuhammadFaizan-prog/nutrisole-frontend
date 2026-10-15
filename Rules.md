# NutriSole implementation rules

Individual PNGs control default visual states. Preserve text, quantities, image crops, and screen anatomy. Recovered images need provenance. Real components and interaction state are required. No whole screenshot behind invisible controls. Do not invent a new visual direction.

Keep protected mobile runtime files intact; run integrity checks. Implement shared app UI in `src/nutrisole/` and integrate in Prototype. Use platform-specific adapters for genuine native operation. Keep image/photo assets independent from UI text. Record any non-identical typography, generated backdrop, or inferred state in QA. No commits or publishing.


## Glucose monitoring (feature/glucose-monitoring, draft)

Glucose: every input path goes through `validateGlucoseInput`/`reconcileImport`; never convert a value silently or twice; keep the original value and unit; never show "connected" or "saved" unless a real adapter/repository returned it; no sample readings outside the demo flag; no clinical labels (high/low, diagnosis, dosing). Only public Supabase URL + publishable key in clients. New native packages need an RN 0.86.3 New Architecture build test first.
