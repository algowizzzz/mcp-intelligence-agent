"""
Canadian Bank IR Downloader — Playwright-native version.
Uses the browser for navigation AND downloads (no requests session).
Converts PDF→MD on the fly, deletes raw files to save disk.
"""

import re, json, time
from pathlib import Path
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright, Page, BrowserContext
from pypdf import PdfReader
import html2text as _ht
import requests as _req

BASE   = Path(__file__).parent / "bank_filings" / "canada"
MFILE  = Path(__file__).parent / "bank_filings" / "ca_ir_manifest.json"
YEARS  = set(str(y) for y in range(2020, 2026))
UA     = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
LOG: list[dict] = []

# ── converters ────────────────────────────────────────────────────────────────
_h = _ht.HTML2Text()
_h.ignore_images = True; _h.body_width = 0; _h.unicode_snob = True

def _clean(t): return re.sub(r'\n{4,}', '\n\n\n', t).strip() + '\n'

def pdf_to_md(p: Path) -> str:
    try:
        pages = []
        for i, pg in enumerate(PdfReader(str(p)).pages, 1):
            t = (pg.extract_text() or "").strip()
            if t: pages.append(f"<!-- p{i} -->\n\n{t}")
        return _clean("\n\n---\n\n".join(pages)) if pages else "# (empty PDF)\n"
    except Exception as e:
        return f"# PDF parse error\n\n{e}\n"

def html_to_md(html: str) -> str:
    return _clean(_h.handle(html))

def slug(s: str) -> str:
    return re.sub(r'[^\w\-]', '_', s.strip())[:80].strip('_')

# ── navigation ────────────────────────────────────────────────────────────────
def go(page: Page, url: str, wait=2000):
    for strategy in ("domcontentloaded", "load"):
        try:
            page.goto(url, wait_until=strategy, timeout=20000)
            page.wait_for_timeout(wait)
            return True
        except Exception:
            pass
    print(f"    [TIMEOUT] {url}")
    return False

# ── download a PDF via requests (direct URL — no browser needed) ──────────────
_sess = _req.Session()
_sess.headers.update({"User-Agent": UA, "Accept": "application/pdf,*/*"})

def dl_pdf(ctx: BrowserContext, url: str, dest: Path, label: str) -> bool:
    md = dest.with_suffix(".md")
    if md.exists() and md.stat().st_size > 2000:
        print(f"    [SKIP] {label}")
        LOG.append({"label": label, "url": url, "file": str(md), "status": "skipped"})
        return True

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    try:
        r = _sess.get(url, timeout=60, stream=True)
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)

        md.write_text(pdf_to_md(tmp), encoding="utf-8")
        tmp.unlink(missing_ok=True)

        kb = md.stat().st_size // 1024
        print(f"    [OK]   {label} ({kb} KB md)")
        LOG.append({"label": label, "url": url, "file": str(md), "status": "ok",
                    "size_kb": kb, "at": datetime.now(timezone.utc).isoformat()})
        return True
    except Exception as e:
        tmp.unlink(missing_ok=True)
        print(f"    [FAIL] {label} — {e}")
        LOG.append({"label": label, "url": url, "file": str(dest), "status": f"failed: {e}"})
        return False

# ── collect all PDF hrefs on current page ─────────────────────────────────────
def pdf_links(page: Page) -> list[tuple[str, str]]:
    try:
        raw = page.evaluate("""() =>
            Array.from(document.querySelectorAll('a[href]'))
              .map(a => ({t: (a.innerText||a.title||'').trim(), h: a.href}))
        """)
        return [(r["t"], r["h"]) for r in raw if ".pdf" in r["h"].lower()]
    except Exception:
        return []

def in_range(text: str, href: str) -> bool:
    combined = (text + href).lower()
    return any(y in combined for y in YEARS)

def save_links(page: Page, ctx: BrowserContext, ticker: str, cat: str, prefix: str):
    links = [(t, h) for t, h in pdf_links(page) if in_range(t, h)]
    print(f"    → {len(links)} in-range PDFs")
    for text, href in links:
        fname = slug(text or href.split("/")[-1].replace(".pdf", ""))
        dest  = BASE / ticker / "ir" / cat / f"{fname}.pdf"
        dl_pdf(ctx, href, dest, f"{prefix} | {text[:55]}")
        time.sleep(0.4)
    return len(links)


# ── bank scrapers ─────────────────────────────────────────────────────────────

def rbc(page: Page, ctx: BrowserContext):
    print("\n=== RBC ===")
    go(page, "https://www.rbc.com/investor-relations/financial-information.html", wait=3000)
    # Expand year accordions
    for btn in page.query_selector_all("button")[:40]:
        try: btn.click(); page.wait_for_timeout(150)
        except: pass
    page.wait_for_timeout(1000)
    n = save_links(page, ctx, "ry", "annual", "RBC Annual")
    if n == 0:
        # Fallback: direct quarterly page
        go(page, "https://www.rbc.com/investor-relations/quarterly-results.html", wait=2000)
        save_links(page, ctx, "ry", "quarterly", "RBC Quarterly")


