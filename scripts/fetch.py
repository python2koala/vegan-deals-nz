"""Weekly NZ fetch: this week's Woolworths NZ vegan-tagged specials that are 30%+ off.

Source (the owner's link, highest price first):
  https://www.woolworths.co.nz/specials-offers?page=1&dietary=isVegan&staticFilters=SPECIALS&sortBy=PRICE_HIGH_LOW
Woolworths NZ specials run Monday to the following Sunday (NZ time).

Reads only the product LIST (about 7 requests = ~70 Scrape.do credits). Product details (ingredients,
pack claims) are fetched separately and only when the vegan check asks for them (scripts/details.py).
Writes data/candidates.json. Never decides vegan status.
Skips if this week's candidates already exist, unless FORCE=1.
"""
import datetime as dt, json, os, sys, urllib.parse, zoneinfo
from sd import get, credits_left

SOURCE = "https://www.woolworths.co.nz/specials-offers?page=1&dietary=isVegan&staticFilters=SPECIALS&sortBy=PRICE_HIGH_LOW"
MIN_DISCOUNT = 30
PAGE_SIZE = 120  # the most Woolworths NZ allows per request
AKL = zoneinfo.ZoneInfo("Pacific/Auckland")
OUT = "data/candidates.json"


def main():
    now = dt.datetime.now(AKL)
    mon = now.date() - dt.timedelta(days=now.weekday())
    week = {"from": mon.isoformat(), "to": (mon + dt.timedelta(days=6)).isoformat()}
    if os.environ.get("FORCE") != "1" and os.path.exists(OUT):
        if json.load(open(OUT)).get("week", {}).get("from") == week["from"]:
            print("This week's NZ candidates already fetched; nothing to do."); return
    if now.weekday() == 0 and now.hour < 6:
        print("Too early on Monday (NZ); new specials may not be live yet."); return

    before = credits_left()
    print(f"Scrape.do credits left: {before}")
    if before is not None and before < 80:
        sys.exit("Not enough Scrape.do credits left this month for the weekly list.")

    flt = urllib.parse.quote("PiesAttributes;;Vegan;true")
    items, total = [], None
    for page in range(1, 15):
        j = get(f"/api/v1/products?target=specials&inStockProductsOnly=false&size={PAGE_SIZE}&page={page}"
                f"&sortBy=PRICE_HIGH_LOW&dasFilter={flt}")
        if j is None:
            sys.exit(f"Could not read page {page} of the Woolworths NZ list.")
        prods = j.get("products") or {}
        got = [x for x in prods.get("items") or [] if x.get("type") == "Product"]
        total = prods.get("totalItems") or 0
        items += got
        print(f"page {page}: {len(got)} products ({len(items)} of {total})")
        if not got or len(items) >= total:
            break
    if not items:
        sys.exit("Woolworths NZ returned no vegan specials.")

    seen, rows, skipped = set(), [], {"no_price": 0, "under_min": 0, "out_of_stock": 0}
    for it in items:
        sku = str(it.get("sku") or "").strip()
        if not sku or sku in seen:
            continue
        seen.add(sku)
        p = it.get("price") or {}
        now_p, was_p = p.get("salePrice"), p.get("originalPrice")
        if not now_p or not was_p or was_p <= now_p:
            skipped["no_price"] += 1; continue
        pct = round((1 - now_p / was_p) * 100)
        if pct < MIN_DISCOUNT:
            skipped["under_min"] += 1; continue
        if (it.get("availabilityStatus") or "").lower() == "out of stock":
            skipped["out_of_stock"] += 1; continue
        img = (it.get("images") or {})
        rows.append({
            "code": sku, "slug": it.get("slug") or "",
            "name": " ".join((it.get("name") or "").split()),
            "brand": " ".join((it.get("brand") or "").split()),
            "size": ((it.get("size") or {}).get("volumeSize") or "").strip(),
            "now": now_p, "was": was_p, "pct": pct, "half": 1 if pct >= 50 else 0,
            "department": ((it.get("departments") or [{}])[0] or {}).get("name") or "",
            "image": (img.get("big") or img.get("small") or "") if isinstance(img, dict) else "",
        })
    rows.sort(key=lambda x: -x["now"])
    after = credits_left()
    out = {"week": week, "fetched": now.isoformat(timespec="minutes"), "listed": len(items), "siteTotal": total,
           "skipped": skipped, "minDiscount": MIN_DISCOUNT, "source": SOURCE,
           "credits": {"before": before, "after": after}, "rows": rows}
    os.makedirs("data", exist_ok=True)
    json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)
    print(f"{len(items)} listed, {len(rows)} candidates at {MIN_DISCOUNT}%+ off; skipped {skipped}; "
          f"week {week}; credits {before} -> {after}")


if __name__ == "__main__":
    main()
