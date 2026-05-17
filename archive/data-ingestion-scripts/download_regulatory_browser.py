"""
Browser-based downloader for regulatory pages that block bots.
Uses Playwright (Chromium) to render and save pages as HTML.
"""

import time
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).parent / "regulatory_downloads"
MANIFEST = []


def save_page(page, url: str, dest: Path, label: str, wait_ms: int = 2000):
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  [SKIP] {label}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "skipped"})
        return
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(wait_ms)
        content = page.content()
        dest.write_text(content, encoding="utf-8")
        size_kb = dest.stat().st_size // 1024
        print(f"  [OK]   {label} ({size_kb} KB)")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "ok", "size_kb": size_kb})
    except Exception as e:
        print(f"  [FAIL] {label} — {e}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": f"failed: {e}"})


def download_pdf_via_browser(page, url: str, dest: Path, label: str):
    """For PDF URLs blocked by 403 — navigate to the page and trigger download."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  [SKIP] {label}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "skipped"})
        return
    try:
        import requests
        # Use session cookies from browser context to fetch the PDF
        cookies = page.context.cookies()
        session = requests.Session()
        for c in cookies:
            session.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
        session.headers.update({
            "User-Agent": page.evaluate("navigator.userAgent"),
            "Referer": url,
        })
        r = session.get(url, timeout=30, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        size_kb = dest.stat().st_size // 1024
        print(f"  [OK]   {label} ({size_kb} KB)")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "ok", "size_kb": size_kb})
    except Exception as e:
        print(f"  [FAIL] {label} — {e}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": f"failed: {e}"})


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()

        # ── SEC Pages ─────────────────────────────────────────────────
        print("\n=== SEC Pages ===")
        sec_docs = [
            ("SEC Regulation SHO Short Selling",
             "https://www.sec.gov/divisions/marketreg/mrfaqregsho1204.htm",
             BASE_DIR / "us/markets/SEC_Reg_SHO.html"),
            ("SEC Regulation Best Interest (Reg BI)",
             "https://www.sec.gov/info/smallbus/secg/regulation-best-interest",
             BASE_DIR / "us/markets/SEC_Reg_BI.html"),
            ("SEC Investment Advisers Act",
             "https://www.sec.gov/divisions/investment/adviserinfo.htm",
             BASE_DIR / "us/markets/SEC_Advisers_Act.html"),
        ]
        for label, url, dest in sec_docs:
            save_page(page, url, dest, label)
            time.sleep(1)

        # ── FASB ASC 326 ───────────────────────────────────────────────
        print("\n=== FASB ===")
        save_page(page,
                  "https://asc.fasb.org/326",
                  BASE_DIR / "us/aml/FASB_ASC326_CECL.html",
                  "FASB ASC 326 CECL",
                  wait_ms=3000)

        # ── CIRO Rules ─────────────────────────────────────────────────
        print("\n=== CIRO ===")
        save_page(page,
                  "https://www.ciro.ca/rules-and-enforcement/current-rules",
                  BASE_DIR / "canada/other/CIRO_Rules.html",
                  "CIRO Rules and Enforcement",
                  wait_ms=2000)

        # ── OSFI B-6 & E-21 (search the guidance library) ─────────────
        print("\n=== OSFI B-6 & E-21 ===")

        # Load guidance library and search for B-6
        page.goto("https://www.osfi-bsif.gc.ca/en/guidance/guidance-library", wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(1500)

        # Try to find B-6 via search
        b6_candidates = [
            ("OSFI B-6 Liquidity Principles",
             "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/guideline-b-6",
             BASE_DIR / "osfi/guidelines/OSFI_B-6_Liquidity_Principles.html"),
            ("OSFI B-6 Liquidity Principles (alt)",
             "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/b-6-liquidity-principles",
             BASE_DIR / "osfi/guidelines/OSFI_B-6_Liquidity_Principles.html"),
        ]
        for label, url, dest in b6_candidates:
            if dest.exists():
                break
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=15000)
                status = page.evaluate("document.title")
                content = page.content()
                if "404" not in status and "not found" not in status.lower() and len(content) > 5000:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_text(content, encoding="utf-8")
                    print(f"  [OK]   {label} ({dest.stat().st_size//1024} KB)")
                    MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "ok"})
                    break
            except Exception:
                pass

        # OSFI search for B-6 text
        if not (BASE_DIR / "osfi/guidelines/OSFI_B-6_Liquidity_Principles.html").exists():
            try:
                page.goto("https://www.osfi-bsif.gc.ca/en/guidance/guidance-library?q=B-6+liquidity", wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(1500)
                # Find first matching link
                links = page.query_selector_all("a[href*='guidance-library']")
                for link in links:
                    text = link.inner_text().lower()
                    if "b-6" in text or "liquidity principles" in text:
                        href = link.get_attribute("href")
                        full_url = "https://www.osfi-bsif.gc.ca" + href if href.startswith("/") else href
                        save_page(page, full_url,
                                  BASE_DIR / "osfi/guidelines/OSFI_B-6_Liquidity_Principles.html",
                                  "OSFI B-6 Liquidity Principles")
                        break
            except Exception as e:
                print(f"  [FAIL] OSFI B-6 search — {e}")
                MANIFEST.append({"label": "OSFI B-6 Liquidity Principles", "url": "", "file": "", "status": f"not_found: {e}"})

        # OSFI E-21
        e21_url = "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library?q=E-21+operational+risk"
        try:
            page.goto(e21_url, wait_until="networkidle", timeout=20000)
            page.wait_for_timeout(1500)
            links = page.query_selector_all("a[href*='guidance-library']")
            found_e21 = False
            for link in links:
                text = link.inner_text().lower()
                if "e-21" in text or ("operational risk" in text and "resilience" in text):
                    href = link.get_attribute("href")
                    full_url = "https://www.osfi-bsif.gc.ca" + href if href.startswith("/") else href
                    save_page(page, full_url,
                              BASE_DIR / "osfi/guidelines/OSFI_E-21_Operational_Risk.html",
                              "OSFI E-21 Operational Risk Resilience")
                    found_e21 = True
                    break
            if not found_e21:
                print("  [FAIL] OSFI E-21 — not found in search results")
                MANIFEST.append({"label": "OSFI E-21", "url": e21_url, "file": "", "status": "not_found"})
        except Exception as e:
            print(f"  [FAIL] OSFI E-21 search — {e}")
            MANIFEST.append({"label": "OSFI E-21", "url": e21_url, "file": "", "status": f"failed: {e}"})

        browser.close()

    # Update manifest
    existing_path = BASE_DIR / "download_manifest.json"
    existing = json.loads(existing_path.read_text()) if existing_path.exists() else {"results": []}
    all_results = existing.get("results", []) + MANIFEST
    all_ok = [m for m in all_results if m["status"] == "ok"]
    all_failed = [m for m in all_results if m["status"] not in ("ok", "skipped")]

    with open(existing_path, "w") as f:
        json.dump({
            "summary": {
                "ok": len(all_ok),
                "skipped": len([m for m in all_results if m["status"] == "skipped"]),
                "failed": len(all_failed),
            },
            "results": all_results,
        }, f, indent=2)

    ok = [m for m in MANIFEST if m["status"] == "ok"]
    failed = [m for m in MANIFEST if m["status"] not in ("ok", "skipped")]
    print(f"\n{'='*60}")
    print(f"Browser run done — Downloaded: {len(ok)}  |  Failed: {len(failed)}")
    print(f"Total across all runs — OK: {len(all_ok)}  |  Failed: {len(all_failed)}")
    if failed:
        print("\nStill failing:")
        for m in failed:
            print(f"  - {m['label']}: {m['status']}")


if __name__ == "__main__":
    run()
