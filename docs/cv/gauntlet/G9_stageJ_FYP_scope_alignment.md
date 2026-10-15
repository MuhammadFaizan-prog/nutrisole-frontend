# Stage J alignment with the NutriSole FYP proposal

Checked on **2026-10-15** against the user-supplied **FYP-proposal edit one.docx**, titled *NutriSole: Computer Vision-Based Food and Health Assistant*.
The source file's SHA256 is `c76c8a6eafab613cad1fb0e1d667eb06eae9348f8535e7378a7c7295c0aa5438`.
The main document text, including tables, and methodology figures 7.1–7.3 were inspected. The proposal itself was not edited.

The proposal defines the full product scope. Existing G9 protocols supply the current experimental checks and readiness floors;
their image counts and two-person annotation process are implementation decisions, not extra claims about what the proposal prescribes.
This document maps requirements and limits. It does not certify that every product module is implemented or accepted.

## Requirement traceability

| Proposal requirement and location | Required NutriSole behaviour | Meaning for the current Stage J work |
|---|---|---|
| Supported fruit/vegetable recognition; section 4 objective 1, 6.1 Food Recognition & Nutrition | Identify items from a defined library and report uncertainty for unsupported or unclear inputs. | Apple, banana, orange-type citrus, tomato and carrot are the current showcase subset. Preserve existing broader class mappings and artifacts. Section 6.2 expressly excludes recognising every food. |
| Visible ripeness, defects, colour, shape and surface condition; section 4 objective 2, introduction, figure 7.3 | Assess visible condition after identity is sufficiently established. | These identity/visibility labels support later condition assessment. They are not ripeness ground truth, laboratory tests, or completed defect validation. Preserve the existing condition models. |
| Understandable quality grade; section 4 objective 3, figure 7.2 | Eventually explain a grade from validated identity and visible condition. | Keep the grading engine and interfaces. Current failed experimental gates still block user-facing automatic A/B/C grades. The illustrative proposal image is a target concept, not evidence that model acceptance has passed. |
| Grade plus verified market-price data; section 4 objective 4, introduction, figures 7.1 and 7.3 | Give a sourced reference price range using appropriate produce identity, units and available validated quality information. | Preserve pricing integration and provenance. A photo alone does not verify current market prices or exact weight. Keep grade-specific pricing unavailable when the grade is not reliable. Any weight input must be explicit/user-provided or from a supported source. |
| Food recognition linked to nutrition and portions; section 6.1, introduction, figure 7.1 | Retrieve/display nutrition for the identified supported food, with portion assumptions stated. | Keep nutrition mappings, portion handling and backend contracts. Recognition labels alone do not establish nutrient quantity, exact mass or clinical suitability. |
| Manual or supported API/device glucose records, history and visualization; section 4 objective 5, 6.1 and 6.3 | Accept available user records and supported integrations, clearly identifying data source and availability. | Preserve glucose workflows and records. Manual entry is explicitly allowed; the architecture diagram does not require custom glucose hardware or direct device control. No device integration is claimed tested by this dataset task. |
| Personalized weekly diet and exercise guidance; section 4 objective 6, 6.1, figure 7.3 | Use available nutrition, glucose, preferences and mobility/foot information to support weekly planning. | Keep planning modules and their data flow. CV preparation is one input to this feature, not a replacement for it or evidence of clinical outcomes. |
| Basic footwear and injury-prevention support; section 4 objective 7, 6.1 | Provide defined-rule guidance within the project's information boundaries. | Preserve this module. The name NutriSole does not imply building smart shoes, pressure sensors or diagnosing foot disease; these are excluded in 6.2. |
| Conversational assistant; section 4 objective 8, 6.1, introduction | Support food, lifestyle and diabetes-related information within stated boundaries. | Preserve the assistant and system context. Diagnosis, prescriptions, insulin dosing and medical-equipment control stay outside scope under 6.2. |
| User management, feedback, progress, uncertainty and data protection; section 4 objective 9, 6.1 and problem description | Maintain profiles/history and distinguish reliable, missing, unsupported and uncertain data. | Preserve user modules and APIs. Keep AI-assisted, human-verified and pending results separate. Consent/session records and location checks support data handling; filenames do not prove labels or ownership. |
| Modular mobile/backend/data integration; section 7 figures 7.1/7.3, section 8 | React Native mobile flows connect CV, backend, database, nutrition, pricing, health records and planning. | Preserve current interfaces and integrations. This follow-up adds dataset documentation, not an architecture migration. Final acceptance still needs end-to-end and physical-camera evidence; pytest counts alone do not prove the full mobile system. |

