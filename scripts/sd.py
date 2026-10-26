"""Small helper for reading Woolworths NZ through Scrape.do (home-internet NZ connection).

Woolworths NZ blocks ordinary data-centre connections, so every request uses super=true + geoCode=nz,
which costs 10 Scrape.do credits per successful request (failed requests are free).

Two Scrape.do accounts are supported: SCRAPEDO_TOKEN (main) and SCRAPEDO_TOKEN_2 (backup).
Requests use the main account until it runs out of credits, then switch to the backup.
credits_left() reports the total left across both accounts.
"""
import os, time, requests

TOKENS = [t.strip() for t in (os.environ.get("SCRAPEDO_TOKEN", ""), os.environ.get("SCRAPEDO_TOKEN_2", ""))
          if t.strip()]
NAMES = {t: ("main" if i == 0 else "backup") for i, t in enumerate(TOKENS)}
BASE = "https://www.woolworths.co.nz"
HDR = {"sd-x-requested-with": "OnlineShopping.WebApp", "sd-accept": "application/json"}
COST = 10
LAST = {}    # token -> credits left as reported by Scrape.do on the latest successful request
INFO = {}    # token -> credits left as reported by the /info page on the latest check
DEAD = set() # tokens Scrape.do refused (out of credits or invalid) during this run


def _info(tok):
    try:
        j = requests.get("https://api.scrape.do/info", params={"token": tok}, timeout=30).json()
        INFO[tok] = int(j.get("RemainingMonthlyRequest"))
    except Exception:
        pass
    return INFO.get(tok)


def _left(tok):
    """Lowest credit count we know of for one account: the response header beats /info, which can lag."""
    if tok in DEAD:
        return 0
    known = [v for v in (INFO.get(tok), LAST.get(tok)) if v is not None]
    return min(known) if known else None


def credits_left(verbose=False):
    """Total credits left across all accounts (None if no balance could be read)."""
    vals = []
    for tok in TOKENS:
        _info(tok)
        v = _left(tok)
        if verbose:
            print(f"  Scrape.do {NAMES[tok]} account: {v if v is not None else 'unknown'} credits left")
        vals.append(v)
    known = [v for v in vals if v is not None]
    return sum(known) if known else None


def _pick():
    """First account that still has credits for one request (or whose balance is unknown)."""
    for tok in TOKENS:
        v = _left(tok)
        if v is None or v >= COST:
            return tok
    return None


def get(path, tries=4):
    """GET a Woolworths NZ API path through Scrape.do and return JSON, or None after all tries fail."""
    i = 0
    while i < tries:
        tok = _pick()
        if tok is None:
            print("  No Scrape.do account has credits left.")
            return None
        try:
            r = requests.get("https://api.scrape.do/", timeout=150, headers=HDR, params={
                "token": tok, "url": BASE + path, "super": "true", "geoCode": "nz", "extraHeaders": "true"})
            if r.status_code == 200:
                try:
                    LAST[tok] = int(r.headers.get("scrape.do-remaining-credits"))
                except (TypeError, ValueError):
                    pass
                return r.json()
            out = r.status_code in (401, 402) or (r.status_code in (403, 429) and "credit" in r.text.lower())
            if out and tok not in DEAD:
                # Account refused (usually out of credits): switch to the next account without using a try.
                print(f"  {NAMES[tok]} Scrape.do account refused (HTTP {r.status_code}): {r.text[:120]!r}; trying the next account")
                DEAD.add(tok)
                continue
            print(f"  {path.split('?')[0]} -> HTTP {r.status_code} (try {i + 1}): {r.text[:160]!r}")
        except Exception as e:
            print(f"  {path.split('?')[0]} -> {type(e).__name__} (try {i + 1})")
        i += 1
        time.sleep(8 * (i))
    return None
