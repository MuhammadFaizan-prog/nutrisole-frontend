// G9 Stage J7 (cv-gauntlet-device): QA-build replacement for flags.ts. NEVER imported directly: metro.config.js substitutes this
// file for flags.ts ONLY when the bundle is built with NUTRISOLE_QA=1 (the Android QA APK workflow,
// .github/workflows/android-qa-apk.yml). Without that env the committed flags.ts (false) is bundled, so production is unchanged.
export const CV_DEBUG_PIPELINE = true as boolean;
export const NUTRISOLE_QA_BUILD_MARKER = 'NUTRISOLE_QA_FLAGS_ON';
