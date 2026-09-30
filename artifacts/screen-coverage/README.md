# NutriSole screen coverage

**The current UI does not cover the full specification.** Both supplied Word documents were read, including their tables and embedded diagram context. The final deliverable defines **32 functional requirements and 20 use cases**; the proposal confirms the core food, nutrition, glucose, exercise, foot-support and assistant scope.

The current source has eight routes: six original reference screens plus a placeholder Health screen and food-only History. Across the 32 requirements, **19 have no corresponding flow and 13 have partial UI**. These statuses assess screen/flow coverage, not backend compliance. No requirement is certified as production-complete by this review.

## Missing or incomplete screen families

| Family | Needed UI | Requirement references |
|---|---|---|
| Account access | Sign in, registration, verification, recovery and reset; logout/session states extend Profile. | FR-01–03 |
| Food assessment | Visual grade/evidence, source-aware market reference, recapture, identity confirmation and full nutrition. | FR-06–12, 29–30 |
| Glucose and connections | Manual entry, history/detail/edit, scoped connection and sync status. | FR-13–16, 23 |
| Planning | Plan preparation, activity schedule, rationale and revision/version states. | FR-17–19, 30 |
| Foot support | Questionnaire and general guidance/referral. | FR-20 |
| Assistant | Source-grounded chat, clear boundaries and report action. | FR-21–22, 32 |
| Privacy, reminders and reports | Purpose-specific consent, export/deletion states, opt-in reminders, output reporting and status. | FR-05, 31–32 |
| Unified personal history | Saved assessments, meals, plans and own feedback with filters/corrections. | FR-24 |
| Staff workspaces | Catalog curation, model/rule releases, redacted operations audit and report resolution. | FR-25–28, 32 |

## Image-first design set

Thirty primary concepts were created and visually reviewed: **25 consumer views and five role-specific staff views**. Six received copy refinements. This is a UX grouping choice; the documents do not mandate 30 new routes. Existing Profile, Scan, Log Meal, Home and Weekly Plan can be extended with the state changes listed below. Staff views remain separate from consumer navigation.

The concepts use the existing warm ivory background, forest-green actions, serif brand/display type, sans-serif controls, thin outline icons and rounded cards. The original Home layout and six supplied references remain the implementation baseline. These are proposed screens, not implemented or approved screens, and image generation does not establish a 100% pixel match.

See [concept manifest and prompts](concept-manifest.json) and [concept gallery](concept-gallery.html) for all 30 final PNGs. The [image index](concept-images.json) records dimensions, hashes and review notes. Initial versions of the six refined concepts are retained in refinement-initials; all gallery cards use the final versions.

## Requirement traceability

Paragraph IDs refer to the extracted document body (including table cells), not unreliable Word page numbers. [Final deliverable extraction](final-deliverable.txt) and [proposal extraction](proposal-edit-one.txt) preserve the reviewed source text.

