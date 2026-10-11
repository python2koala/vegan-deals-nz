"""One-off test: how many products per request will Woolworths NZ return through Scrape.do?"""
import os, urllib.parse, requests
TOK = os.environ["SCRAPEDO_TOKEN"]
out = []
for size in (500,):
    url = ("https://www.woolworths.co.nz/api/v1/products?target=specials&inStockProductsOnly=false&size=%d&page=1"
           "&sortBy=PRICE_HIGH_LOW&dasFilter=" % size + urllib.parse.quote("PiesAttributes;;Vegan;true"))
    r = requests.get("https://api.scrape.do/", params={"token": TOK, "url": url, "super": "true", "geoCode": "nz", "extraHeaders": "true"},
                     headers={"sd-x-requested-with": "OnlineShopping.WebApp", "sd-accept": "application/json"}, timeout=120)
    try:
        p = r.json().get("products") or {}
        n = len([x for x in p.get("items") or [] if x.get("type") == "Product"])
        out.append(f"size={size}: HTTP {r.status_code}, got {n} products of {p.get('totalItems')}, cost {r.headers.get('scrape.do-request-cost')}")
    except Exception:
        out.append(f"size={size}: HTTP {r.status_code}, {r.text[:300]!r}")
i = requests.get("https://api.scrape.do/info", params={"token": TOK}, timeout=30).json()
out.append(f"Credits left: {i.get('RemainingMonthlyRequest')} of {i.get('MaxMonthlyRequest')}")
print("\n".join(out)); os.makedirs("data", exist_ok=True); open("data/scrapedo-test.txt", "w").write("\n".join(out) + "\n")
