"""
Regulatory Data Downloader
Downloads all regulatory documents into regulatory_downloads/ for review.
"""

import os
import re
import time
import json
import requests
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

BASE_DIR = Path(__file__).parent / "regulatory_downloads"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

MANIFEST = []  # track successes/failures


def mkdir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(name: str) -> str:
    return re.sub(r'[^\w\-_. ]', '_', name).strip()


def download_pdf(url: str, dest: Path, label: str) -> bool:
    if dest.exists():
        print(f"  [SKIP] {label} (already exists)")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "skipped"})
        return True
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
        return True
    except Exception as e:
        print(f"  [FAIL] {label} — {e}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": f"failed: {e}"})
        return False


def save_html(url: str, dest: Path, label: str) -> bool:
    if dest.exists():
        print(f"  [SKIP] {label} (already exists)")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "skipped"})
        return True
    try:
        r = SESSION.get(url, timeout=30)
        r.raise_for_status()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(r.text, encoding="utf-8")
        size_kb = dest.stat().st_size // 1024
        print(f"  [OK]   {label} ({size_kb} KB)")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": "ok", "size_kb": size_kb})
        return True
    except Exception as e:
        print(f"  [FAIL] {label} — {e}")
        MANIFEST.append({"label": label, "url": url, "file": str(dest), "status": f"failed: {e}"})
        return False