## Why the phone collection fits

The proposal's methodology explicitly includes dataset development, training/validation/testing and image augmentation, followed by
CV, grading and system validation. Team phone images address the documented mismatch between available training imagery and actual
smartphone captures. They provide separate train and evaluation candidates without redefining the product.

The [revised shot list](G9_stageJ_team_photo_shotlist.md) requests an initial **80 evaluation candidates** and **70 whole-apple training
candidates**. The first set tests packaging and visibility handling; it must never be reused to improve the model through training.
Photographers/sessions/fruit instances remain separated. The training set is checked against actual clean-whole verified needs before
calling any shortage closed. Optional cut/damaged examples do not replace the clean-whole floor.

The original annotation guide remains authoritative: clear packaging normally adds B; an established real main item with **less than
about half visible** can receive `occluded`; mostly visible items keep their produce label if identifiable. The revised hidden-shot list
therefore separates majority-hidden cases from mostly-visible controls. A filename saying `hid-*` never determines a human answer.

## Current evidence and pending work

- Existing separate AI reviews cover 265 + 335 = **600 pilot images**. They remain `AI_ASSISTED_NOT_HUMAN`; no independent human
  exports, kappa, adjudication or human-verified images are invented. H3 remains **BLOCKED**.
- The remote `cv-gauntlet` checkpoint **017c9a5** was inspected and fast-forwarded locally. It adds the phone ingestion stub, six
  synthetic tests, the initial shot list and a separate retry record. The complete **117-test ML suite** and the **28-file runtime
  integrity check** reproduce locally. These checks do not establish label correctness, product completion or device performance.
- The other agent's retry record reports P729, P756 and P773 retrieved with original hashes and matching pHashes. Original pixels were
  not supplied in that commit and were not re-viewed for this scope check. Earlier failed-request and AI-review records remain historical.
- The ingestion stub is preparatory: full earlier-reference/source checks, blinded pack integration, genuine independent labels and
  third-person adjudication still need completion before those new photographs can satisfy readiness gates.
- Apple is the largest projected training gap, but banana, citrus and tomato also have smaller projected deficits. Actual verified
  counts, class/source coverage and every frozen prerequisite decide readiness; a fixed number of submitted camera files does not.
- Recognition recovery is the current subtask. Full FYP delivery still requires evidence for visible-condition assessment, understandable
  grading, sourced reference pricing, nutrition/portions, glucose history, weekly plans, footwear guidance, assistant boundaries and
  connected user workflows, without representing pending functions or mock data as completed integrations.

## Instruction for the development agent

Continue Stage J within the proposal's dataset-development and testing scope. Use the revised phone shot list and unchanged annotation
guide, preserve all G1–G9 work and all NutriSole modules, and keep train/eval sources separate. Treat collected photos as candidates until
permission, identity, grouping and human verification are complete. Preserve the original independent agreement score and adjudication
history. Do not narrow the final product to classification, manufacture unsupported medical/hardware scope, weaken frozen gates, launch
H3/GPU work, enable unvalidated grades, merge to main or deploy. Report each FYP requirement as verified, partial, pending or blocked
with the evidence needed for its actual user workflow.
