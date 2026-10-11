"""Small helper for reading Woolworths NZ through Scrape.do (home-internet NZ connection).

Woolworths NZ blocks ordinary data-centre connections, so every request uses super=true + geoCode=nz,
which costs 10 Scrape.do credits per successful request (failed requests are free).
"""
import os, time, requests

TOK = os.environ.get("SCRAPEDO_TOKEN", "")
BASE = "https://www.woolworths.co.nz"
HDR = {"sd-x-requested-with": "OnlineShopping.WebApp", "sd-accept": "application/json"}


def credits_left():
    try:
        j = requests.get("https://api.scrape.do/info", params={"token": TOK}, timeout=30).json()
        return int(j.get("RemainingMonthlyRequest"))
    except Exception:
        return None


def get(path, tries=4):
    """GET a Woolworths NZ API path through Scrape.do and return JSON, or None after all tries fail."""
    for i in range(tries):
        try:
            r = requests.get("https://api.scrape.do/", timeout=150, headers=HDR, params={
                "token": TOK, "url": BASE + path, "super": "true", "geoCode": "nz", "extraHeaders": "true"})
            if r.status_code == 200:
                return r.json()
            print(f"  {path.split('?')[0]} -> HTTP {r.status_code} (try {i + 1}): {r.text[:160]!r}")
        except Exception as e:
            print(f"  {path.split('?')[0]} -> {type(e).__name__} (try {i + 1})")
        time.sleep(8 * (i + 1))
    return None