def scrape_osfi_index(index_url: str, folder: Path, prefix: str) -> None:
    """Scrape an OSFI guidance index page and download all linked PDFs."""
    print(f"\n  Scraping OSFI index: {index_url}")
    try:
        r = SESSION.get(index_url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")
        pdf_links = [
            a["href"] for a in soup.find_all("a", href=True)
            if a["href"].lower().endswith(".pdf")
        ]
        if not pdf_links:
            # Try saving index as HTML fallback
            dest = folder / f"{prefix}_index.html"
            save_html(index_url, dest, f"{prefix} index page")
            return
        for href in pdf_links:
            full_url = urljoin(index_url, href)
            fname = safe_filename(Path(urlparse(full_url).path).name)
            dest = folder / f"{prefix}_{fname}"
            download_pdf(full_url, dest, f"{prefix} — {fname}")
            time.sleep(0.5)
    except Exception as e:
        print(f"  [FAIL] Could not scrape {index_url} — {e}")
        MANIFEST.append({"label": f"{prefix} index", "url": index_url, "file": "", "status": f"scrape_failed: {e}"})


# ─────────────────────────────────────────────
# SECTION 1: OSFI CAR
# ─────────────────────────────────────────────
def download_osfi_car():
    folder = mkdir(BASE_DIR / "osfi" / "car")
    print("\n=== OSFI Capital Adequacy Requirements (CAR) ===")
    scrape_osfi_index(
        "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/capital-adequacy-requirements-2024",
        folder, "OSFI_CAR_2024"
    )
    time.sleep(1)
    scrape_osfi_index(
        "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/capital-adequacy-requirements-2023",
        folder, "OSFI_CAR_2023"
    )


# ─────────────────────────────────────────────
# SECTION 2: OSFI LAR
# ─────────────────────────────────────────────
def download_osfi_lar():
    folder = mkdir(BASE_DIR / "osfi" / "lar")
    print("\n=== OSFI Liquidity Adequacy Requirements (LAR) ===")
    scrape_osfi_index(
        "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/liquidity-adequacy-requirements-2024",
        folder, "OSFI_LAR_2024"
    )
    time.sleep(1)
    scrape_osfi_index(
        "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/liquidity-adequacy-requirements-2023",
        folder, "OSFI_LAR_2023"
    )


# ─────────────────────────────────────────────
# SECTION 3: OSFI Guidelines (B-Series & E-Series)
# ─────────────────────────────────────────────
def download_osfi_guidelines():
    folder = mkdir(BASE_DIR / "osfi" / "guidelines")
    print("\n=== OSFI Guidelines (B-Series & E-Series) ===")

    guidelines = [
        # (label, url, filename)
        ("OSFI B-6 Liquidity Principles",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/liquidity-principles-deposit-taking-institutions",
         "OSFI_B-6_Liquidity_Principles.html"),
        ("OSFI B-10 Third-Party Risk Management",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/third-party-risk-management-guideline",
         "OSFI_B-10_Third_Party_Risk.html"),
        ("OSFI B-13 Technology and Cyber Risk",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/technology-cyber-risk-management",
         "OSFI_B-13_Tech_Cyber_Risk.html"),
        ("OSFI B-15 Climate Risk Management",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/climate-risk-management",
         "OSFI_B-15_Climate_Risk.html"),
        ("OSFI B-20 Residential Mortgage Underwriting",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/residential-mortgage-underwriting-practices-procedures",
         "OSFI_B-20_Mortgage_Underwriting.html"),
        ("OSFI E-13 Regulatory Compliance Management",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/regulatory-compliance-management",
         "OSFI_E-13_Compliance_Mgmt.html"),
        ("OSFI E-21 Operational Risk and Resilience",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/operational-resilience-risk-management",
         "OSFI_E-21_Operational_Risk.html"),
        ("OSFI E-23 Enterprise-Wide Model Risk Management",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/enterprise-wide-model-risk-management-financial-institutions",
         "OSFI_E-23_Model_Risk.html"),
        ("OSFI Corporate Governance Guideline",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/corporate-governance-guideline",
         "OSFI_Corporate_Governance.html"),
        ("OSFI Integrity and Security Guideline",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/integrity-security-guideline",
         "OSFI_Integrity_Security.html"),
        ("OSFI Pillar 3 Disclosure Requirements",
         "https://www.osfi-bsif.gc.ca/en/guidance/guidance-library/pillar-3-disclosure-requirements",
         "OSFI_Pillar3_Disclosure.html"),
        ("OSFI Supervisory Framework",
         "https://www.osfi-bsif.gc.ca/en/supervision/supervisory-framework",
         "OSFI_Supervisory_Framework.html"),
        ("OSFI Domestic Stability Buffer",
         "https://www.osfi-bsif.gc.ca/en/bank-regulatory-capital/domestic-stability-buffer",
         "OSFI_DSB_Announcements.html"),
    ]

    for label, url, fname in guidelines:
        dest = folder / fname
        save_html(url, dest, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# SECTION 4: Canada — Other Regulatory Bodies
# ─────────────────────────────────────────────
def download_canada_other():
    folder = mkdir(BASE_DIR / "canada" / "other")
    print("\n=== Canada — Other Regulatory Bodies ===")

    docs = [
        ("Bank Act (Canada)",
         "https://laws-lois.justice.gc.ca/eng/acts/B-1.01/",
         "Bank_Act_Canada.html"),
        ("PCMLTFA — AML Act",
         "https://laws-lois.justice.gc.ca/eng/acts/P-24.501/",
         "PCMLTFA_AML_Act.html"),
        ("FINTRAC Guidelines Overview",
         "https://www.fintrac-canafe.gc.ca/guidance-directives/overview-apercu/Guide-eng",
         "FINTRAC_Guidelines.html"),
        ("OSC NI 31-103 Registration Requirements",
         "https://www.osc.ca/en/securities-law/instruments-rules-policies/3/31-103",
         "OSC_NI_31-103.html"),
        ("CIRO Rules and Enforcement",
         "https://www.ciro.ca/rules-and-enforcement/current-rules",
         "CIRO_Rules.html"),
    ]

    for label, url, fname in docs:
        dest = folder / fname
        save_html(url, dest, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# SECTION 5: US — OCC Comptroller's Handbooks
# ─────────────────────────────────────────────
def download_occ_handbooks():
    folder = mkdir(BASE_DIR / "us" / "occ")
    print("\n=== US — OCC Comptroller's Handbooks ===")

    # Scrape the index to find actual PDF links
    index_url = "https://www.occ.gov/publications-and-resources/publications/comptrollers-handbook/index-comptrollers-handbook.html"
    print(f"  Scraping OCC index: {index_url}")
    try:
        r = SESSION.get(index_url, timeout=30)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "lxml")

        target_keywords = [
            "commercial real estate", "credit risk", "operational risk",
            "market risk", "interest rate risk", "model risk"
        ]

        found = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            href = a["href"]
            if any(kw in text for kw in target_keywords) and (
                href.lower().endswith(".pdf") or "/comptrollers-handbook/" in href.lower()
            ):
                found.append((a.get_text(strip=True), urljoin(index_url, href)))

        if found:
            for label, url in found:
                if url.lower().endswith(".pdf"):
                    fname = safe_filename(Path(urlparse(url).path).name)
                    dest = folder / f"OCC_{fname}"
                    download_pdf(url, dest, f"OCC — {label}")
                else:
                    fname = safe_filename(label[:60]) + ".html"
                    dest = folder / f"OCC_{fname}"
                    save_html(url, dest, f"OCC — {label}")
                time.sleep(0.5)
        else:
            # Save index as fallback
            dest = folder / "OCC_Handbook_Index.html"
            save_html(index_url, dest, "OCC Handbook Index")

    except Exception as e:
        print(f"  [FAIL] OCC index — {e}")
        MANIFEST.append({"label": "OCC Handbook Index", "url": index_url, "file": "", "status": f"failed: {e}"})


# ─────────────────────────────────────────────
# SECTION 6: US — Federal Reserve SR Letters & Capital Rules
# ─────────────────────────────────────────────
def download_fed_documents():
    folder = mkdir(BASE_DIR / "us" / "federal_reserve")
    print("\n=== US — Federal Reserve SR Letters & Capital Rules ===")

    docs = [
        ("Fed SR 11-7 Model Risk Management",
         "https://www.federalreserve.gov/supervisionreg/srletters/sr1107.htm",
         "Fed_SR11-7_Model_Risk.html"),
        ("Fed SR 12-7 Stress Testing Guidance",
         "https://www.federalreserve.gov/supervisionreg/srletters/sr1207.htm",
         "Fed_SR12-7_Stress_Testing.html"),
        ("Fed SR 99-18 Counterparty Credit Risk",
         "https://www.federalreserve.gov/supervisionreg/srletters/sr9918.htm",
         "Fed_SR99-18_CCR.html"),
        ("Fed SR 16-11 Data and Models",
         "https://www.federalreserve.gov/supervisionreg/srletters/sr1611.htm",
         "Fed_SR16-11_Data_Models.html"),
        ("Fed Regulation YY Enhanced Prudential Standards",
         "https://www.federalreserve.gov/supervisionreg/regs/regy.htm",
         "Fed_Reg_YY.html"),
        ("Fed Regulation W Transactions with Affiliates",
         "https://www.federalreserve.gov/supervisionreg/regs/regw.htm",
         "Fed_Reg_W.html"),
        ("CCAR Stress Test Policies Index",
         "https://www.federalreserve.gov/publications/stress-test-policies.htm",
         "Fed_CCAR_Index.html"),
        ("DFAST Stress Tests Index",
         "https://www.federalreserve.gov/supervisionreg/dfa-stress-tests.htm",
         "Fed_DFAST_Index.html"),
    ]

    for label, url, fname in docs:
        dest = folder / fname
        save_html(url, dest, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# SECTION 7: US — Markets, Conduct & Wealth Regulation
# ─────────────────────────────────────────────
def download_us_markets():
    folder = mkdir(BASE_DIR / "us" / "markets")
    print("\n=== US — Markets, Conduct & Wealth Regulation ===")

    docs = [
        ("SEC Regulation SHO Short Selling",
         "https://www.sec.gov/divisions/marketreg/mrfaqregsho1204.htm",
         "SEC_Reg_SHO.html"),
        ("CFTC Swap Dealer Rules Dodd-Frank",
         "https://www.cftc.gov/LawRegulation/DoddFrankAct/Rulemakings/index.htm",
         "CFTC_Dodd_Frank.html"),
        ("SEC Regulation Best Interest",
         "https://www.sec.gov/info/smallbus/secg/regulation-best-interest",
         "SEC_Reg_BI.html"),
        ("SEC Investment Advisers Act",
         "https://www.sec.gov/divisions/investment/adviserinfo.htm",
         "SEC_Advisers_Act.html"),
        ("FINRA Rulebook",
         "https://www.finra.org/rules-guidance/rulebooks/finra-rules",
         "FINRA_Rulebook.html"),
        # PDFs
        ("BCBS-IOSCO Margin Requirements for Non-Cleared Derivatives",
         "https://www.bis.org/bcbs/publ/d499.pdf",
         "BCBS_IOSCO_Margin_Requirements_d499.pdf"),
        ("Volcker Rule Final Rule 2020",
         "https://www.occ.gov/topics/charters-and-licensing/volcker-rule/volcker-rule-final-rule-2020.pdf",
         "OCC_Volcker_Rule_2020.pdf"),
    ]

    for label, url, fname in docs:
        dest = folder / fname
        if fname.endswith(".pdf"):
            download_pdf(url, dest, label)
        else:
            save_html(url, dest, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# SECTION 8: US — AML, Sanctions & Financial Reporting
# ─────────────────────────────────────────────
def download_us_aml():
    folder = mkdir(BASE_DIR / "us" / "aml")
    print("\n=== US — AML, Sanctions & Financial Reporting ===")

    docs = [
        ("Bank Secrecy Act FinCEN",
         "https://www.fincen.gov/resources/statutes-regulations/bank-secrecy-act",
         "FinCEN_BSA.html"),
        ("FFIEC BSA/AML Examination Manual",
         "https://bsaaml.ffiec.gov/manual",
         "FFIEC_BSAAML_Manual.html"),
        ("FinCEN AML Program Rules",
         "https://www.fincen.gov/resources/statutes-regulations",
         "FinCEN_AML_Rules.html"),
        ("OFAC Sanctions Programs",
         "https://ofac.treasury.gov/faqs/topic/1521",
         "OFAC_Sanctions.html"),
        ("FASB ASC 326 CECL",
         "https://asc.fasb.org/326",
         "FASB_ASC326_CECL.html"),
    ]

    for label, url, fname in docs:
        dest = folder / fname
        save_html(url, dest, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# SECTION 9: International — Basel / BCBS
# ─────────────────────────────────────────────
def download_bcbs():
    folder = mkdir(BASE_DIR / "bcbs")
    print("\n=== International — Basel Committee (BCBS) ===")

    pdfs = [
        ("BCBS 239 Risk Data Aggregation RDARR (MANDATORY)",
         "https://www.bis.org/publ/bcbs239.pdf",
         "BCBS_239_RDARR.pdf"),
        ("Basel LCR Standard bcbs238",
         "https://www.bis.org/publ/bcbs238.pdf",
         "Basel_LCR_Standard_bcbs238.pdf"),
        ("Basel NSFR Standard d295",
         "https://www.bis.org/bcbs/publ/d295.pdf",
         "Basel_NSFR_d295.pdf"),
        ("Basel IRRBB Standard d368",
         "https://www.bis.org/bcbs/publ/d368.pdf",
         "Basel_IRRBB_d368.pdf"),
        ("BCBS Sound Stress Testing Practices bcbs155",
         "https://www.bis.org/publ/bcbs155.pdf",
         "BCBS_Stress_Testing_bcbs155.pdf"),
        ("BCBS Sound Liquidity Risk Management bcbs144",
         "https://www.bis.org/publ/bcbs144.pdf",
         "BCBS_Liquidity_Risk_bcbs144.pdf"),
        ("BCBS Corporate Governance Principles d328",
         "https://www.bis.org/bcbs/publ/d328.pdf",
         "BCBS_Corporate_Governance_d328.pdf"),
        ("BCBS-IOSCO Margin Requirements d499",
         "https://www.bis.org/bcbs/publ/d499.pdf",
         "BCBS_Margin_Requirements_d499.pdf"),
    ]

    html_docs = [
        ("Basel Framework — CRE Credit Risk",
         "https://www.bis.org/basel_framework/chapter/CRE/1.htm",
         "Basel_Framework_CRE.html"),
        ("Basel Framework — MAR Market Risk FRTB",
         "https://www.bis.org/basel_framework/chapter/MAR/1.htm",
         "Basel_Framework_MAR.html"),
        ("Basel Framework — OPE Operational Risk",
         "https://www.bis.org/basel_framework/chapter/OPE/1.htm",
         "Basel_Framework_OPE.html"),
        ("Basel Framework — LEX Large Exposures",
         "https://www.bis.org/basel_framework/chapter/LEX/1.htm",
         "Basel_Framework_LEX.html"),
        ("Basel Framework — SA-CCR CRE52",
         "https://www.bis.org/basel_framework/chapter/CRE/52.htm",
         "Basel_Framework_SA-CCR_CRE52.html"),
        ("Basel Framework Index",
         "https://www.bis.org/basel_framework/",
         "Basel_Framework_Index.html"),
    ]

    for label, url, fname in pdfs:
        dest = folder / fname
        download_pdf(url, dest, label)
        time.sleep(0.5)

    for label, url, fname in html_docs:
        dest = folder / fname
        save_html(url, dest, label)
        time.sleep(0.5)


# ─────────────────────────────────────────────
# MANIFEST
# ─────────────────────────────────────────────
def write_manifest():
    manifest_path = BASE_DIR / "download_manifest.json"
    ok = [m for m in MANIFEST if m["status"] == "ok"]
    skipped = [m for m in MANIFEST if m["status"] == "skipped"]
    failed = [m for m in MANIFEST if m["status"] not in ("ok", "skipped")]

    with open(manifest_path, "w") as f:
        json.dump({"summary": {"ok": len(ok), "skipped": len(skipped), "failed": len(failed)},
                   "results": MANIFEST}, f, indent=2)

    print(f"\n{'='*60}")
    print(f"DONE — Downloaded: {len(ok)}  |  Skipped: {len(skipped)}  |  Failed: {len(failed)}")
    print(f"Manifest: {manifest_path}")
    if failed:
        print("\nFailed downloads:")
        for m in failed:
            print(f"  - {m['label']}: {m['status']}")


if __name__ == "__main__":
    print(f"Saving all files to: {BASE_DIR}\n")
    mkdir(BASE_DIR)

    download_osfi_car()
    download_osfi_lar()
    download_osfi_guidelines()
    download_canada_other()
    download_occ_handbooks()
    download_fed_documents()
    download_us_markets()
    download_us_aml()
    download_bcbs()

    write_manifest()
