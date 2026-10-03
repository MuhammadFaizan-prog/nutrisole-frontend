"""Exercise the installed standalone app through Android's own test interfaces."""
import json
import hashlib
import re
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

native = Path(__file__).resolve().parents[1]
root = native.parent
adb = Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe"
serial = sys.argv[1] if len(sys.argv) > 1 else "emulator-5554"
package = "com.muhammadfaizan.nutrisole"
out = root / ("artifacts/native/responsive-qa/v1.0.3/interactions" if "--responsive" in sys.argv else "artifacts/native/plain-rn-qa")
out.mkdir(parents=True, exist_ok=True)
references = out / "reference-screens"
references.mkdir(exist_ok=True)
model = (root / "src/nutrisole/extensions/model.ts").read_text(encoding="utf-8")
extras = re.findall(r"'([^']+)'", model.split("export const extensionRoutes = [", 1)[1].split("] as const", 1)[0])
screens = ["onboarding", "home", "scan", "log-meal", "weekly-plan", "profile"] + extras
apk = native / "android/app/build/outputs/apk/release/app-release.apk"
report = {"serial": serial, "apkSha256": hashlib.sha256(apk.read_bytes()).hexdigest(), "screens": [], "directoryTaps": [], "interactions": [], "errors": [], "standalone": True, "iosRuntimeTested": False, "physicalPhoneTested": False}

def run(*args, binary=False):
    result = subprocess.run([str(adb), "-s", serial, *args], capture_output=True, timeout=45)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors="replace") + result.stdout.decode(errors="replace"))
    return result.stdout if binary else result.stdout.decode(errors="replace").strip()

def tree(name):
    run("shell", "uiautomator", "dump", "/sdcard/nutrisole-qa.xml")
    xml = run("shell", "cat", "/sdcard/nutrisole-qa.xml")
    (out / f"{name}.xml").write_text(xml, encoding="utf-8")
    return ET.fromstring(xml)

def capture(name):
    (out / f"{name}.png").write_bytes(run("exec-out", "screencap", "-p", binary=True))

def screen_in(doc, name):
    return any(node.get("resource-id", "").endswith("screen-" + name) for node in doc.iter("node"))

def go(name):
    run("shell", "am", "start", "-W", "-a", "android.intent.action.VIEW", "-d", f"nutrisole://screens/{name}", "-n", package + "/.MainActivity")
    time.sleep(0.8)
    doc = tree(name)
    if not screen_in(doc, name):
        time.sleep(1.2)
        doc = tree(name)
    assert run("shell", "pidof", package), "App process ended"
    assert screen_in(doc, name), f"Expected screen {name} did not render"
    capture(name)
    return doc

