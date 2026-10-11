"""Fetch Woolworths NZ product details (ingredients, pack claims, may-contain) for the codes listed in
data/details-wanted.json, and keep them in data/details.json (a cache, reused in later weeks).

Each product costs ~10 Scrape.do credits, so this only runs for products the vegan check could not settle
from the manufacturer or trusted sites. It always keeps RESERVE credits back for the weekly list.
"""
import datetime as dt, json, os, re
from sd import get, credits_left

RESERVE = 300          # enough for ~4 weekly list runs
MAX_PER_RUN = 25
WANT, CACHE = "data/details-wanted.json", "data/details.json"


def text_of(v):
    if v is None:
        return ""
    if isinstance(v, str):
        return v
    if isinstance(v, list):
        return " ".join(text_of(x) for x in v)
    if isinstance(v, dict):
        return " ".join(text_of(x) for x in v.values())
    return str(v)


def main():
    want = json.load(open(WANT)).get("codes", []) if os.path.exists(WANT) else []
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    todo = [c for c in dict.fromkeys(map(str, want)) if c not in cache][:MAX_PER_RUN]
    left = credits_left()
    print(f"{len(todo)} products need details; Scrape.do credits left: {left}")
    if left is None:
        print("Cannot read the Scrape.do credit balance; fetching nothing to be safe.")
        todo, held0 = [], list(dict.fromkeys(map(str, want)))
    else:
        held0 = []
    done, held = 0, held0
    for code in todo:
        if left - 10 < RESERVE:
            held.append(code); continue
        d = get(f"/api/v1/products/{code}")
        if d is None:
            held.append(code); continue
        left = min(left - 10, credits_left() or left - 10)
        desc = re.sub(r"<[^>]+>", " ", text_of(d.get("description")))
        claims = [text_of(c).strip() for c in (d.get("claims") or []) + (d.get("endorsements") or []) if text_of(c).strip()]
        ing = d.get("ingredients") or {}
        cache[code] = {
            "name": d.get("name") or "", "brand": d.get("brand") or "",
            "ingredients": text_of(ing.get("ingredients") if isinstance(ing, dict) else ing).strip(),
            "mayContain": text_of(d.get("allergenMaybePresent")).strip(),
            "allergens": text_of(d.get("allergens")).strip(),
            "packClaim": "; ".join(claims),
            "descriptionVegan": sorted({m.group(0).strip() for m in re.finditer(r"[^.\n]{0,70}\bvegan\w*[^.\n]{0,50}", desc, re.I)})[:3],
            "fetched": dt.date.today().isoformat(),
        }
        done += 1
    json.dump(cache, open(CACHE, "w"), indent=1, ensure_ascii=False, sort_keys=True)
    json.dump({"codes": held, "note": "Held back to protect the weekly list credits, or failed; retried next run."},
              open(WANT, "w"), indent=1)
    print(f"Fetched details for {done}; {len(held)} held for later; credits left: {credits_left()}")


if __name__ == "__main__":
    main()
