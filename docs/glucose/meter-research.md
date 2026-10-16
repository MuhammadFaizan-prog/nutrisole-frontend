<!-- Imported from the parallel meter research (Hark project files/glucose/meter_research.md, prepared 2026-10-16). Research evidence only: no hardware was bought or tested, and nothing here is implemented code. Prices change; re-verify before any purchase. -->

# NutriSole — Finger-prick (SMBG) Meter Research Matrix (Master Prompt §4)

- **Scope:** affordable test-strip glucose meters sold in Pakistan; import routes A–E (manual, direct BLE, Health Connect, HealthKit, vendor API/CSV/USB).
- **Prepared:** 2026-10-16 (Asia/Karachi). Location assumed: Lahore, Pakistan. Retailer prices were read in October 2026 (most on 2026-10-16; some earlier in this same research task: Dawa, D. Watson, Marham, Divine, Hamza, Nova, Sehat, Roche PK, Ascensia PK, OneTouch, mySugr Apple Health pages). Prices change often; confirm at checkout.
- **Status:** research only. No code was changed, nothing was bought, and no hardware was tested. Every "works" claim below is documentary. **A real hardware test is still mandatory before any auto-sync claim.**
- **Labels:** **SUPPORTED** = official manufacturer or platform documentation says so · **REQUIRES HARDWARE TEST** = strong evidence (standards certification or a working open-source implementation) but no official third-party guarantee and not tested by us · **UNVERIFIED** = no source found either way · **UNSUPPORTED** = the source says no, or the hardware has no such capability.
- CGM products (Sinocare iCan i3/Linx, FreeStyle Libre, Accu-Chek SmartGuide) appear in Pakistani shops but are **out of scope** (CGM ≠ SMBG) and are excluded on purpose.

---

## 0. TL;DR for the implementation agent

1. **Manual entry (Route A) is the only path that works for every meter on this list.** Build it first. It is the complete answer for Sinocare, On Call, Accu-Chek Instant S and Contour Plus/TS, none of which have BLE.
2. **Direct BLE (Route B) via the standard Bluetooth Glucose Service 0x1808 is the most realistic auto-import path for a Pakistan-available meter.** Best candidate: **Accu-Chek Instant (the Bluetooth model, not "Instant S")**. Roche says it uses BLE passkey pairing. Open-source xDrip+ reads it over 0x1808 with RACP since the 2025-05-23 nightly. Known quirks: it does **not** send Glucose Measurement Context (0x2A34), and it has a **vendor-private decoy characteristic that reuses the RACP UUID 0x2A52**, so look up characteristics *within* service 0x1808. Label: REQUIRES HARDWARE TEST.
3. **Health Connect (Route C) is a platform-ready but source-poor route in Pakistan.** The API is solid (BloodGlucoseRecord, `android.permission.health.READ_BLOOD_GLUCOSE`). The only manufacturer app with **official** documentation that it writes finger-prick glucose to Health Connect is **OneTouch Reveal** (LifeScan). OneTouch meters only reach Pakistan as grey imports. **mySugr (Roche) documents Apple Health and Google Fit, not Health Connect.** Contour documents Apple Health only. Build the HC reader generically and test it with synthetic data. Do not claim a real meter→HC chain works.
4. **HealthKit (Route D):** OneTouch Reveal, mySugr and Contour Diabetes all document writing blood glucose to Apple Health. That is an iOS-later path.
5. **Vendor API (Route E):** no public SMBG cloud API was found for any of these vendors. OneTouch Reveal can export a **CSV** (documented). Roche/Ascensia/ACON/LifeScan meters use **USB/serial PC software**, which is not useful for a phone app. → UNSUPPORTED as an app integration; CSV import is a possible fallback only with a real sample file.

---

## 1. Summary matrix (Pakistan-available models)

