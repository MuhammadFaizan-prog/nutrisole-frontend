"""Apply the agent review edits (edits.json: per image ok, drop_cells, relabel_cells / relabel_all, grey_cells on a 10x10 grid,
rows A-J top->bottom, cols 0-9 left->right; 'X5!c' = drop all but class c; '*' wildcard) to the teacher proposals and write the
S manifest (labels, licence, uploader, page, url). Usage: build_s.py OUT_manifest.json"""
import json, sys, collections
D = "/workspace/work/cv/g9d"; T = json.load(open(f"{D}/teacher.json")); E = json.load(open(f"{D}/edits.json"))
man = {m["file"]: m for m in json.load(open(f"{D}/commons/manifest.json")).values() if "file" in m}
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
def cell(b): cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2; return "ABCDEFGHIJ"[min(9, int(cy * 10))], str(min(9, int(cx * 10)))
def hit(spec, b):
    r, c = cell(b); s = spec.split("!")[0].split("=")[0]
    if s == "*": return True
    return (s[0] in ("*", r)) and (s[1] in ("*", c))
items = []; stats = collections.Counter(); rej = {}
for k, e in sorted(E.items()):
    if not e.get("ok"): rej[k] = e.get("why"); continue
    f = k + ".jpg"; bs = []
    for b in T[f]["boxes"]:
        b = list(b[:5])
        if any(hit(s, b) and ("!" not in s or b[4] != int(s.split("!")[1])) for s in e.get("drop_cells", [])): continue
        if any(hit(s, b) for s in e.get("grey_cells", [])): continue
        if "relabel_all" in e: b[4] = e["relabel_all"]
        for s in e.get("relabel_cells", []):
            if hit(s, b): b[4] = int(s.split("=")[1])
        bs.append(b)
    grey = [[int(g[1]) / 10, "ABCDEFGHIJ".index(g[0]) / 10, (int(g[1]) + 1) / 10, ("ABCDEFGHIJ".index(g[0]) + 1) / 10] for g in e.get("grey_cells", [])]
    m = man[f]; items.append(dict(id=k, file=f, url=m["url"], page=m["page"], licence=m["licence"], uploader=m["uploader"], artist=m["artist"], W=T[f]["W"], H=T[f]["H"], boxes=bs, grey=grey))
    for b in bs: stats[N[b[4]]] += 1
json.dump(dict(items=items, rejected=rej, box_counts=dict(stats)), open(sys.argv[1], "w"), indent=0)
print(len(items), "accepted", len(rej), "rejected", dict(stats))