def td(page: Page, ctx: BrowserContext):
    print("\n=== TD ===")
    for cat, url in [
        ("annual",    "https://www.td.com/ca/en/about-td/for-investors/investor-relations/financial-information/financial-reports/annual-reports"),
        ("quarterly", "https://www.td.com/ca/en/about-td/for-investors/investor-relations/financial-information/financial-reports/quarterly-results"),
    ]:
        print(f"  {cat}...")
        go(page, url, wait=3000)
        save_links(page, ctx, "td", cat, f"TD {cat.title()}")


def bns(page: Page, ctx: BrowserContext):
    print("\n=== Scotiabank ===")
    for cat, url in [
        ("annual",    "https://www.scotiabank.com/ca/en/about/investors-shareholders/annual-reports.html"),
        ("quarterly", "https://www.scotiabank.com/ca/en/about/investors-shareholders/quarterly-results.html"),
    ]:
        print(f"  {cat}...")
        go(page, url, wait=3000)
        # click load-more up to 6 times for quarterly history
        for _ in range(6):
            btn = page.query_selector("button:has-text('Load'), button:has-text('Show more')")
            if btn:
                try: btn.click(); page.wait_for_timeout(1200)
                except: break
            else: break
        save_links(page, ctx, "bns", cat, f"BNS {cat.title()}")


def bmo(page: Page, ctx: BrowserContext):
    print("\n=== BMO ===")
    for cat, url in [
        ("annual",    "https://www.bmo.com/en-ca/main/about-bmo/investor-relations/annual-reports/"),
        ("quarterly", "https://www.bmo.com/en-ca/main/about-bmo/investor-relations/quarterly-results/"),
        # fallback IR portal
        ("annual",    "https://ir.bmo.com/financial-information/annual-reports/default.aspx"),
        ("quarterly", "https://ir.bmo.com/financial-information/quarterly-results/default.aspx"),
    ]:
        print(f"  trying {url[:60]}...")
        if go(page, url, wait=3000):
            n = save_links(page, ctx, "bmo", cat, f"BMO {cat.title()}")
            if n > 0:
                break   # got results, skip fallback


def cibc(page: Page, ctx: BrowserContext):
    print("\n=== CIBC ===")
    for cat, url in [
        ("annual",    "https://www.cibc.com/en/about-cibc/investor-relations/annual-reports-and-proxy-circulars.html"),
        ("quarterly", "https://www.cibc.com/en/about-cibc/investor-relations/quarterly-results.html"),
    ]:
        print(f"  {cat}...")
        go(page, url, wait=3000)
        save_links(page, ctx, "cm", cat, f"CIBC {cat.title()}")


def na(page: Page, ctx: BrowserContext):
    print("\n=== National Bank ===")
    # Try direct PDF URLs first
    for year in sorted(YEARS):
        yr = int(year)
        for label, url in [
            (f"NA Annual Report {yr}",
             f"https://www.nbc.ca/content/dam/bnc/a-propos-de-nous/relations-investisseurs/assemblee-annuelle/{yr+1}/na-annual-report-{yr}.pdf"),
            (f"NA Annual Report {yr} (alt)",
             f"https://www.nbc.ca/content/dam/bnc/a-propos-de-nous/relations-investisseurs/assemblee-annuelle/{yr}/na-annual-report-{yr}.pdf"),
        ]:
            dest = BASE / "na" / "ir" / "annual" / f"NA_Annual_{yr}.pdf"
            if dl_pdf(ctx, url, dest, label):
                break
        time.sleep(0.5)

    # Scrape IR pages for quarterly
    for cat, url in [
        ("quarterly", "https://www.nbc.ca/en/about-us/investors/quarterly-results.html"),
        ("annual",    "https://www.nbc.ca/en/about-us/investors/archives.html"),
    ]:
        print(f"  {cat}...")
        go(page, url, wait=3000)
        save_links(page, ctx, "na", cat, f"NA {cat.title()}")


# ── manifest ──────────────────────────────────────────────────────────────────
def save_manifest():
    ok  = sum(1 for l in LOG if l["status"] == "ok")
    fail= sum(1 for l in LOG if l["status"].startswith("failed"))
    skip= sum(1 for l in LOG if l["status"] in ("skipped", "too_large"))
    MFILE.write_text(json.dumps({
        "generated": datetime.now(timezone.utc).isoformat(),
        "summary": {"ok": ok, "failed": fail, "skipped": skip},
        "files": LOG,
    }, indent=2))
    print(f"\n  ✓ {ok} downloaded  ✗ {fail} failed  — {MFILE.name} updated")


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx     = browser.new_context(
            user_agent=UA,
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
        )
        page = ctx.new_page()
        page.set_default_timeout(20000)

        rbc(page, ctx);  save_manifest()
        td(page, ctx);   save_manifest()
        bns(page, ctx);  save_manifest()
        bmo(page, ctx);  save_manifest()
        cibc(page, ctx); save_manifest()
        na(page, ctx);   save_manifest()

        browser.close()

    ok   = sum(1 for l in LOG if l["status"] == "ok")
    fail = sum(1 for l in LOG if l["status"].startswith("failed"))
    print(f"\n{'='*60}")
    print(f"DONE — Downloaded: {ok}  Failed: {fail}")
    print(f"Files: {BASE}")


if __name__ == "__main__":
    main()
