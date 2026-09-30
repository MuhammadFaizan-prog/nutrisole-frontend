# NutriSole

A frontend prototype for a food and health assistant, built with React, TypeScript, and shared React Native components. NutriSole brings food capture, portion confirmation, meal planning, glucose records, preferences, and support flows into one mobile interface.

[Editable Figma design](https://www.figma.com/design/UQU8ormOKktMlOTzsZaRko) · [Screen coverage](artifacts/screen-coverage/) · [Design QA](design-qa.md)

![NutriSole reference-screen implementation](artifacts/qa/exact-refinement/six-screen-preview.png)

## Project scope

This repository contains the runnable web frontend, an Expo companion app, individual image/font assets, tests, and the editable Figma importer. Text, forms, navigation, and controls are implemented as components; whole-screen images are used only as reference or QA evidence.

The app is a **frontend demonstration with synthetic data**. Authentication, food recognition, camera capture, health connections, prices, notifications, and staff permissions are simulated. Original demo edits may persist in the current browser; expanded-flow records reset on reload. Deploying the app does not add a backend or synchronize data across users.

## Screens and interactions

The six reference screens remain intact: onboarding, home, scan, log meal, weekly plan, and profile/preferences. Thirty additional concepts and two supporting routes extend the prototype.

| Area | Included views |
| --- | --- |
| Accounts | Sign in, create account, verify email, recover account, reset password |
| Food | Assessment result, market reference, capture retry, food selector, nutrition details, portion confirmation |
| Health | Glucose overview, add reading, reading detail, health connections |
| Planning | Plan generation, activity plan, plan rationale, weekly meal details |
| Foot support | Questionnaire and guidance |
| Personal controls | Assistant, privacy/data rights, reminders |
| Records | Report output, report status, personal history |
| Staff workflows | Catalog queue/review, model release, operations audit, report triage |
| Navigation | Flow directory and screen selector |

Working demo interactions include portion/calorie updates, meal logging and drafts, meal acceptance/substitution, preference editing, manual glucose validation, account form validation, report review, and sample staff evidence gates. The web preview includes iPhone and Pixel device presets, simulated keyboards, and a Reset control.

## Technology

| Layer | Stack |
| --- | --- |
| Web preview | React 19, TypeScript 7, Vite 8, React Native Web |
| Shared app UI | React Native components, semantic scene models, local state |
| Native companion | Expo SDK 57, Expo Router, React Native 0.86 |
| UI assets | Local food/avatar photos, font files, Lucide/vector icons, source artwork |
| Verification | Node test runner, Playwright, TypeScript, runtime integrity checks |
| Design handoff | Native Figma text, components, shapes, variables, and prototype links |
| Web hosting | Vercel static deployment of `dist/client` |

## Run locally

Use Node.js 24 and npm. Install the web dependencies from the repository root:

```sh
npm ci
npm run dev -- --host 0.0.0.0 --port 4173 --strictPort
```

Open `http://localhost:4173/`. Use the screen selector to explore every view, or open `http://localhost:4173/?screen=flow-directory` for the journey directory. The device picker changes the preview preset; Reset restores the demo fixtures.

Build and preview the production web bundle:

```sh
npm run build
npx vite preview --host 0.0.0.0 --port 4175
```

The web build is written to `dist/client`. The existing build also prepares optional Sites worker files under `dist/server` and `dist/.openai`; Vercel serves only `dist/client`.

### Native companion

The Expo app is in `native/` and consumes shared source from `src/nutrisole/`.

```sh
npm --prefix native ci
npm run native:start
```

Use a compatible Expo Go client or a configured simulator. Windows cannot run an iOS simulator. This repository does not include signed app-store binaries.

## Verification

```sh
npm run check:runtime
npm run typecheck
npm test
npm run test:expansion
npm run test:sites
npm run build
```

Optional browser and native checks:

```sh
npx playwright install chromium
npm run test:runtime
npm run native:typecheck
npm run native:lint
npm run native:export
```

The expansion baseline protects 119 original screen/shared-asset files. The runtime lock protects 28 device-preview files. Existing browser evidence covers the 30 added concepts and key interactions; the native app has export checks but has not been verified on a physical device or emulator. Visual fidelity has been refined against the supplied PNGs, but exact pixel identity is not certified.

## Figma design and prototype

[NutriSole — Mobile UI](https://www.figma.com/design/UQU8ormOKktMlOTzsZaRko) contains the original six editable screens and a separate **NutriSole · Expanded flows** page (`34:254`). The live expansion includes 32 primary frames, 53 selection/filled-example states, 80 overlays, and six editable continuation copies for connected journeys.

Live inspection recorded 1,837 native text nodes, 2,254 component instances, and 716 nodes with prototype reactions. All six original frames passed preservation checks, and all inspected navigation destinations exist. The 32 primary frames were exported for visual review, including a refinement of 455 icon instances. Full manual prototype interaction QA remains pending; Figma input examples do not execute frontend validation logic.

The importer and its evidence are in [artifacts/figma-expansion](artifacts/figma-expansion/README.md). Rebuild or check the local package with:

```sh
npm run figma:build
npm run figma:check
```

## Deploy to Vercel

Import this GitHub repository into Vercel and deploy from the repository root. `vercel.json` supplies the build settings:

| Setting | Value |
| --- | --- |
| Framework | Vite |
| Install command | `npm ci` |
| Build command | `npm run build` |
| Output directory | `dist/client` |
| Node.js | 24.x |
| Environment variables | None required for the current frontend demo |

The deployed site uses the same components, fonts, images, and device-preview runtime as the local web app. Query links such as `/?screen=flow-directory` work on the deployment. After connecting the Git repository in Vercel, pushes to the production branch can trigger redeployment.

## Repository layout

```text
src/nutrisole/              Shared original screens and app state
src/nutrisole/extensions/   Added flow scenes, UI, and demo logic
src/mobile/                Protected web device/keyboard runtime
native/                    Expo companion app
public/                    Web-served assets and device artwork
assets/                    Shared source photos, fonts, and icons
scripts/                   Build, integrity, QA, and Figma utilities
tests/                     Domain, expansion, hosting, and browser tests
artifacts/                 Screen audit, comparisons, and design handoff
worker/                    Optional Sites static worker
```

## Development boundaries

Read `AGENTS.md` before changing the app. Preserve the original six screens and protected preview runtime unless an explicit change is requested. Add new flows under `src/nutrisole/extensions/`. Keep generated dependency folders, build outputs, local credentials, and environment files out of Git.

Asset provenance and font/icon license notices are retained alongside their assets. No repository-wide open-source license has been assigned.
