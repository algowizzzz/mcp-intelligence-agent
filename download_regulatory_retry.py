"""
Retry script for failed regulatory downloads — uses corrected URLs.
Picks up where download_regulatory_data.py left off.
"""

import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent / "regulatory_downloads"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
MANIFEST = []


def download_pdf(url, dest, label):
    dest = Path(dest)
    if dest.exists():
        print(f"  [SKIP] {label}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "skipped"})
        return
    try:
        r = SESSION.get(url, timeout=30, stream=True)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        size_kb = dest.stat().st_size // 1024
        print(f"  [OK]   {label} ({size_kb} KB)")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "ok", "size_kb": size_kb})
    except Exception as e:
        print(f"  [FAIL] {label} — {e}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": f"failed: {e}"})


def save_html(url, dest, label):
    dest = Path(dest)
    if dest.exists():
        print(f"  [SKIP] {label}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "skipped"})
        return
    try:
        r = SESSION.get(url, timeout=30)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(r.text, encoding="utf-8")
        size_kb = dest.stat().st_size // 1024
        print(f"  [OK]   {label} ({size_kb} KB)")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "ok", "size_kb": size_kb})
    except Exception as e:
        print(f"  [FAIL] {label} — {e}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": f"failed: {e}"})


# ─────────────────────────────────────────────
# 1. OSFI CAR 2026 — Direct PDF URLs (discovered via scraping)
# ─────────────────────────────────────────────
def download_osfi_car_2026():
    folder = BASE_DIR / "osfi" / "car"
    folder.mkdir(parents=True, exist_ok=True)
    print("\n=== OSFI CAR 2026 — Chapter PDFs ===")

    chapters = [
        ("CAR 2026 Ch1 Overview",           "2026-car-nfp-chap1-en.pdf"),
        ("CAR 2026 Ch2 Definition of Capital", "2026-car-nfp-chap2-en.pdf"),
        ("CAR 2026 Ch3 Operational Risk",    "2026-car-nfp-chap3-en.pdf"),
        ("CAR 2026 Ch4 Credit Risk Standardized", "2026-car-nfp-chap4-en.pdf"),
        ("CAR 2026 Ch5 Credit Risk IRB",     "2026-car-nfp-chap5-en.pdf"),
        ("CAR 2026 Ch6 Securitization",      "2026-car-nfp-chap6-en.pdf"),
        ("CAR 2026 Ch7 Settlement & CCR SA-CCR", "2026-car-nfp-chap7-en.pdf"),
        ("CAR 2026 Ch8 CVA Risk",            "2026-car-nfp-chap8-en.pdf"),
        ("CAR 2026 Ch9 Market Risk FRTB",    "2026-car-nfp-chap9-en.pdf"),
    ]

    base_url = "https://www.osfi-bsif.gc.ca/sites/default/files/documents/"
    for label, fname in chapters:
        download_pdf(base_url + fname, folder / f"OSFI_{fname}", label)
        time.sleep(0.4)


# ─────────────────────────────────────────────
# 2. OSFI LAR 2026 — Chapters with known PDFs
# ─────────────────────────────────────────────
def download_osfi_lar_2026():
    folder = BASE_DIR / "osfi" / "lar"
    folder.mkdir(parents=True, exist_ok=True)
    print("\n=== OSFI LAR 2026 — Chapter PDFs ===")

    chapters = [
        ("LAR 2026 Ch2 LCR",    "https://www.osfi-bsif.gc.ca/sites/default/files/documents/2026-lar-nl-chpt-2-en.pdf"),
        ("LAR 2026 Ch3 NSFR",   "https://www.osfi-bsif.gc.ca/sites/default/files/documents/2026-lar-nl-chpt-3-en.pdf"),
        ("LAR 2026 Ch4 Net Cumulative Cash Flow", "https://www.osfi-bsif.gc.ca/sites/default/files/documents/2026-lar-nl-chpt-4-en.pdf"),
    ]

    # Chapters 1,5,6,7 had no PDF — save their index pages as HTML
    html_chapters = [
        ("LAR 2026 Ch1 Overview",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/liquidity-adequacy-requirements-lar-2026-chapter-1-overview",
         "OSFI_LAR_2026_Ch1_Overview.html"),
        ("LAR 2026 Ch5 Operating Cash Flows",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/liquidity-adequacy-requirements-lar-2026-chapter-5-operating-cash-flows",
         "OSFI_LAR_2026_Ch5_OperatingCashFlows.html"),
        ("LAR 2026 Ch6 Liquidity Monitoring Tools",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/liquidity-adequacy-requirements-lar-2026-chapter-6-liquidity-monitoring-tools",
         "OSFI_LAR_2026_Ch6_LiquidityMonitoring.html"),
        ("LAR 2026 Ch7 Intraday Liquidity",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/liquidity-adequacy-requirements-lar-2026-chapter-7-intraday-liquidity-management",
         "OSFI_LAR_2026_Ch7_IntradayLiquidity.html"),
    ]

    for label, url in chapters:
        fname = url.split("/")[-1]
        download_pdf(url, folder / f"OSFI_{fname}", label)
        time.sleep(0.4)

    for label, url, fname in html_chapters:
        save_html(url, folder / fname, label)
        time.sleep(0.4)