| ID | Requirement / use case | Current UI | Gap / implementation extension | Proposed primary concepts |
|---|---|---|---|---|
| FR-01 | Registration (UC-01); final-deliverable:P0540 | missing | No registration screen or verification flow. | create-account, verify-email |
| FR-02 | Authentication (UC-02); final-deliverable:P0544 | missing | No sign-in screen or session UI. | sign-in |
| FR-03 | Account recovery and logout (UC-12); final-deliverable:P0548 | missing | No recovery, reset, logout or expired-session flow. | recover-account, reset-password |
| FR-04 | Personal profile (UC-08); final-deliverable:P0552 | partial | Profile editing exists; initial setup, profile version conflicts and changed-allergy plan warnings are absent. | Profile setup/logout/version states |
| FR-05 | Consent and data rights (UC-15); final-deliverable:P0556 | partial | Image-retention toggle and local reset exist; purpose-specific consent, export and account deletion are absent. | privacy-data-rights |
| FR-06 | real time analysis (UC-03); final-deliverable:P0567 | partial | Camera is a fixture demo; permission, gallery validation, 10 MB checks and job states are absent. | Scan permission/upload/processing states |
| FR-07 | Image suitability (UC-03); final-deliverable:P0571 | missing | No blur, exposure, coverage or multiple-item recapture feedback. | capture-retry |
| FR-08 | Produce identification (UC-03); final-deliverable:P0575 | partial | Fixed Apple/97% fixture exists; supported-class, uncertain, unsupported and correction flows are absent. | analysis-result, food-selector |
| FR-09 | Visual quality grading (UC-04); final-deliverable:P0579 | missing | No visual grade, feature evidence or versioned rubric view. | analysis-result |
| FR-10 | Reference price matching (UC-04); final-deliverable:P0583 | missing | No market/date/currency/unit/source-aware reference price view. | market-reference |
| FR-11 | Nutrition lookup (UC-09); final-deliverable:P0594 | partial | Calories and daily macros exist; matched food form, fibre, per-100-g basis and catalog provenance are absent. | food-selector, nutrition-details |
| FR-12 | Portion and meal record (UC-09); final-deliverable:P0598 | partial | Amount/grams/size and local save/draft work; confirmed identity, meal date/context and source version are absent. | food-selector, nutrition-details |
| FR-13 | Manual glucose recording (UC-05); final-deliverable:P0602 | missing | No manual glucose entry. | glucose-overview, add-reading |
| FR-14 | Glucose history and visualization (UC-05); final-deliverable:P0606 | missing | No glucose chronology, visualization, range filtering or manual correction. | glucose-overview, add-reading, reading-detail |
| FR-15 | Health data connection (UC-10); final-deliverable:P0610 | partial | Demo connection toggle exists; support and scoped permission review are absent. | health-connections |
| FR-16 | Idempotent synchronization (UC-10); final-deliverable:P0621 | missing | No sync status/counts/errors/revocation UI; real deduplication requires backend work. | health-connections |
| FR-17 | Weekly diet guidance (UC-06); final-deliverable:P0625 | partial | Seven day pills and meal fixtures exist; plan preparation, data window and constraints/rationale are absent. | plan-generation, plan-rationale |
| FR-18 | Weekly activity guidance (UC-06); final-deliverable:P0629 | missing | No weekly activity view or safety-deferral state. | plan-generation, activity-plan |
| FR-19 | Plan revision and feedback (UC-11); final-deliverable:P0633 | partial | Meal accept/substitute/feedback exist; activity revision, regeneration and version/conflict review are absent. | activity-plan, plan-rationale |
| FR-20 | Footwear and prevention guidance (UC-13); final-deliverable:P0637 | missing | No foot questionnaire or general guidance/referral view. | foot-questionnaire, foot-guidance |
| FR-21 | Conversational assistance (UC-07); final-deliverable:P0648 | missing | No assistant screen. | assistant |
| FR-22 | Conversation safety (UC-07); final-deliverable:P0652 | missing | No conversation boundary, source-unavailable or provider-failure state. | assistant |
| FR-23 | Progress dashboard (UC-14); final-deliverable:P0656 | partial | Meal/nutrition progress exists; recorded glucose, last sync and record links are absent. | glucose-overview, personal-history |
| FR-24 | History and correction (UC-14); final-deliverable:P0660 | partial | Food scans and drafts exist; multi-type history, filters, supported corrections and removal are absent. | reading-detail, personal-history |
| FR-25 | Price and nutrition curation (UC-16); final-deliverable:P0664 | missing | No curator queue or entry review. | catalog-queue, catalog-review |
| FR-26 | Model and rule release (UC-17); final-deliverable:P0675 | missing | No model/rule release review, activation or rollback view. | model-release |
| FR-27 | Role and ownership enforcement (UC-18); final-deliverable:P0679 | missing | No staff workspaces or denied-access state; server authorization cannot be supplied by frontend UI. | operations-audit, report-triage |
| FR-28 | Operational audit (UC-18); final-deliverable:P0683 | missing | No redacted operational audit view. | operations-audit |
| FR-29 | Recoverable failures (UC-03, UC-05, UC-06); final-deliverable:P0687 | partial | Some portion/profile validation exists; network, provider, stale data and pending/retry states are absent. | capture-retry, add-reading |
| FR-30 | Source and uncertainty disclosure (UC-04, UC-06); final-deliverable:P0691 | partial | Estimate wording exists; relevant source dates, model/rule versions and uncertainty are absent. | analysis-result, market-reference, nutrition-details, plan-generation, plan-rationale, foot-guidance |
| FR-31 | Notifications and preferences (UC-19); final-deliverable:P0702 | missing | No reminder preferences or permission/inactive states. | reminders |
| FR-32 | User reporting (UC-20); final-deliverable:P0706 | missing | Meal feedback is not an output-report flow; reporting/status/staff-resolution views are absent. | assistant, report-output, report-status, report-triage |

