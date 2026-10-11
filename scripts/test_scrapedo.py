"""One-off test: can Scrape.do read Woolworths NZ's vegan specials, and how many credits does it cost?

Tries the cheapest route first and stops at the first one that works. Never prints the token.
Writes data/scrapedo-test.txt.
"""
import json, os, urllib.parse, requests

TOK = os.environ["SCRAPEDO_TOKEN"]
LIST = ("https://www.woolworths.co.nz/api/v1/products?target=specials&inStockProductsOnly=false&size=48&page=1"
        "&sortBy=PRICE_HIGH_LOW&dasFilter=" + urllib.parse.quote("PiesAttributes;;Vegan;true"))
DETAIL = "https://www.woolworths.co.nz/api/v1/products/{sku}"
HDR = {"x-requested-with": "OnlineShopping.WebApp", "accept": "application/json"}
ROUTES = [
    ("plain, headers as extras", {"extraHeaders": "true"}),
    ("residential NZ, headers as extras", {"super": "true", "geoCode": "nz", "extraHeaders": "true"}),
    ("residential NZ, no extra headers", {"super": "true", "geoCode": "nz", "noHeaders": True}),
    ("residential NZ, real browser", {"super": "true", "geoCode": "nz", "render": "true", "noHeaders": True}),
]
out = []


def say(s):
    out.append(s); print(s)


def credits():
    try:
        r = requests.get("https://api.scrape.do/info", params={"token": TOK}, timeout=30)
        j = r.json()
        return {k: v for k, v in j.items() if "request" in k.lower() or "credit" in k.lower() or "concurren" in k.lower()}
    except Exception as e:
        return f"unavailable ({type(e).__name__})"


def ask(url, extra):
    extra = dict(extra)
    bare = extra.pop("noHeaders", False)
    p = {"token": TOK, "url": url, **extra}
    if bare:
        h = {}
    elif extra.get("extraHeaders"):
        h = {"sd-" + k: v for k, v in HDR.items()}
    else:
        p["customHeaders"] = "true"; h = HDR
    r = requests.get("https://api.scrape.do/", params=p, headers=h, timeout=120)
    cost = {k: v for k, v in r.headers.items() if k.lower().startswith("scrape.do")}
    return r, cost


say(f"Credits before: {credits()}")
ok = None
for name, extra in ROUTES:
    try:
        r, cost = ask(LIST, extra)
    except Exception as e:
        say(f"[{name}] error: {type(e).__name__}"); continue
    good = False
    try:
        j = r.json(); prods = j.get("products") or {}
        items = [x for x in prods.get("items") or [] if x.get("type") == "Product"]
        good = r.status_code == 200 and len(items) > 0
    except Exception:
        items, prods = [], {}
    say(f"[{name}] HTTP {r.status_code}; products on page 1: {len(items)}; total vegan specials: {prods.get('totalItems')}; "
        f"cost: {cost.get('scrape.do-request-cost')}; reply: {r.text[:700]!r}")
    if good:
        ok = (name, extra, items)
        break

if ok:
    name, extra, items = ok
    it = items[0]
    p = it.get("price") or {}
    say(f"Sample: {it.get('name')} | ${p.get('salePrice')} (was ${p.get('originalPrice')})")
    r, cost = ask(DETAIL.format(sku=it["sku"]), extra)
    try:
        d = r.json()
        say(f"[{name}] product page HTTP {r.status_code}; has ingredients: {bool(d.get('ingredients'))}; "
            f"has claims: {bool(d.get('claims'))}; offer runs {(d.get('price') or {}).get('promotionStartDate')} to "
            f"{(d.get('price') or {}).get('promotionEndDate')}; cost headers: {cost}")
    except Exception:
        say(f"[{name}] product page HTTP {r.status_code}; start of reply: {r.text[:120]!r}")
    say(f"RESULT: works via '{name}'")
else:
    say("RESULT: no route worked")
say(f"Credits after: {credits()}")
os.makedirs("data", exist_ok=True)
open("data/scrapedo-test.txt", "w").write("\n".join(out) + "\n")
