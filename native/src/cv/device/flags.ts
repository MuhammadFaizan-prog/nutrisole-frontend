// G9 Stage J5 (cv-gauntlet-device): phone-test switch for the real camera + model pipeline on the Scan screen.
// OFF by default. When false the Scan screen renders exactly as before, no camera permission is requested and no native camera or
// inference module is loaded. To test on the phone, set it to true in a LOCAL debug build only (never commit `true`, never ship it).
export const CV_DEBUG_PIPELINE = false as boolean;
