"""Make background-free product photos for the deals on the page.

For every product in docs/deals.json without docs/img/<code>.png yet: download the Woolworths photo
(free; it comes from Woolworths' image CDN, not through Scrape.do), make the white background
transparent (flood fill from the edges, soft edge), crop to the product and save a small PNG.
"""
import io, json, os, re, sys
from collections import deque
import requests
from PIL import Image

OUT = "docs/img"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
SIZE = 260


def cut(im):
    im = im.convert("RGBA")
    W, H = im.size
    px = im.load()
    seen = bytearray(W * H)
    q = deque()
    for x in range(W):
        q.append((x, 0)); q.append((x, H - 1))
    for y in range(H):
        q.append((0, y)); q.append((W - 1, y))
    white = lambda p: p[0] > 234 and p[1] > 234 and p[2] > 234
    while q:
        x, y = q.popleft()
        i = y * W + x
        if seen[i]:
            continue
        seen[i] = 1
        p = px[x, y]
        if not white(p):
            continue
        px[x, y] = (p[0], p[1], p[2], 0)
        if x > 0: q.append((x - 1, y))
        if x < W - 1: q.append((x + 1, y))
        if y > 0: q.append((x, y - 1))
        if y < H - 1: q.append((x, y + 1))
    # soften the light fringe next to removed pixels
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if p[3] == 0:
                continue
            near = (x > 0 and px[x - 1, y][3] == 0) or (x < W - 1 and px[x + 1, y][3] == 0) or \
                   (y > 0 and px[x, y - 1][3] == 0) or (y < H - 1 and px[x, y + 1][3] == 0)
            if near:
                l = (p[0] + p[1] + p[2]) / 3
                if l > 200:
                    px[x, y] = (p[0], p[1], p[2], max(0, min(255, int((255 - l) * 4))))
    box = im.getchannel("A").point(lambda a: 255 if a > 10 else 0).getbbox()
    if not box:
        raise ValueError("nothing left after removing the background")
    im = im.crop(box)
    im.thumbnail((SIZE, SIZE), Image.LANCZOS)
    return im


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = json.load(open("docs/deals.json")).get("r", [])
    cand = {r["code"]: r for r in json.load(open("data/candidates.json")).get("rows", [])} if os.path.exists("data/candidates.json") else {}
    s = requests.Session(); s.headers["User-Agent"] = UA
    made = failed = 0
    for r in rows:
        code = r[0]
        dest = f"{OUT}/{code}.png"
        if os.path.exists(dest):
            continue
        src = (cand.get(code) or {}).get("image") or (r[16] if len(r) > 16 and str(r[16]).startswith("http") else "")
        if not src:
            continue
        src = re.sub(r"([?&])w=\d+", r"\1w=400", re.sub(r"([?&])h=\d+", r"\1h=400", src))
        try:
            g = s.get(src, timeout=40)
            g.raise_for_status()
            cut(Image.open(io.BytesIO(g.content))).save(dest, optimize=True)
            made += 1
        except Exception as e:
            failed += 1
            print(f"{code}: {type(e).__name__} {str(e)[:120]}")
    print(f"photos made: {made}, failed: {failed}, total on disk: {len(os.listdir(OUT))}")


if __name__ == "__main__":
    main()
