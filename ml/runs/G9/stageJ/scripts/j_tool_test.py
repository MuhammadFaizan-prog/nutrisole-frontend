"""Offline smoke test of the ORIGINAL tool, in a fresh disposable browser profile.

Usage: python j_tool_test.py original.html NEW_OUTPUT_DIR [--browser /path/to/chromium]
Outputs are AUTOMATION_TEST_NOT_HUMAN; never submit them as human annotation exports.
"""
import argparse
import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
import j_annotation as V


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("html")
    ap.add_argument("out_dir")
    ap.add_argument("--browser")
    args = ap.parse_args(argv)
    html, dest = Path(args.html).resolve(), Path(args.out_dir).resolve()
    dest.mkdir(parents=True, exist_ok=False)
    browser = args.browser or os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE")
    if not browser and os.name == "nt":
        candidates = sorted((Path.home() / "AppData/Local/ms-playwright").glob("chromium-*/chrome-win*/chrome.exe"))
        if candidates:
            browser = str(candidates[-1])
    name = "TestAnnotator_OFFLINE_AUTOMATION"
    note = 'test note, with comma and "quote"\nملٹا'
    with tempfile.TemporaryDirectory(prefix="nutrisole-tool-smoke-") as profile, sync_playwright() as p:
        if not Path(profile).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise ValueError("profile outside intended temporary root")
        opts = dict(headless=True, accept_downloads=True, viewport={"width":1366,"height":768}, offline=True)
        if browser:
            opts["executable_path"] = browser
        ctx = p.chromium.launch_persistent_context(profile, **opts)
        try:
            pg = ctx.new_page()
            errs, remote = [], []
            pg.on("pageerror", lambda e: errs.append(str(e)))
            pg.on("request", lambda r: remote.append(r.url) if r.url.startswith(("http:","https:")) else None)
            pg.on("dialog", lambda d: d.accept())
            pg.goto(html.as_uri())
            pg.locator("#nameinput").fill(name)
            pg.locator("#nameinput").press("Enter")
            first = [pg.locator("#itemid").inner_text()]
            count = pg.evaluate("ITEMS.length")
            pg.keyboard.press("1")
            first.append(pg.locator("#itemid").inner_text())
            pg.keyboard.press("c")
            pg.keyboard.press("3")
            first.append(pg.locator("#itemid").inner_text())
            pg.keyboard.press("6")
            pg.locator("#othername").select_option("lemon_or_lime")
            pg.locator("#note").fill(note)
            pg.locator("#note").press("Escape")
            expect(pg.locator("#progress")).to_have_text(f"3 / {count} done")
            pg.reload()
            expect(pg.locator("#start")).not_to_be_visible()
            expect(pg.locator("#progress")).to_have_text(f"3 / {count} done")
            with pg.expect_download() as event:
                pg.keyboard.press("e")
            dl = event.value
            csv_path = dest / dl.suggested_filename
            dl.save_as(str(csv_path))
            rows = V.load_table(csv_path, exact_schema=True)
            labelled = {r["item_id"]:r for r in rows if r["label"]}
            assert len(rows) == count and len(labelled) == 3
            assert labelled[first[0]]["label"] == "apple"
            assert labelled[first[1]]["label"] == "citrus_orange" and labelled[first[1]]["cut"] == "1"
            assert labelled[first[2]]["other_produce_name"] == "lemon_or_lime" and labelled[first[2]]["note"] == note
            assert all(r["annotator"] == name for r in rows)
            pg.locator('input[type="file"]').set_input_files(str(csv_path))
            expect(pg.locator("#progress")).to_have_text(f"3 / {count} done")
            assert not errs and not remote
            result = dict(provenance="AUTOMATION_TEST_NOT_HUMAN", html_sha256=V.digest(html), browser=Path(browser).name if browser else "playwright-chromium",
                          browser_version=ctx.browser.version if ctx.browser else "persistent", offline=True, rows=count, labelled=3,
                          export_schema=True, export_sha256=V.digest(csv_path), autosave_reload=True, stable_id_mapping=True,
                          comma_quote_newline_unicode_roundtrip=True, import_roundtrip=True, page_errors=errs, external_requests=remote, passed=True)
            (dest / "offline_tool_test.json").write_text(json.dumps(result,indent=2)+"\n", encoding="utf-8")
            print(json.dumps(result,indent=2))
            return result
        finally:
            ctx.close()


if __name__ == "__main__":
    main()