# ─────────────────────────────────────────────
# 3. OSFI Guidelines — corrected URLs
# ─────────────────────────────────────────────
def download_osfi_guidelines_retry():
    folder = BASE_DIR / "osfi" / "guidelines"
    folder.mkdir(parents=True, exist_ok=True)
    print("\n=== OSFI Guidelines — Retry with corrected URLs ===")

    docs = [
        ("OSFI E-23 Model Risk Management 2027",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/guideline-e-23-model-risk-management-2027",
         "OSFI_E-23_Model_Risk_2027.html"),
        ("OSFI Corporate Governance Guideline",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/corporate-governance",
         "OSFI_Corporate_Governance.html"),
        ("OSFI E-21 Operational Risk Resilience",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/guideline-e-21-operational-risk-resilience",
         "OSFI_E-21_Operational_Risk.html"),
        ("OSFI B-6 Liquidity Principles",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/guideline-b-6-liquidity-principles-deposit-taking-institutions",
         "OSFI_B-6_Liquidity_Principles.html"),
        ("OSFI DSB Dec 2025 Announcement",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/osfi-maintains-level-domestic-stability-buffer-35-letter-december-2025",
         "OSFI_DSB_Dec2025.html"),
        ("OSFI DSB Jun 2025 Announcement",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/osfi-maintains-level-domestic-stability-buffer-350-letter-june-2025",
         "OSFI_DSB_Jun2025.html"),
    ]

    for label, url, fname in docs:
        save_html(url, folder / fname, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# 4. Federal Reserve — corrected URLs
# ─────────────────────────────────────────────
def download_fed_retry():
    folder = BASE_DIR / "us" / "federal_reserve"
    folder.mkdir(parents=True, exist_ok=True)
    print("\n=== Federal Reserve — Retry with corrected URLs ===")

    docs = [
        # SR 99-18 moved - try alternate
        ("Fed SR 99-18 Counterparty Credit Risk",
         "https://www.federalreserve.gov/boarddocs/srletters/1999/sr9918.htm",
         "Fed_SR99-18_CCR.html"),
        # Reg YY — use eCFR
        ("Federal Regulation YY Enhanced Prudential Standards (eCFR)",
         "https://www.ecfr.gov/current/title-12/part-252",
         "Fed_Reg_YY_eCFR.html"),
        # Reg W — use eCFR
        ("Federal Regulation W Transactions with Affiliates (eCFR)",
         "https://www.ecfr.gov/current/title-12/part-223",
         "Fed_Reg_W_eCFR.html"),
        # CCAR — corrected page
        ("CCAR Stress Test Policies",
         "https://www.federalreserve.gov/supervisionreg/stress-tests-capital-planning.htm",
         "Fed_CCAR_Index.html"),
    ]

    for label, url, fname in docs:
        save_html(url, folder / fname, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# 5. FinCEN BSA — corrected URL
# ─────────────────────────────────────────────
def download_fincen_retry():
    folder = BASE_DIR / "us" / "aml"
    folder.mkdir(parents=True, exist_ok=True)
    print("\n=== FinCEN / AML — Retry ===")

    docs = [
        ("Bank Secrecy Act FinCEN",
         "https://www.fincen.gov/resources/statutes-regulations",
         "FinCEN_BSA_Regulations.html"),
        ("FASB ASC 326 CECL (public summary)",
         "https://www.fasb.org/page/PageContent?pageId=/standards/recently-issued-standards.html",
         "FASB_Standards_Index.html"),
    ]

    for label, url, fname in docs:
        save_html(url, folder / fname, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# 6. FINTRAC — corrected URL
# ─────────────────────────────────────────────
def download_fintrac_retry():
    folder = BASE_DIR / "canada" / "other"
    folder.mkdir(parents=True, exist_ok=True)
    print("\n=== FINTRAC — Retry ===")
    save_html(
        "https://www.fintrac-canafe.gc.ca/guidance-directives/overview-apercu/Guide-eng",
        folder / "FINTRAC_Guidelines.html",
        "FINTRAC Guidelines Overview"
    )
    # Try index page as fallback
    save_html(
        "https://fintrac-canafe.canada.ca/guidance-directives/1-eng",
        folder / "FINTRAC_Guidelines_Alt.html",
        "FINTRAC Guidelines Alt"
    )


# ─────────────────────────────────────────────
# MANUAL DOWNLOAD NOTICE
# ─────────────────────────────────────────────
MANUAL_DOWNLOADS = [
    {
        "label": "SEC Regulation SHO",
        "reason": "SEC blocks automated downloads (403). Download manually.",
        "url": "https://www.sec.gov/divisions/marketreg/mrfaqregsho1204.htm",
        "save_to": "regulatory_downloads/us/markets/SEC_Reg_SHO.html"
    },
    {
        "label": "SEC Regulation Best Interest (Reg BI)",
        "reason": "SEC blocks automated downloads (403).",
        "url": "https://www.sec.gov/info/smallbus/secg/regulation-best-interest",
        "save_to": "regulatory_downloads/us/markets/SEC_Reg_BI.html"
    },
    {
        "label": "SEC Investment Advisers Act",
        "reason": "SEC blocks automated downloads (403).",
        "url": "https://www.sec.gov/divisions/investment/adviserinfo.htm",
        "save_to": "regulatory_downloads/us/markets/SEC_Advisers_Act.html"
    },
    {
        "label": "FASB ASC 326 CECL",
        "reason": "FASB requires account login for full standard access (403).",
        "url": "https://asc.fasb.org/326",
        "save_to": "regulatory_downloads/us/aml/FASB_ASC326_CECL.html"
    },
    {
        "label": "CIRO Rules and Enforcement",
        "reason": "CIRO blocks automated access (403). Download manually.",
        "url": "https://www.ciro.ca/rules-and-enforcement/current-rules",
        "save_to": "regulatory_downloads/canada/other/CIRO_Rules.html"
    },
    {
        "label": "Fed SR 99-18 Counterparty Credit Risk (1999)",
        "reason": "Old SR letter — URL may have changed. Check: www.federalreserve.gov/boarddocs/srletters/",
        "url": "https://www.federalreserve.gov/boarddocs/srletters/1999/",
        "save_to": "regulatory_downloads/us/federal_reserve/Fed_SR99-18_CCR.html"
    },
]


def write_manifest():
    ok = [m for m in MANIFEST if m["status"] == "ok"]
    skipped = [m for m in MANIFEST if m["status"] == "skipped"]
    failed = [m for m in MANIFEST if m["status"] not in ("ok", "skipped")]

    # Append to existing manifest
    existing_path = BASE_DIR / "download_manifest.json"
    existing = json.loads(existing_path.read_text()) if existing_path.exists() else {"results": []}
    all_results = existing["results"] + MANIFEST

    all_ok = [m for m in all_results if m["status"] == "ok"]
    all_skipped = [m for m in all_results if m["status"] == "skipped"]
    all_failed = [m for m in all_results if m["status"] not in ("ok", "skipped")]

    manifest_path = BASE_DIR / "download_manifest.json"
    with open(manifest_path, "w") as f:
        json.dump({
            "summary": {"ok": len(all_ok), "skipped": len(all_skipped), "failed": len(all_failed),
                        "manual_required": len(MANUAL_DOWNLOADS)},
            "results": all_results,
            "manual_downloads_required": MANUAL_DOWNLOADS
        }, f, indent=2)

    print(f"\n{'='*60}")
    print(f"RETRY DONE — Downloaded: {len(ok)}  |  Skipped: {len(skipped)}  |  Failed: {len(failed)}")
    print(f"TOTAL (all runs) — OK: {len(all_ok)}  |  Skipped: {len(all_skipped)}  |  Failed: {len(all_failed)}")
    print(f"Manual downloads required: {len(MANUAL_DOWNLOADS)}")
    print(f"\nManifest updated: {manifest_path}")

    if failed:
        print("\nStill failing:")
        for m in failed:
            print(f"  - {m['label']}: {m['status']}")

    print(f"\nManual downloads needed (blocked by site):")
    for m in MANUAL_DOWNLOADS:
        print(f"  - {m['label']}")
        print(f"    URL: {m['url']}")
        print(f"    Save to: {m['save_to']}")


if __name__ == "__main__":
    print(f"Retrying failed downloads into: {BASE_DIR}")
    download_osfi_car_2026()
    download_osfi_lar_2026()
    download_osfi_guidelines_retry()
    download_fed_retry()
    download_fincen_retry()
    download_fintrac_retry()
    write_manifest()