| # | Exact model | PK device price (retailer, 2026-10-16) | Strip (exact) · PKR per pack · ≈ cost/test | Connectivity | Direct BLE (0x1808) | Health Connect chain | HealthKit chain | Vendor API / export | Overall confidence |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **Accu-Chek Instant** (Roche, Bluetooth model, model no. 973 per BLE Device Info) | Rs 4,340.30 sale / 5,293 list (Dawa Healthcare); Rs 4,752 (Dawaai, listed, add-to-cart) | Accu-Chek Instant strips · 50 = Rs 2,011.20 (Dawa) · **≈ Rs 40.2/test**; 100 = Rs 3,950 (Hamza Surgical) ≈ Rs 39.5/test; 10 = Rs 475 (Dawaai, sold out) | BLE + micro-USB | **REQUIRES HARDWARE TEST** (standard GLS with passkey; xDrip works since 2025-05-23; quirks) | **UNSUPPORTED/UNVERIFIED**: mySugr documents Google Fit, not HC | **SUPPORTED** via mySugr → Apple Health | **UNSUPPORTED** for apps (USB → Roche Care Platform/Smart Pix PC software only) | Medium-high |
| 2 | **Accu-Chek Instant S** (Roche, no BT) | Rs 2,825 (Sehat/Ailaaj); Rs 3,078.20 sale (Dawa); Rs 3,621 (D. Watson) | Same Accu-Chek Instant strips · **≈ Rs 40.2/test** | micro-USB only | **UNSUPPORTED** (no radio) | UNSUPPORTED | UNSUPPORTED | USB → PC software only | High |
| 3 | **Accu-Chek Guide** (Roche, APAC kit, BT) | Rs 4,275 (Dawaai, **sold out**) | Accu-Chek Guide strips · 50 = Rs 2,403 (Dawaai, in stock) · **≈ Rs 48.1/test** | BLE + micro-USB | **REQUIRES HARDWARE TEST** (Roche: Continua-certified, passkey; xDrip README lists it) | UNSUPPORTED/UNVERIFIED (mySugr) | SUPPORTED via mySugr | USB → PC only | Medium (stock risk) |
| 4 | **Sinocare Safe AQ Voice** ("Safe AQ Glucometer with Voice & Light") | Rs 1,599 (sinocare.pk, official distributor); price list Rs 2,499 | Sinocare Safe AQ (& UG) strips · 50 = Rs 1,600 (vial) / Rs 1,700 (foil) · **≈ Rs 32/test**; lancets 25 = Rs 80 | **None** (stores only 10 results) | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | None | High |
| 5 | **ACON On Call EZ II** (uses On Call Plus strips) | Rs 2,350 (My Vitamin Store, in stock) | On Call Plus strips · 50 = Rs 1,327 (My Vitamin Store) · **≈ Rs 26.5/test**; code chip per box | None wireless; data port (cable optional) on the sister On Call Plus meter. EZ II port **UNVERIFIED** | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | Serial/USB cable + On Call PC software (On Call Plus manual) | Medium |
| 5b | **ACON On Call Plus** (meter kit) | Rs 1,412 (Sehat/Ailaaj listing) | Same On Call Plus strips · **≈ Rs 26.5/test** | Data port + optional PC cable | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | PC software via cable | Medium |
| 6 | **Contour Plus** (Ascensia, non-BT) / **Contour TS** | Contour Plus Rs 3,722 (Dawaai, sold out); Contour TS Rs 2,755 (Dawaai, add-to-cart) / Rs 2,900 (Sehat) | Contour Plus strips 50 = Rs 2,755 (Dawaai, sold out) · ≈ Rs 55/test; Contour TS strips 50 = Rs 2,090 (Dawaai, sold out) · ≈ Rs 41.8/test | None wireless (cable port per Roche connectivity list) | UNSUPPORTED | UNSUPPORTED | UNSUPPORTED | PC cable only | Medium |

**Not confirmed as sold in Pakistan (kept for reference, excluded from the "≥5 PK models" count):**

| Model | PK status | Software status |
|---|---|---|
| **Contour Plus One** (BT) | **Not in Ascensia Pakistan's lineup** (diabetes.ascensia.pk lists only Contour PLUS and Contour TS meters). Sold in Bangladesh (Square Pharma), Nepal, Egypt. No PK retailer listing found. | BLE GLS 0x1808, read by xDrip (REQUIRES HARDWARE TEST); Contour Diabetes app → Apple Health SUPPORTED; → Health Connect UNVERIFIED (Sahha says iOS only) |
| **OneTouch Verio Flex / Verio Reflect** (LifeScan, BT) | **Grey import only** (Shoppingbag/StarShop/Medical Hut/Ubuy, "not confirmed" pricing). No official PK distributor found. Verio strips via importers ≈ Rs 12,500–14,000 per 50 (search excerpts, not fetched) → ≈ Rs 250+/test. | **Best documented**: OneTouch Reveal Android → **Health Connect SUPPORTED (official)**, iOS → Apple Health SUPPORTED, CSV export SUPPORTED. BLE is proprietary (not 0x1808) per OneTouch docs: **UNVERIFIED**/treat as proprietary. |
| **Sinocare Safe AQ Air** (BT) | Sold in EU/global stores; **not on sinocare.pk** (official PK distributor). | Pairs with the MedM Health app → Apple Health / Google health per MedM: UNVERIFIED for Health Connect specifically. |

