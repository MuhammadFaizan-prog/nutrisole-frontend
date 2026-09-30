"""Package the reviewed concept images and build a local review gallery."""
from pathlib import Path
import hashlib, html, json, shutil
from PIL import Image

root = Path(__file__).resolve().parent
manifest_path = root / "concept-manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
outputs = json.loads((root / "image-outputs.json").read_text(encoding="utf-8-sig"))
lookup = {item["id"]: item for item in outputs}
image_dir = root / "images"
image_dir.mkdir(exist_ok=True)
initial_dir = root / "refinement-initials"
cards, index = [], []
for order, concept in enumerate(manifest["concepts"], 1):
    record = lookup[concept["id"]]
    source = Path(record["sourcePath"])
    target = image_dir / (concept["id"] + ".png")
    assert root in target.resolve().parents
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    with Image.open(target) as image:
        image.verify()
    with Image.open(target) as image:
        dimensions = list(image.size)
    image_info = {
        "id": concept["id"], "title": concept["title"], "role": concept["role"],
        "requirements": concept["fr"], "path": "images/" + target.name,
        "dimensions": dimensions, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "reviewStatus": record["reviewStatus"], "reviewNotes": record["notes"]
    }
    if record.get("originalSourcePath"):
        initial_dir.mkdir(exist_ok=True)
        initial_target = initial_dir / target.name
        shutil.copy2(record["originalSourcePath"], initial_target)
        image_info["initialImage"] = "refinement-initials/" + target.name
        image_info["refinementPrompt"] = record.get("refinementPrompt")
    index.append(image_info)
    concept["image"] = image_info
    role = "Consumer" if concept["role"] == "consumer" else concept["role"].replace("-", " ").title()
    category = "consumer" if concept["role"] == "consumer" else "staff"
    src = image_info["path"]
    title = html.escape(concept["title"])
    cards.append(
        f'<article data-role="{category}"><header><span>{order:02d} · {html.escape(role)}</span>'
        f'<h2>{title}</h2><p>{html.escape(", ".join(concept["fr"]))}</p></header>'
        f'<a href="{src}" target="_blank"><img src="{src}" alt="{title} proposed UI screen"'
        f' width="{dimensions[0]}" height="{dimensions[1]}" loading="lazy"></a>'
        f'<footer><a href="{src}" download>Download PNG</a><details><summary>Design brief</summary>'
        f'<p>{html.escape(concept["brief"])}</p></details></footer></article>'
    )
manifest["status"] = "generated-reviewed-primary-concepts"
manifest["generatedCount"] = len(index)
manifest["reviewScope"] = "Visual and copy review of primary concepts; not approval, browser testing, implementation or pixel-match certification"
manifest["secondaryStates"] = "See coverage.json requiredVariants; not all branches have separate images."
manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
(root / "concept-images.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
page = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NutriSole · Missing screen concepts</title><style>
:root{color-scheme:light;--cream:#faf8f1;--green:#123f2c;--ink:#080d16;--muted:#5c626d;--line:#ebe7df}
*{box-sizing:border-box}body{margin:0;background:var(--cream);color:var(--ink);font:16px/1.5 Arial,sans-serif}
main{max-width:1700px;margin:auto;padding:32px 24px}h1{font:48px/1.12 Georgia,serif;margin:8px 0 16px}
.intro{max-width:950px}a{color:var(--green)}.eyebrow{color:var(--green);font-weight:bold}
nav{display:flex;flex-wrap:wrap;gap:12px;margin:24px 0}button{border:1px solid var(--line);border-radius:24px;
background:white;padding:12px 24px;font:inherit;cursor:pointer;color:var(--green)}
button[aria-pressed=true]{background:var(--green);color:white}button:focus-visible,a:focus-visible{outline:3px solid #c7861e;outline-offset:4px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:24px;align-items:start}
article{border:1px solid var(--line);border-radius:20px;overflow:hidden;background:white}
article[hidden]{display:none}article header,article footer{padding:18px}
article header span,article header p{color:var(--muted);font-size:13px}
h2{font:24px/1.2 Georgia,serif;margin:8px 0}article header p{margin:0}
img{display:block;width:100%;height:auto;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
summary{cursor:pointer;margin-top:12px}details p{font-size:14px;color:var(--muted)}.note{border:1px solid var(--line);
background:white;padding:16px;border-radius:16px;margin:24px 0}footer.end{margin-top:32px;color:var(--muted)}
</style></head><body><main><div class="intro"><p class="eyebrow">NutriSole · Document coverage · Sep 30, 2026</p>
<h1>The missing screen concepts.</h1>
<p>30 primary concepts: 25 consumer views and five staff views, extending the existing cream and forest-green design.</p>
<p><a href="README.md">Read the full coverage report</a> · <a href="coverage.json">32-requirement mapping</a> ·
<a href="concept-manifest.json">Saved prompts and design briefs</a></p>
<div class="note">These images are proposals for review. The app and Figma have not been updated with these flows.
Secondary error, permission and confirmation states are specified in the coverage report.
Prices are unavailable until verified; records and events shown here are synthetic samples.</div></div>
<nav aria-label="Concept group"><button data-filter="all" aria-pressed="true">All 30</button>
<button data-filter="consumer" aria-pressed="false">Consumer 25</button>
<button data-filter="staff" aria-pressed="false">Staff 5</button></nav>
<div class="grid">""" + "\n".join(cards) + """</div>
<footer class="end">Each PNG opens at full resolution. The screen count groups related requirements; it is not a required route count.</footer>
</main><script>document.querySelectorAll('[data-filter]').forEach(button=>button.addEventListener('click',()=>{
document.querySelectorAll('[data-filter]').forEach(item=>item.setAttribute('aria-pressed',String(item===button)));
document.querySelectorAll('article[data-role]').forEach(card=>card.hidden=button.dataset.filter!=='all'&&card.dataset.role!==button.dataset.filter);
}));</script></body></html>"""
(root / "concept-gallery.html").write_text(page, encoding="utf-8")
coverage_path = root / "coverage.json"
coverage = json.loads(coverage_path.read_text(encoding="utf-8-sig"))
coverage["conceptStatus"] = "generated-reviewed-primary-concepts"
coverage["generatedConceptCount"] = len(index)
coverage["conceptIndex"] = "concept-images.json"
coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"images": len(index), "consumer": sum(x["role"]=="consumer" for x in index),
"staff": sum(x["role"]!="consumer" for x in index), "gallery": str(root / "concept-gallery.html")}))