def scroll(doc, up=False):
    region = next((n for n in doc.iter("node") if n.get("scrollable") == "true"), None)
    if region is None:
        return False
    x1, y1, x2, y2 = map(int, re.findall(r"\d+", region.get("bounds")))
    # Slow, overlapping scrolls avoid flinging past a short directory row.
    start, end = (y1 + int((y2-y1)*.25), y1 + int((y2-y1)*.70)) if up else (y1 + int((y2-y1)*.75), y1 + int((y2-y1)*.30))
    run("shell", "input", "swipe", str((x1 + x2)//2), str(start), str((x1+x2)//2), str(end), "500")
    time.sleep(.2)
    return True

def tap(doc, label=None, resource=None, text=None):
    for attempt in range(10):
        for node in doc.iter("node"):
            if (label and node.get("content-desc", "").lower() == label.lower()) or (resource and node.get("resource-id", "").endswith(resource)) or (text and text in [node.get("text"), node.get("content-desc")]):
                points = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
                if len(points) == 4 and points[2] > points[0] and points[3] - points[1] >= 12:
                    run("shell", "input", "tap", str((points[0] + points[2]) // 2), str((points[1] + points[3]) // 2))
                    time.sleep(.6)
                    return
        if not scroll(doc, up=3 <= attempt < 6):
            break
        doc = tree("seek-control")
    capture("missing-control")
    raise AssertionError(f"Control missing or unreachable: {label or resource or text}")

def visible(doc, snippet):
    return any(snippet in (node.get("text", "") + node.get("content-desc", "")) for node in doc.iter("node"))

try:
    report['api'] = int(run('shell', 'getprop', 'ro.build.version.sdk'))
    installed_path = run('shell', 'pm', 'path', package).splitlines()[0].removeprefix('package:')
    report['installedApkSha256'] = run('shell', 'sha256sum', installed_path).split()[0]
    assert report['installedApkSha256'] == report['apkSha256'], 'Installed APK differs from the release artifact'
    report["configuration"] = {"size": run("shell", "wm", "size"), "density": run("shell", "wm", "density"), "fontScale": run("shell", "settings", "get", "system", "font_scale"), "navigation": run("shell", "cmd", "overlay", "list", "android")}
    run("logcat", "-c")
    run("shell", "pm", "clear", package)
    run("shell", "am", "force-stop", package)
    run("shell", "am", "start", "-W", "-n", package + "/.MainActivity")
    time.sleep(2)
    for attempt in range(4):
        startup = tree("cold-start")
        if screen_in(startup, "onboarding"):
            break
        time.sleep(1)
    capture("cold-start")
    assert screen_in(startup, "onboarding"), "Cold launch did not render onboarding"
    report["coldStart"] = "passed"
    print("PASS cold launch: real onboarding rendered", flush=True)
    for name in screens:
        doc = go(name)
        shutil.copyfile(out / f"{name}.png", references / f"{name}.png")
        report["screens"].append({"route": name, "status": "passed", "nativeNodes": sum(1 for _ in doc.iter("node"))})
        print("PASS screen: " + name, flush=True)
    doc = go("onboarding")
    tap(doc, resource="skip-onboarding")
    assert screen_in(tree("skip-result"), "home")
    report["interactions"].append("onboarding skip opens home")
    doc = go("log-meal")
    tap(doc, resource="increase-portion")
    doc = tree("portion-increased")
    assert visible(doc, "190"), "Portion did not update calories"
    tap(doc, resource="confirm-log-meal")
    assert screen_in(tree("logged-home"), "home")
    report["interactions"].append("portion increase recalculates calories and meal logging opens home")
    doc = go("log-meal")
    tap(doc, resource="portion-by-weight")
    doc = tree("portion-weight-sheet")
    tap(doc, label="Weight in grams")
    run("shell", "input", "keyevent", "123")
    for _ in range(3):
        run("shell", "input", "keyevent", "67")
    run("shell", "input", "text", "200")
    run("shell", "input", "keyevent", "4")
    tap(tree("portion-weight-input"), text="Save")
    doc = tree("portion-weight-saved")
    assert visible(doc, "104 calories"), "Weight mode did not recalculate calories"
    tap(doc, resource="portion-by-size")
    tap(tree("portion-size-sheet"), text="Small apple")
    doc = tree("portion-size-saved")
    assert visible(doc, "78 calories"), "Size mode did not recalculate calories"
    tap(doc, resource="increase-portion")
    doc = tree("portion-size-increased")
    assert visible(doc, "156 calories")
    tap(doc, resource="decrease-portion")
    doc = tree("portion-size-decreased")
    assert visible(doc, "78 calories")
    tap(doc, resource="save-for-later")
    assert screen_in(tree("portion-draft-home"), "home")
    report["interactions"].append("weight and size sheets, both portion controls and saving a draft work")
    doc = go("profile")
    tap(doc, resource="edit-glucose-unit")
    doc = tree("profile-unit-sheet")
    tap(doc, text="mmol/L")
    assert visible(tree("profile-unit-saved"), "mmol/L")
    report["interactions"].append("native preference sheet updates glucose unit")
    for label in ["Dietary Preferences", "Allergens", "Activity Preferences", "Mobility Constraints", "Timezone"]:
        doc = go("profile")
        tap(doc, label="Edit " + label)
        doc = tree("preference-" + label.lower().replace(" ", "-"))
        assert visible(doc, "Save"), "Preference editor did not open: " + label
        tap(doc, label="Cancel")
    report["interactions"].append("all six nested profile preference controls respond to physical taps")
    doc = go("profile")
    tap(doc, label="Edit Dietary Preferences")
    doc = tree("preference-edit")
    tap(doc, label="Dietary Preferences")
    run("shell", "input", "keyevent", "123")
    run("shell", "input", "text", "%sQA")
    run("shell", "input", "keyevent", "4")
    tap(tree("preference-edited"), text="Save")
    assert visible(tree("preference-saved"), "QA"), "Preference change did not persist"
    report["interactions"].append("preference input editing and sheet save update the profile")
    doc = go("home")
    tap(doc, resource="navigate-plan")
    doc = tree("home-plan-navigation")
    assert screen_in(doc, "weekly-plan")
    tap(doc, resource="select-tue")
    doc = tree("tuesday-selected")
    tap(doc, resource="show-nutrition")
    doc = tree("tuesday-nutrition")
    assert visible(doc, "Tue 19") and visible(doc, "Daily nutrition")
    tap(doc, resource="show-meals")
    doc = tree("meal-tab")
    tap(doc, resource="accept-breakfast")
    doc = tree("meal-accepted")
    if not visible(doc, "5/5"):
        for _ in range(3):
            scroll(doc, up=True)
        doc = tree("meal-accepted-summary")
    assert visible(doc, "5/5") and visible(doc, "100%")
    tap(doc, resource="substitute-breakfast")
    doc = tree("meal-substitute-sheet")
    tap(doc, text="Apple & Yogurt Bowl")
    assert visible(tree("meal-substituted"), "Apple & Yogurt Bowl")
    run("shell", "input", "keyevent", "4")
    assert screen_in(tree("android-back-home"), "home")
    report["interactions"].append("home navigation, weekday choice, nutrition tab, acceptance, substitution and Android back work")
    doc = go("home")
    tap(doc, resource="scan-food")
    doc = tree("camera-opened")
    assert screen_in(doc, "scan")
    tap(doc, resource="capture-food")
    assert screen_in(tree("camera-captured"), "log-meal")
    report["interactions"].append("home scan action and photo capture open portion confirmation")
    doc = go("scan")
    tap(doc, resource="video-mode")
    tap(tree("camera-video-mode"), resource="capture-food")
    doc = tree("camera-recording")
    assert visible(doc, "Demo recording"), "Video toggle did not start the demo recording"
    tap(doc, resource="capture-food")
    doc = tree("camera-recording-stopped")
    assert not visible(doc, "Demo recording")
    tap(doc, resource="photo-mode")
    tap(tree("camera-photo-mode"), resource="toggle-flash")
    tap(tree("camera-flash"), resource="choose-gallery-image")
    tap(tree("camera-gallery-sheet"), text="Grilled Chicken Bowl")
    tap(tree("camera-gallery-selected"), resource="capture-food")
    tap(tree("camera-gallery-demo"), text="Use Apple demo")
    assert screen_in(tree("camera-gallery-portion"), "log-meal")
    report["interactions"].append("camera video mode, recording toggle, flash and gallery capture flow work")
    doc = go("profile")
    tap(doc, resource="privacy-and-consent")
    tap(tree("privacy-sheet"), text="Explore all screens")
    doc = tree("directory-opened")
    assert screen_in(doc, "flow-directory")
    tap(doc, resource="directory-sign-in")
    doc = tree("directory-accounts")
    assert screen_in(doc, "sign-in")
    tap(doc, resource="action-sign-in")
    doc = tree("account-validation")
    assert visible(doc, "valid email"), "Empty account form was not validated"
    tap(doc, label="Close")
    report["interactions"].append("in-app directory opens added account screens and validates empty sign-in")
    doc = go("home")
    tap(doc, resource="all-screens")
    doc = tree("home-all-screens")
    assert screen_in(doc, "flow-directory") and visible(doc, "38 screens")
    report["interactions"].append("visible Home All screens entry opens the complete 38-screen directory")
    # Exercise real directory taps, not deep links, for every screen in the app.
    for destination in screens:
        doc = go("home")
        tap(doc, resource="all-screens")
        doc = tree("directory-seek-" + destination)
        found = None
        for seek in range(22):
            found = next((n for n in doc.iter("node") if n.get("resource-id", "").endswith("directory-" + destination) and len(re.findall(r"\d+", n.get("bounds", ""))) == 4 and int(re.findall(r"\d+", n.get("bounds", ""))[3]) - int(re.findall(r"\d+", n.get("bounds", ""))[1]) >= 24), None)
            if found is not None:
                break
            assert scroll(doc), "Directory cannot scroll to " + destination
            doc = tree("directory-seek-" + destination)
        assert found is not None, "Directory route missing: " + destination
        tap(doc, resource="directory-" + destination)
        assert screen_in(tree("directory-result-" + destination), destination), "Directory did not open " + destination
        report["directoryTaps"].append({"route": destination, "status": "passed"})
        print("PASS directory tap: " + destination, flush=True)
    report["interactions"].append("all 38 screens are reachable through physical Home directory taps")
    doc = go("home")
    tap(doc, resource="view-plan")
    assert screen_in(tree("home-view-plan-card"), "weekly-plan")
    doc = go("home")
    tap(doc, resource="open-health")
    assert screen_in(tree("home-health-card"), "glucose-overview")
    report["interactions"].append("Home View Plan and Health cards remain reachable and open their correct screens")
    doc = go("create-account")
    for label, value in [("Name", "Demo%sTester"), ("Email", "qa@nutrisole.test"), ("Password", "Frontend123")]:
        tap(doc, label=label)
        focused = tree("account-focused-" + label.lower())
        assert any(n.get("content-desc") == label and n.get("focused") == "true" for n in focused.iter("node")), label + " lost focus when moving between fields"
        assert "mInputShown=true" in run("shell", "dumpsys", "input_method"), label + " did not keep the keyboard open"
        run("shell", "input", "text", value)
        time.sleep(0.5)
        doc = tree("account-input-" + label.lower())
        capture("account-keyboard-" + label.lower())
        if label != "Password":
            assert any(n.get("content-desc") == label and n.get("text") == value.replace("%s", " ") for n in doc.iter("node")), label + " did not retain the complete input"
    run("shell", "input", "keyevent", "4")
    doc = tree("account-keyboard-dismissed")
    tap(doc, label="Show password")
    doc = tree("account-password-visible")
    assert visible(doc, "Frontend123"), "Password visibility did not reveal the complete test input"
    tap(doc, label="Hide password")
    doc = tree("account-password-hidden")
    tap(doc, resource="action-toggle-terms")
    doc = tree("account-consent")
    tap(doc, resource="action-create-account")
    assert screen_in(tree("account-created"), "verify-email")
    report["interactions"].append("native account inputs retain focus while moving between fields with the keyboard open; password visibility, consent and simulated submission work")
    doc = go("food-selector")
    tap(doc, resource="action-choose-food-Banana")
    doc = tree("food-selected")
    assert visible(doc, "Confirm Banana")
    tap(doc, resource="action-go-nutrition-details")
    doc = tree("banana-nutrition")
    assert screen_in(doc, "nutrition-details") and visible(doc, "Banana") and visible(doc, "89 kcal")
    report["interactions"].append("food selection updates nutrition data")
    doc = go("add-reading")
    tap(doc, label="Reading")
    run("shell", "input", "text", "110")
    run("shell", "input", "keyevent", "4")
    doc = tree("reading-input")
    tap(doc, resource="action-review-reading")
    doc = tree("reading-review")
    assert visible(doc, "110 mg/dL")
    tap(doc, text="Confirm & save reading")
    doc = tree("reading-saved")
    assert screen_in(doc, "reading-detail") and visible(doc, "Manual record") and visible(doc, "110")
    report["interactions"].append("native numeric input, reading validation, review and save work")
    doc = go("assistant")
    tap(doc, resource="action-assistant-plan")
    assert visible(tree("assistant-response"), "Review your dietary preferences")
    report["interactions"].append("assistant prompt updates the scripted frontend response")
    report["status"] = "passed"
except Exception as error:
    report["status"] = "failed"
    report["errors"].append(str(error))
    print("FAIL " + str(error), flush=True)
finally:
    try:
        crash = run("logcat", "-d", "-b", "crash")
        (out / "crash-log.txt").write_text(crash, encoding="utf-8")
        logs = run("logcat", "-d", "-s", "ReactNativeJS", "AndroidRuntime")
        (out / "runtime-log.txt").write_text(logs, encoding="utf-8")
        report["crashFree"] = "FATAL EXCEPTION" not in crash and "Fatal signal" not in crash
        if not report["crashFree"]:
            report["status"] = "failed"
    except Exception as error:
        report["errors"].append(str(error))
        report["status"] = "failed"
    (out / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report.get("status"), "screens": len(report["screens"]), "interactions": report["interactions"], "errors": report["errors"]}), flush=True)
sys.exit(0 if report.get("status") == "passed" else 1)
