"""Give bundled font copies stable names shared by Android and iOS."""
from pathlib import Path
from fontTools.ttLib import TTFont

native = Path(__file__).resolve().parents[1]
for file in (native / "assets" / "fonts").glob("*.ttf"):
    alias = file.stem
    font = TTFont(file)
    for record in font["name"].names:
        if record.nameID in (1, 3, 4, 6, 16):
            record.string = alias.encode(record.getEncoding())
        elif record.nameID in (2, 17):
            record.string = "Regular".encode(record.getEncoding())
    font.save(file)
    target = native / "android" / "app" / "src" / "main" / "assets" / "fonts" / file.name
    target.write_bytes(file.read_bytes())
    print(alias)