---

## 2. Per-meter detail

### 2.1 Accu-Chek Instant (Roche Diabetes Care), Bluetooth model
- **Exact model:** Accu-Chek Instant (mg/dL PK version). BLE Device Information reports Manufacturer "Roche", Model Number "973" ([StackOverflow capture](https://stackoverflow.com/questions/70025172/accu-chek-bluetooth-connection-identification), search excerpt, community). Firmware is not published.
- **Manufacturer sources:** Roche Pakistan product page, which lists "Connects via Bluetooth to the mySugr app", BLE 2.402–2.480 GHz, micro-B USB, ≥720 results, auto-coding, 2×CR2032: <https://www.accu-chek.com.pk/products/meters/instant> · PK manuals: <https://www.accu-chek.com.pk/support/instant#user-downloads-section> · Roche UK FAQ ("implements BLE Pass Key Pairing security"; BLE to mySugr; micro-USB to the RocheDiabetes Care Platform; app must be open to transfer): <https://www.accu-chek.co.uk/support/instant/faq> · Roche connectivity table (Instant = USB, Bluetooth; Instant S = USB): <https://diabetes.roche.com/sites/g/files/papvje141/files/2023-08/RDCP_Connectivity_Guide.pdf>
- **PK price (Oct 2026):** Dawa Healthcare (Karachi) Rs 4,340.30 sale, Rs 5,293 list (page text also says Rs 4,234.40 "as of 23 September 2026"); also Divine Medicines Rs 3,470, Hamza Surgical Rs 3,999, Marham Rs 4,499, Nova Health Rs 4,763.70, D. Watson Rs 5,293: <https://dawahealthcare.biz/products/accu-chek-meter-instant> · Dawaai Rs 4,752 (list Rs 5,003): <https://dawaai.pk/brands/accu-chek-1457> · Roche PK "where to buy" points to Digimall: <https://www.digimall.pk/collections/rochelist>
- **Strips:** Accu-Chek Instant test strips (shared with Instant S). 50 = Rs 2,011.20 at Dawa ([link](https://dawahealthcare.biz/products/accu-chek-meter-instant)) → **≈ Rs 40.2/test**; 100 (Instant/Instant S strips) = Rs 3,950 at Hamza Surgical → ≈ Rs 39.5/test; 25 = Rs 1,330 at Divine Medicines (≈ Rs 53.2/test). DVAGO 25 = Rs 1,249 appears in a search excerpt only (UNVERIFIED).
- **Lancets/calibration:** Softclix lancing device and lancets; **no coding/calibration** (auto-coding).
- **Connection:** BLE (passkey pairing; Dawa says "one device at a time") + micro-USB.
- **BLE status: REQUIRES HARDWARE TEST.** Evidence: (a) Roche officially states BLE passkey security; (b) xDrip+ discussion #2997 shows Instant pairs but timed out waiting for the optional Glucose Measurement Context. PR #4000 fixed this and maintainers say it works "as of the 2025.05.23 Nightly" ([discussion](https://github.com/NightscoutFoundation/xDrip/discussions/2997)); (c) 2026-09-29 HCI-snoop report in the same thread: the meter exposes **a second vendor-private GATT service (`00000000-0000-1000-1000-000000000000`) containing a characteristic that reuses RACP UUID 0x2A52**. Writing to it returns ATT error 0x81 and the meter disconnects. **Always resolve characteristics via `getService(0x1808).getCharacteristic(0x2A52)`.** Some users in late 2025 still reported "pairs, no data". This is not an encrypted/proprietary blocker; it is a standard GLS with quirks.
- **Health Connect: UNSUPPORTED / UNVERIFIED.** mySugr's current Play listing names "Google Fit®" and Accu-Chek Guide/Guide Me/ReliOn as integrations, not Health Connect ([Play](https://play.google.com/store/apps/details?id=com.mysugr.android.companion&hl=en), updated 2026-09-24). The Play listing's meter list varies by country: the IN/ZA listings in search excerpts include Accu-Chek Instant. Google Fit APIs are supported only "until the end of 2026" ([Android Developers](https://developer.android.com/health-and-fitness/guides/health-connect/plan/data-types)). No Roche/mySugr page found saying mySugr writes to Health Connect.
- **HealthKit: SUPPORTED** (mySugr ↔ Apple Health, with blood glucose among the shareable data): <https://www.mysugr.com/support/en/what-apple-health-and-what-are-its-benefits> · <https://www.mysugr.com/support/en/can-i-import-and-export-data>
- **Vendor API/export:** no public API found. mySugr PRO offers PDF/Excel reports (Play listing). USB goes only to Roche PC/cloud tools. → **UNSUPPORTED** as an app integration.
- **OS:** mySugr needs Android 9+ / iOS 16.2+ for meter sync per ADCES DanaTech (search excerpt, UNVERIFIED). A NutriSole direct-BLE client needs Android BLE permissions (`BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT` on Android 12+).
- **Local support:** Roche Diabetes Care Pakistan site with support/warranty pages; strips widely stocked (Dawaai, Dawa, D. Watson, DVAGO).
- **Risks:** pairing NutriSole may unpair mySugr (single bond); the decoy-RACP quirk; no Context characteristic (meal flags won't arrive over BLE, so ask the user); firmware variance; Roche gives no third-party support. **Do not confuse with Instant S.**

### 2.2 Accu-Chek Instant S
- No Bluetooth. Roche connectivity table: Instant S = USB only ([PDF](https://diabetes.roche.com/sites/g/files/papvje141/files/2023-08/RDCP_Connectivity_Guide.pdf)). Roche PK page: <https://www.accu-chek.com.pk/products/meters/instant-s>
- **PK price:** Sehat/Ailaaj Rs 2,825 ([category](https://sehat.com.pk/categories/Over-The-Counter-Drugs/Blood-glucose-control-/Glucometers/); note Sehat is redirecting to Ailaaj); Dawa Rs 3,078.20 sale; D. Watson Rs 3,621 (search excerpt).
- **Strips:** same Instant strips, ≈ Rs 40.2/test. **Routes B/C/D/E: UNSUPPORTED.** Manual entry only. A good **manual-demo** meter if the user later upgrades to the BT Instant on the same strips.

### 2.3 Accu-Chek Guide (APAC kit)
- **Sources:** Roche India FAQ (official): "Accu-Chek Guide meter certifying against the Continua 2014 Design Guidelines… use Passkey pairing… send BG/CG results under the same formats as described in the standards": <https://www.accu-chek.in/faq/connectivity> · Roche connectivity table (USB, Bluetooth). xDrip README lists "AccuChek Guide" among supported BT meters: <https://github.com/NightscoutFoundation/xDrip/blob/master/README.md>
- **PK price:** Dawaai kit Rs 4,275 (**sold out**); strips 50 Rs 2,403 (in stock): <https://dawaai.pk/brands/accu-chek-1457> → ≈ Rs 48.1/test. (D. Watson/Naheed list Guide strips at Rs 3,400 per search excerpts.)
- **BLE: REQUIRES HARDWARE TEST** (strongest *official* standards claim of the PK set). **HC:** same as mySugr (UNSUPPORTED/UNVERIFIED). **HealthKit:** SUPPORTED via mySugr. **Risk:** meter stock in Pakistan.

### 2.4 Sinocare Safe AQ Voice
- **Source / PK price:** official PK distributor sinocare.pk, product page: model "Safe AQ Voice", 0.6 µL, 10 s, **memory: 10 results**, voice prompts, mg/dL, Rs 1,599 (list Rs 2,500): <https://sinocare.pk/product/sinocare-safe-aq-blood-glucometer-with-voice-light-feature/> · price list (Safe AQ Glucometer Rs 2,499; strips 50 Rs 1,600 vial / Rs 1,700 foil; lancets 25 Rs 80): <https://sinocare.pk/sinocare-price-pakistan/> · Hamza Surgical (Lahore) strips Rs 1,550 (search excerpt).
- Manufacturer note: different Sinocare meters use different strips; "Safe AQ Smart… can only use Safe AQ test strips" (<https://en.sinocare.com/products/sinocare-blood-glucose-test-strips>, search excerpt).
- **Strips ≈ Rs 32/test.** Calibration: no coding claimed. **Routes B–E: UNSUPPORTED** (no radio, no port). Manual only. **Risk:** 10-result memory, so users must log immediately.

### 2.5 ACON On Call EZ II / On Call Plus
- **PK prices:** My Vitamin Store EZ II Rs 2,350 (in stock); On Call Plus strips 50 Rs 1,327 ("for use with On Call EZ II"): <https://www.myvitaminstore.pk/collections/oncall> · Sehat "On Call Plus Meter Kit" Rs 1,412 ([category](https://sehat.com.pk/categories/Over-The-Counter-Drugs/Blood-glucose-control-/Glucometers/)). Marham lists EZ II at Rs 1,699 (search excerpt).
- **Strips ≈ Rs 26.5/test** (cheapest branded strip found). **Calibration: code chip with every strip box** (On Call Plus manual).
- **Manual (On Call Plus):** data port that "sends information to a computer via an optional data transfer cable"; transfer uses PC software over a serial port; 300-record memory, 9600-baud port (FDA K090057): <https://www.medaval.ie/docs/manuals/Acon-On-Call-Plus-Manual.pdf> · <https://www.accessdata.fda.gov/cdrh_docs/pdf9/K090057.pdf> (search excerpts). EZ II's own manual was **not** fetched, so its port is **UNVERIFIED**.
- **Routes B/C/D: UNSUPPORTED.** Route E: PC-cable only, not a phone integration. **Risk:** code-chip mismatch errors; ACON support in PK is via distributors only.

### 2.6 Contour Plus / Contour TS (Ascensia, Pakistan lineup)
- Ascensia Pakistan lists only **CONTOUR PLUS** and **CONTOUR TS** meters (plus Contour Diabetes App page): <https://www.diabetes.ascensia.pk/products/> (Karachi office, +92 21 35834471-3).
- **PK prices (Dawaai):** Contour Plus meter Rs 3,722 (sold out); Contour TS meter Rs 2,755; Contour Plus strips 50 Rs 2,755 (sold out), 25 Rs 1,425 (sold out); Contour TS strips 50 Rs 2,090 (sold out): <https://dawaai.pk/brands/ascensia-diabetes-care-1392>
- No wireless (Roche third-party table lists Contour Plus/TS with a "Bayer's blue USB (3.5 mm)" cable). **Routes B/C/D: UNSUPPORTED.** **Risk:** widespread "sold out" on Dawaai.

### 2.7 Reference-only: Contour Plus One (not confirmed in PK)
- BLE meter; Contour Diabetes app → **Apple Health SUPPORTED** ([Ascensia Canada support](https://community.contourcare.ca/s/app-software-support)). Android Health Connect: **UNVERIFIED** (Sahha: "an iOS integration… not Health Connect": <https://sahha.ai/integrations/contour-diabetes/>). Direct BLE: xDrip's `BluetoothGlucoseMeter` targets 0x1808 and has Contour-specific handling (`CONTOUR_SERVICE 00000000-0002-11e2-9e96-0800200c9a66`): [source](https://raw.githubusercontent.com/NightscoutFoundation/xDrip/master/app/src/main/java/com/eveningoutpost/dexdrip/services/BluetoothGlucoseMeter.java). **Do not buy for a PK FYP** unless a PK seller is confirmed.

### 2.8 Reference-only: OneTouch Verio Flex / Verio Reflect (grey import)
- **Health Connect: SUPPORTED (official LifeScan doc, published 2026-03-22, updated 2026-07-28):** "you can share your blood glucose data with Health Connect… Health Connect will only receive blood glucose readings taken after the connection is complete… readings with a future date or time will not be shared": <https://www.onetouch.com/s/article/OneTouch-Reveal-Mobile-App-Android-Apps> (US page; regional app availability in Pakistan **UNVERIFIED**).
- **HealthKit: SUPPORTED:** <https://support.onetouch.com/s/article/OneTouch-Reveal-Mobile-App-iOS-Apps-canada> · **CSV export: SUPPORTED** (values, timestamps, manual flag, meal tags, notes; 14/30/90 days): <https://www.onetouch.com/s/article/OneTouch-Reveal-Mobile-App-Android-Navigation-Bar> (search excerpt).
- **Direct BLE:** treat as proprietary/UNVERIFIED (not standard-documented). **PK:** grey import at Rs 7,850–17,825 for the meter and very expensive strips → poor for an affordable FYP.

---

## 3. Platform research

### 3.1 Android Health Connect: BloodGlucoseRecord (Route C)
- **Record:** `androidx.health.connect.client.records.BloodGlucoseRecord`, "a single instantaneous blood glucose reading". Fields: `time: Instant`, `zoneOffset: ZoneOffset?`, `metadata` (includes `dataOrigin` package for source attribution), `level: BloodGlucose`, `specimenSource: Int`, `mealType: Int`, `relationToMeal: Int`. Reference: <https://developer.android.com/reference/kotlin/androidx/health/connect/client/records/BloodGlucoseRecord> (page header: "Added in 1.1.0").
  - `specimenSource`: UNKNOWN 0, INTERSTITIAL_FLUID 1, **CAPILLARY_BLOOD 2**, PLASMA 3, SERUM 4, TEARS 5, WHOLE_BLOOD 6. → **Use this to separate finger-prick records from CGM (interstitial fluid).** Treat UNKNOWN as "needs user confirmation"; never auto-label it SMBG.
  - `relationToMeal`: UNKNOWN 0, GENERAL 1, FASTING 2, BEFORE_MEAL 3, AFTER_MEAL 4. `mealType` uses the shared MealType constants.
- **Permissions:** `android.permission.health.READ_BLOOD_GLUCOSE` (and `WRITE_BLOOD_GLUCOSE` if NutriSole writes manual entries back). Extra: `android.permission.health.READ_HEALTH_DATA_HISTORY` to read data older than 30 days; `android.permission.health.READ_HEALTH_DATA_IN_BACKGROUND` for background reads. Mandatory fields: level, specimenSource, mealType, relationToMeal, metadata, time. Source: <https://developer.android.com/health-and-fitness/guides/health-connect/plan/data-types> (last updated 2026-09-23).
- **Publishing:** apps must complete the **health apps declaration in Play Console** for HC data types or users see access errors (same page). The library README says approval can take ~7 days plus 5–7 business days of allow-list propagation.
- **Availability / min OS:** Health Connect needs **Android 9 (API 28)+ with Google Play services**. It is built into Settings on Android 14+ and is a Play Store app on 13 and lower. Not supported in work profiles. <https://developer.android.com/health-and-fitness/health-connect/availability> (search excerpt; also stated on the HC overview). No Pakistan region restriction was found.
- **Feasibility verdict:** platform **SUPPORTED**. End-to-end with a PK-available meter **UNVERIFIED** (no PK-available meter's app is documented to write SMBG to HC). Recommendation: implement the reader with provenance (`metadata.dataOrigin`, `metadata.id` as the external record UID for dedupe), filter `specimenSource == CAPILLARY_BLOOD`, and test with the **Health Connect Toolbox** using synthetic records. Ship it behind a "beta/compatible apps" label.

### 3.2 React Native library (RN 0.86.3, New Architecture)
- **`react-native-health-connect`** (matinzd), npm latest **4.1.3** (published 2026-08-06); last main-branch commit 2026-08-26 ("replace deprecated TurboReactPackage and ReactModuleInfo APIs"). README: "Supports both old and new architecture ✅", requires RN ≥ 0.71 (latest patch), Health Connect `minSdkVersion=26`, Expo example uses compileSdk/targetSdk 36. It needs `HealthConnectPermissionDelegate.setPermissionDelegate(this)` in `MainActivity.onCreate` for RN CLI apps. Codegen spec `RNHealthConnectSpec` (TurboModule). peerDeps: react, react-native `*`. Repo: <https://github.com/matinzd/react-native-health-connect> (420★, 50 open issues).
- **RN 0.86 compatibility:** not explicitly stated → **REQUIRES BUILD TEST** in `native/`. Maintenance looks **active** (multiple 2026 releases).
- iOS counterparts named by that README (not verified here): `@kingstinct/react-native-healthkit`, `react-native-health`.

### 3.3 Apple HealthKit (Route D)
- `HKQuantityTypeIdentifier.bloodGlucose`: "A quantity sample type that measures the user's blood glucose level". iOS 8.0+. Mass/volume units (mg/dL or mmol/L, region-dependent; use `preferredUnits(for:)`). Discrete aggregation. Metadata key `HKMetadataKeyBloodGlucoseMealTime`. "Don't save samples… when the meter is processing control solution." <https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/bloodglucose>
- Authorization goes through `HKHealthStore` per Apple's "Authorizing access to health data" guide (linked from the same page; not fetched in detail). It needs the HealthKit capability plus `NSHealthShareUsageDescription`.
- Writers documented: OneTouch Reveal, mySugr, Contour Diabetes (see §2). Defer native iOS work until an iPhone test device exists.

### 3.4 Bluetooth SIG Glucose Service / Profile (Route B)
- Spec: Glucose Service v1.0.1 (2022-01-18): <https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/GLS_v1.0.1/out/en/index-en.html> · Glucose Profile 1.0.1: <https://www.bluetooth.com/specifications/specs/glucose-profile-1-0-1/>
- **Service UUID 0x1808.** Characteristics (UUIDs as used in xDrip's implementation, [source](https://raw.githubusercontent.com/NightscoutFoundation/xDrip/master/app/src/main/java/com/eveningoutpost/dexdrip/services/BluetoothGlucoseMeter.java)):

| Characteristic | UUID | Requirement / properties (GLS v1.0.1 Table 3.1) |
|---|---|---|
| Glucose Measurement | **0x2A18** | **Mandatory**, Notify; flags, **sequence number (uint16, never rolls over)**, Base Time, optional Time Offset (minutes), concentration as SFLOAT + Type/Sample-Location nibble, optional Sensor Status Annunciation. Units flag bit 2: 0 = kg/L (mg/dL ×10⁻⁵), 1 = mol/L (mmol/L ×10⁻³). Bit 4 = context follows. |
| Glucose Measurement Context | **0x2A34** | **Optional**, Notify; same sequence number; meal, tester/health, carbs, exercise, medication, HbA1c. **Accu-Chek Instant does not provide it.** |
| Glucose Feature | **0x2A51** | Mandatory, Read (Indicate if it can change). UUID from the Bluetooth Assigned Numbers list; **not in xDrip's source, verify against Assigned Numbers before coding.** |
| Record Access Control Point (RACP) | **0x2A52** | Mandatory, Indicate + Write, **"Writeable with Authentication"** → bonding/passkey required. Ops: Report Stored Records (All / ≥ sequence number mandatory), Report Number of Stored Records, Abort; Delete optional. Client must enable CCCD indications first, or the meter returns error 0x81. 30 s ATT timeout; records sent oldest-first; Time Offset must be in the first record. |

- **Implementation notes for NutriSole:** dedupe on (device id/serial + sequence number); compute user-facing time = Base Time + Time Offset; store original unit/value; the Sensor Status/Type nibble can flag control solution, so don't import control-solution records as user readings. Proprietary encryption or an undocumented protocol is a **blocker**: do not reverse-engineer it.

---

## 4. Ranked recommendations

### (1) Lowest ongoing strip cost (PK retail, 2026-10-16)
1. **On Call Plus strips** (On Call EZ II / On Call Plus): **≈ Rs 26.5/test** (Rs 1,327/50, My Vitamin Store). Needs a code chip.
2. **Sinocare Safe AQ strips** (Safe AQ Voice): **≈ Rs 32/test** (Rs 1,600/50, sinocare.pk).
3. **Accu-Chek Instant strips** (Instant / Instant S): **≈ Rs 40.2/test** (Rs 2,011.20/50, Dawa; Rs 3,950/100 at Hamza Surgical ≈ Rs 39.5).
4. Contour TS strips ≈ Rs 41.8 (sold out at Dawaai; meter not BT) · Accu-Chek Guide ≈ Rs 48.1 · Contour Plus ≈ Rs 55 (sold out) · OneTouch Verio (grey) ≈ Rs 250+.
None of the top two have any connectivity, so they suit manual entry only.

### (2) Best documented software compatibility
1. **OneTouch Verio Flex/Reflect + OneTouch Reveal**: the only one with **official** Health Connect + HealthKit + CSV docs. Pakistan availability is grey-import only and strips are very expensive, so it is **not recommended for purchase** in Lahore.
2. **Accu-Chek Guide**: official Continua-standard claim + passkey; standard GLS path (REQUIRES HARDWARE TEST); HealthKit via mySugr. Kit currently sold out on Dawaai.
3. **Accu-Chek Instant**: official BLE passkey + USB; GLS confirmed by an open-source implementation with documented quirks; HealthKit via mySugr; in stock in PK.

### (3) Safest low-cost FYP demonstration route
- **Route:** Manual entry (always) **+** one direct-BLE GLS hardware test on **Accu-Chek Instant** (the Bluetooth model; check the box says "Instant", not "Instant S", and shows Bluetooth/mySugr). Health Connect reader built and tested with synthetic Toolbox data, clearly labelled as not meter-verified.
- **Model I would buy (needs the user's approval first):** **Accu-Chek Instant**, about Rs 4,340 (Dawa Healthcare, sale) to Rs 4,752 (Dawaai), plus one 50-strip box at about Rs 2,011. Total ≈ **Rs 6,350–6,760**. (Cheaper meter listings seen earlier in this research: Divine Medicines Rs 3,470, Hamza Surgical Rs 3,999, Marham Rs 4,499; D. Watson Rs 5,293.) It is documented as BLE with passkey pairing, it is sold by mainstream PK pharmacies with Roche PK support, its strips are mid-priced and widely stocked, and it has the clearest evidence of a standard 0x1808 GLS for a PK-available meter.
- **Budget alternative for a manual-only demo:** Sinocare Safe AQ Voice at Rs 1,599 (no import possible).
- **Pass/fail hardware test plan (before any auto-sync claim):** pair with passkey on Android 12+ → discover 0x1808 → enable CCCD on 0x2A18 and indications on 0x2A52 *(scoped to service 0x1808)* → RACP "Report Number of Stored Records" → "Report Stored Records ≥ seq N" → verify value/unit/time against the meter screen for ≥5 readings → re-run to confirm dedupe → check whether mySugr's pairing is displaced.

---

## 5. Key blockers & open questions
1. **No PK-available meter has a documented Health Connect writer.** mySugr = Apple Health + Google Fit (and Google Fit APIs end with 2026). OneTouch Reveal (documented HC writer) needs a grey-import meter. → Route C stays UNVERIFIED end-to-end.
2. **Accu-Chek Instant BLE quirks:** no Context characteristic; decoy 0x2A52 in a vendor service; some users report "pairs, no data". Needs a real hardware test. Roche gives no third-party SDK or support.
3. **Single-bond risk:** pairing NutriSole may break the user's mySugr pairing (and vice versa).
4. **Stock volatility:** Accu-Chek Guide kit and Contour Plus/TS strips show sold out on Dawaai today. Dawa Healthcare ships outside Karachi by courier only with online payment.
5. **Play Console health declaration** is required before READ_BLOOD_GLUCOSE works in a released build. For an FYP debug build use internal testing; plan the allow-list delay.
6. **RN 0.86 + react-native-health-connect 4.1.3** is not explicitly certified, so a build test is required. A BLE library choice for RN 0.86 New Architecture was **not researched here** (UNVERIFIED).
7. **Unverified items:** On Call EZ II data port; OneTouch Reveal availability on the Pakistan Play Store; 25-strip PK prices for Instant; mySugr country-specific meter lists for Pakistan; Glucose Feature UUID 0x2A51 (standard, not cross-checked in a fetched source).
8. **No vendor cloud API** (Roche, Ascensia, LifeScan, ACON, Sinocare) was found for SMBG import. Do not scrape vendor accounts or impersonate apps.

---

## 6. Source list (fetched 2026-10-16 unless marked "excerpt")
- Roche PK Instant: https://www.accu-chek.com.pk/products/meters/instant · Instant vs Instant S: https://www.accu-chek.com.pk/product-comparison/instant-vs-instant-s
- Roche UK Instant FAQ: https://www.accu-chek.co.uk/support/instant/faq
- Roche India connectivity FAQ (Guide, Continua): https://www.accu-chek.in/faq/connectivity
- Roche Care Platform connectivity guide: https://diabetes.roche.com/sites/g/files/papvje141/files/2023-08/RDCP_Connectivity_Guide.pdf
- Dawa Healthcare Instant: https://dawahealthcare.biz/products/accu-chek-meter-instant
- Dawaai Accu-Chek: https://dawaai.pk/brands/accu-chek-1457 · Dawaai Ascensia: https://dawaai.pk/brands/ascensia-diabetes-care-1392
- Sehat/Ailaaj glucometers: https://sehat.com.pk/categories/Over-The-Counter-Drugs/Blood-glucose-control-/Glucometers/
- Sinocare PK: https://sinocare.pk/sinocare-price-pakistan/ · https://sinocare.pk/product/sinocare-safe-aq-blood-glucometer-with-voice-light-feature/
- My Vitamin Store On Call: https://www.myvitaminstore.pk/collections/oncall
- On Call Plus manual (excerpt): https://www.medaval.ie/docs/manuals/Acon-On-Call-Plus-Manual.pdf · FDA K090057 (excerpt): https://www.accessdata.fda.gov/cdrh_docs/pdf9/K090057.pdf
- Ascensia Pakistan: https://www.diabetes.ascensia.pk/products/
- OneTouch Reveal Android (Health Connect): https://www.onetouch.com/s/article/OneTouch-Reveal-Mobile-App-Android-Apps
- mySugr Play listing: https://play.google.com/store/apps/details?id=com.mysugr.android.companion&hl=en
- xDrip Accu-Chek Instant thread: https://github.com/NightscoutFoundation/xDrip/discussions/2997 · xDrip BLE meter source: https://raw.githubusercontent.com/NightscoutFoundation/xDrip/master/app/src/main/java/com/eveningoutpost/dexdrip/services/BluetoothGlucoseMeter.java
- Bluetooth GLS v1.0.1: https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/GLS_v1.0.1/out/en/index-en.html
- Health Connect BloodGlucoseRecord: https://developer.android.com/reference/kotlin/androidx/health/connect/client/records/BloodGlucoseRecord · data types/permissions: https://developer.android.com/health-and-fitness/guides/health-connect/plan/data-types
- react-native-health-connect: https://github.com/matinzd/react-native-health-connect · npm registry https://registry.npmjs.org/react-native-health-connect
- Apple HealthKit bloodGlucose: https://developer.apple.com/documentation/healthkit/hkquantitytypeidentifier/bloodglucose
- Sahha on Contour (iOS-only): https://sahha.ai/integrations/contour-diabetes/ (excerpt)