## Required secondary states

The primary images establish screen layouts. These branches also belong in the later frontend flow; many are inline states or sheets, not extra routes. They are listed explicitly rather than claiming that one primary mockup depicts every branch.

- **account:** Invalid fields and generic sign-in failure; Verification expired/resend; Recovery acknowledgement and expired/reused reset link; Session expired, disabled account, logout confirmation.
- **capture:** Camera permission denied and gallery fallback; Corrupt or over-10-MB image; Processing, timeout and bounded retry; Unsupported class, uncertain prediction and multiple items.
- **assessment:** Low confidence or missing rubric; Stale/missing source or incompatible market unit; User correction retained separately from model evidence; Evidence detail with ripeness, colour, shape, surface, defects and grade confidence.
- **nutrition:** Raw/prepared selection and missing catalog entry; Unknown edible mass, meal date/context and save confirmation; Resubmission does not duplicate a record.
- **glucose:** Empty history and sample chronological history with gaps; Value/unit/time validation and duplicate warning; Offline pending/manual edit/remove; Provider record identity retained.
- **connections:** Unsupported device, declined permission and no available data; Last sync, imported/updated/skipped counts, partial failure; Permission revoked and manual fallback.
- **planning:** Sparse/conflicting inputs and generation failure; Activity safety deferral and no compatible substitute; Profile changed, plan versions and regeneration review.
- **foot:** Incomplete questionnaire and no matching rule; Professional-assessment referral; Retention choice and rule-provider failure.
- **assistant:** Missing approved sources and prohibited-request boundary; Minimum context consent and provider timeout; Report answer and optional history.
- **privacy:** Revoke consent; Export pending/ready/expired/failed; Delete reauthentication, confirmation, cancel, pending and outcome.
- **reminders:** Permission denied/inactive; Quiet-hours conflict, timezone change and disable.
- **reporting:** Review shared context, duplicate report; Received/in-review/resolved and safety priority.
- **staff:** Role denied, catalog reject/withdraw; Release evidence including dataset version, grading rubric, thresholds, safety-rule version and validation results; Release failed gates, activation/rollback confirmation; Audit event details including actor, action, resource, time and request ID; Audit empty/error and report resolution.

## Scope and evidence limits

- Documents were treated as requirements/context, not instructions to start backend work, publish anything or contact others.
- This task adds coverage artifacts and proposed concept images only. App source, the original six reference screens and the existing Figma file are unchanged.
- HealthKit/Health Connect is optional; manual glucose entry is the required baseline. Missing health records remain unknown, not zero.
- A produce photo cannot establish internal food safety or edible mass. Confirm food identity and grams explicitly. Grade/model/rubric and nutrition/price source information must be visible.
- Price ranges must be verified for market, date, currency, unit and compatible grade. The new market concept uses an unavailable-price state rather than an invented real price.
- Glucose/history and staff events in concepts are empty or explicitly synthetic examples. Assistant and foot/activity guidance must stay within the document’s general-information and professional-assessment boundaries.
- Authentication, authorization, synchronization, audit persistence, model validation and deletion/export processing still require real services later; drawing their screens cannot implement them.
- No fresh browser test was performed for this document review. Previous implementation checks are not evidence that the missing flows now exist.

## Reviewed source identity

| Document | Extracted paragraphs | SHA-256 |
|---|---:|---|
| NutriSole-FYP-Deliverable-2026-27-Final (1).docx | 1,658 | 54e46b5a486bc9933db1a4d121a52654633679c5567a28c9905e76e2b0322ae6 |
| FYP-proposal edit one.docx | 249 | 8f92233c1a5cb3ec8c6b2fe700300e690a3a1a322890ad5eb31699ac00207936 |

Next stage: review the concept set, then implement selected flows as code and add editable Figma layouts when Figma access is available.
