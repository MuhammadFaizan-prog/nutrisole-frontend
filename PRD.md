# NutriSole frontend requirements

Build onboarding, Home, Scan, Log Meal, Weekly Plan, and Profile exactly from the supplied individual images. Users can navigate, confirm portions, save or log meals, accept/substitute plan meals, and edit local preferences. The six PNGs override the poster and preliminary JSON. Default values and copy remain fixed until an interaction changes them.

Acceptance: real text and controls, original separable photos, useful actions, coherent local changes, reset restores fixtures, no hidden screenshot-hotspot implementation, browser comparison evidence for each screen. Exact missing typefaces and photographic originals must be disclosed. Health/history/edit states are inferred and subordinate.

Non-goals (frontend phase, superseded for CV below): authentication, backend, Supabase, real health access, produce prices, clinical advice, deployment. Success is a runnable frontend and an honest visual/functional verification record.


## Phase update — real-time computer vision (October 2026, gauntlet G1 onward)
In scope now, per the FYP proposal "NutriSole: Computer Vision-Based Food and Health Assistant": on-device, offline detection of the 12 v1 produce classes through the phone camera, a quality classifier on the detected crop, explainable measurements (colour band, dark-defect area, shape) and a rule table giving a VISIBLE-condition grade A/B/C/Reject/ungradable with 1-2 reasons and the numbers behind them. The app never claims food safety, disease, chemical status, shelf-life, weight, calories or price from pixels. Backend, prices and glucose sync remain out of scope for this phase. Status and evidence: `docs/cv/DASHBOARD.md`; current scan UI is still the static demo until a model passes the gates (no live camera code is shipped yet).
