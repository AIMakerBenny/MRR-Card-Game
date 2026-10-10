"""Phase59 - deterministic, offline owner-supplied illustration bundler.

Never invent art. Embed only validated files supplied under assets/card-art.
Public-facing lookup is name + rendered card kind, not hidden game state.
"""
from pathlib import Path
import base64
import csv
import json
import struct

MASTER_SIZE = (1200, 960)
EXTENSIONS = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}

def dimensions(raw, ext):
    if ext == ".png":
        if raw[:8] != b"\x89PNG\r\n\x1a\n" or len(raw) < 24 or raw[12:16] != b"IHDR":
            raise ValueError("invalid PNG header")
        return struct.unpack(">II", raw[16:24])
    if raw[:2] != b"\xff\xd8":
        raise ValueError("invalid JPEG start")
    pos = 2
    while pos + 3 < len(raw):
        if raw[pos] != 0xff:
            raise ValueError("invalid JPEG marker")
        while pos < len(raw) and raw[pos] == 0xff:
            pos += 1
        if pos >= len(raw):
            break
        marker = raw[pos]
        pos += 1
        if marker in (0x01, 0xd8, 0xd9) or 0xd0 <= marker <= 0xd7:
            continue
        if marker == 0xda:
            break
        if pos + 2 > len(raw):
            break
        length = struct.unpack(">H", raw[pos:pos+2])[0]
        if length < 2 or pos + length > len(raw):
            raise ValueError("invalid JPEG segment")
        if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf):
            if length < 7:
                raise ValueError("short JPEG frame")
            height, width = struct.unpack(">HH", raw[pos+3:pos+7])
            return width, height
        pos += length
    raise ValueError("no supported JPEG frame")

def bundle(root, art_dir=None):
    root=Path(root)
    folder=Path(art_dir) if art_dir is not None else root/"assets"/"card-art"
    original=(root/"legacy"/"Phase21_Original.html").read_text("utf-8")
    opening='<script id="card-db" type="application/json">'
    data=json.loads(original.split(opening,1)[1].split("</script>",1)[0])
    cards=data["cards"]
    with (root/"assets"/"card_art_index.csv").open(encoding="utf-8",newline="") as f:
        rows=list(csv.DictReader(f))
    by_id={c["id"]:c for c in cards}
    if len(cards)!=244 or len(rows)!=244 or set(by_id)!={r["card_id"] for r in rows}:
        raise ValueError("card-index and original catalog do not match 244 IDs")
    by_public_key={}
    for c in cards:
        kind=f'{c["type"]} · {("공용" if c.get("source") == "공용" else c["faction"])}'
        key=json.dumps([c["name"],kind],ensure_ascii=False,separators=(",",":"))
        if key in by_public_key:
            raise ValueError("ambiguous visible card key: "+key)
        by_public_key[key]=c["id"]
    artwork={}
    supported=set(by_id)
    if folder.exists():
        for item in sorted(folder.iterdir()):
            if item.is_dir():
                raise ValueError("only files allowed in card-art: "+item.name)
            if item.name == ".gitkeep":
                continue
            ext=item.suffix.lower()
            if ext not in EXTENSIONS or item.stem not in supported:
                raise ValueError("unexpected card image file: "+item.name)
            if item.stem in artwork:
                raise ValueError("more than one image for ID: "+item.stem)
            data_bytes=item.read_bytes()
            if len(data_bytes)>8*1024*1024:
                raise ValueError("card image exceeds 8 MiB: "+item.name)
            actual=dimensions(data_bytes,ext)
            if actual!=MASTER_SIZE:
                raise ValueError(f"{item.name}: expected 1200x960, got {actual[0]}x{actual[1]}")
            artwork[item.stem]="data:"+EXTENSIONS[ext]+";base64,"+base64.b64encode(data_bytes).decode("ascii")
    registry={"byPublicKey":by_public_key,"assets":artwork}
    script="window.MRRCardArtRegistry="+json.dumps(registry,ensure_ascii=False,separators=(",",":"))+";\n"
    if "</script" in script.lower():
        raise ValueError("unsafe inline art registry")
    return script,tuple(sorted(artwork))
