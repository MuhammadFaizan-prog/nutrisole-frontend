# NutriSole frontend implementation plan

Goal: implement the six supplied screens as interactive React Native UI, with a protected Product Design mobile preview and an Expo native entry.

Architecture: shared UI and domain state in `src/nutrisole/`; web/native primitive, icon, asset, and persistence adapters. `Prototype.tsx` mounts shared UI inside the existing mobile runtime. `native/` runs the same screens through Expo. No server integration.

- [x] Inspect reference images, prior prompt, context notes, JSON, and runtime contract.
- [x] Bootstrap Product Design mobile preview; scaffold Expo app separately.
- [x] Recover original photo crops and texture assets; document generated recovery behind camera exclusions.
- [x] Write and run focused failing domain tests for validated portions, consumed versus saved records, and idempotent submissions.
- [x] Implement domain model, synthetic local persistence, six default states, history, and back navigation.
- [x] Implement all six measured screens with source photos and interactive text/controls; record fidelity limits.
- [x] Wire secondary sheets through platform adapters, preserving preview keyboard/sheet behavior.
- [x] Run runtime integrity, TypeScript, domain tests, web build, native lint, and native export.
- [x] Verify flows and console in the in-app browser; capture six reference states.
- [x] Compare registered source/capture pairs and focused regions, refine actionable mismatches, record remaining P2 findings in design QA.
- [x] Leave preview running, update tracker and exact run/reset instructions.

Exact-image acceptance remains blocked by the residual findings in `design-qa.md`; completion above describes implemented and checked work, not literal pixel equivalence. Native device behavior/appearance remains unverified.

Check commands from app root: `npm run check:runtime`, `npm run typecheck`, `npm test`, `npm run build`, `npm run native:typecheck`, `npm run native:lint`, `npm run native:export`.

Recovery: source documents and PNGs remain untouched; recovered assets retain provenance. Reset clears only the synthetic local app namespace. No git commit, deployment, or external user-data transmission is requested.
