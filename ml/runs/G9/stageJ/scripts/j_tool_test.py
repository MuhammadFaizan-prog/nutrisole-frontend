"""G9 Stage J: headless-Chromium smoke test of the labelling tool: open, enter a name, label 3 items with keys (incl. a tag, a note and an
'other produce' name), reload (localStorage autosave must restore), export CSV and check its rows. Usage: j_tool_test.py <html> <out_dir>"""
import sys, csv, os, shutil, tempfile
from playwright.sync_api import sync_playwright
html, outd = os.path.abspath(sys.argv[1]), sys.argv[2]; os.makedirs(outd, exist_ok=True)
prof = tempfile.mkdtemp(); res = {}
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(prof, executable_path="/usr/bin/chromium", headless=True, accept_downloads=True, args=["--no-sandbox"])
    pg = ctx.new_page(); pg.set_viewport_size({"width": 1366, "height": 768}); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("file://" + html); pg.wait_for_selector("#nameinput", state="visible", timeout=30000)
    pg.fill("#nameinput", "TestAnnotator"); pg.keyboard.press("Enter"); pg.wait_for_timeout(300); pg.screenshot(path=f"{outd}/tool_start.png")
    first = [pg.inner_text("#itemid")]
    pg.keyboard.press("1"); pg.wait_for_timeout(150); first.append(pg.inner_text("#itemid"))       # apple, auto-advance
    pg.keyboard.press("c"); pg.keyboard.press("3"); pg.wait_for_timeout(150); first.append(pg.inner_text("#itemid"))  # cut + citrus
    pg.keyboard.press("6"); pg.select_option("#othername", "lemon_or_lime"); pg.keyboard.press("n"); pg.keyboard.type("test note, with comma")
    pg.keyboard.press("Escape"); pg.wait_for_timeout(200)
    res["progress_before_reload"] = pg.inner_text("#progress"); pg.screenshot(path=f"{outd}/tool_screenshot.png")
    pg.reload(); pg.wait_for_timeout(800); res["progress_after_reload"] = pg.inner_text("#progress"); res["start_overlay_after_reload"] = pg.is_visible("#start")
    with pg.expect_download() as d: pg.keyboard.press("e")
    dl = d.value; dst = f"{outd}/{dl.suggested_filename}"; dl.save_as(dst); res["export_file"] = dst
    res["page_errors"] = errs; ctx.close()
rows = list(csv.DictReader(open(dst, newline="")))
lab = {r["item_id"]: r for r in rows if r["label"]}
res["rows"] = len(rows); res["labelled"] = len(lab)
res["checks"] = dict(apple=lab.get(first[0], {}).get("label") == "apple",
                     citrus_cut=lab.get(first[1], {}).get("label") == "citrus_orange" and lab.get(first[1], {}).get("cut") == "1",
                     other=lab.get(first[2], {}).get("label") == "other_produce" and lab.get(first[2], {}).get("other_produce_name") == "lemon_or_lime"
                           and lab.get(first[2], {}).get("note") == "test note, with comma",
                     annotator=all(r["annotator"] == "TestAnnotator" for r in rows))
shutil.rmtree(prof, ignore_errors=True); print(res); sys.exit(0 if all(res["checks"].values()) and not res["page_errors"] else 1)
