"""
Bank Filings Downloader — Phase 1 (inventory) + Phase 2/3 (download)
Downloads 10-K/10-Q (US banks) and 40-F/6-K (Canadian banks) from SEC EDGAR.
Output: bank_filings/{us|canada}/{ticker}/{form_type}/

Usage:
  python download_bank_filings.py --phase inventory
  python download_bank_filings.py --phase us
  python download_bank_filings.py --phase canada
  python download_bank_filings.py --phase all
"""

import argparse
import json
import time
import re
import sys
from datetime import datetime, date, timezone
from pathlib import Path

import requests
import html2text as _html2text

# html2text converter (reuse one instance)
_h2t = _html2text.HTML2Text()
_h2t.ignore_images = True
_h2t.ignore_tables = False
_h2t.body_width = 0
_h2t.unicode_snob = True

def _to_md(raw_text: str) -> str:
    md = _h2t.handle(raw_text)
    return re.sub(r'\n{4,}', '\n\n\n', md).strip() + '\n'

# ─── Config ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent / "bank_filings"
MANIFEST_PATH = BASE_DIR / "manifest.json"
GAPS_PATH = BASE_DIR / "GAPS.md"

EDGAR_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
EDGAR_ARCHIVES = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{doc}"
EDGAR_INDEX = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form}&dateb=&owner=include&count=40&search_text="

HEADERS = {
    "User-Agent": "RiskGPT DataLoader saad@riskgpt.ai",
    "Accept-Encoding": "gzip, deflate",
}

START_DATE = date(2020, 1, 1)
END_DATE   = date(2026, 4, 3)

# 6-K filter — only grab quarterly earnings/results packages
SIX_K_KEYWORDS = [
    "quarter", "interim", "results", "financial statements",
    "q1", "q2", "q3", "q4", "first quarter", "second quarter",
    "third quarter", "fourth quarter", "annual", "supplement"
]

MAX_FILE_MB = 150  # skip files larger than this

# ─── Bank Registry ────────────────────────────────────────────────────────────
US_BANKS = [
    {"ticker": "jpm",  "name": "JPMorgan Chase",     "cik": "0000019617", "forms": ["10-K", "10-Q"]},
    {"ticker": "bac",  "name": "Bank of America",    "cik": "0000070858", "forms": ["10-K", "10-Q"]},
    {"ticker": "wfc",  "name": "Wells Fargo",         "cik": "0000072971", "forms": ["10-K", "10-Q"]},
    {"ticker": "c",    "name": "Citigroup",           "cik": "0000831001", "forms": ["10-K", "10-Q"]},
    {"ticker": "gs",   "name": "Goldman Sachs",       "cik": "0000886982", "forms": ["10-K", "10-Q"]},
    {"ticker": "ms",   "name": "Morgan Stanley",      "cik": "0000895421", "forms": ["10-K", "10-Q"]},
    {"ticker": "usb",  "name": "US Bancorp",          "cik": "0000036104", "forms": ["10-K", "10-Q"]},
    {"ticker": "tfc",  "name": "Truist Financial",    "cik": "0000092230", "forms": ["10-K", "10-Q"]},
    {"ticker": "pnc",  "name": "PNC Financial",       "cik": "0000713676", "forms": ["10-K", "10-Q"]},
    {"ticker": "cof",  "name": "Capital One",         "cik": "0000927628", "forms": ["10-K", "10-Q"]},
]

CA_BANKS = [
    {"ticker": "ry",  "name": "Royal Bank of Canada",  "cik": "0001000275", "forms": ["40-F", "6-K"]},
    {"ticker": "td",  "name": "TD Bank Group",          "cik": "0000947263", "forms": ["40-F", "6-K"]},
    {"ticker": "bns", "name": "Scotiabank",             "cik": "0000009631", "forms": ["40-F", "6-K"]},
    {"ticker": "bmo", "name": "Bank of Montreal",       "cik": "0000927971", "forms": ["40-F", "6-K"]},
    {"ticker": "cm",  "name": "CIBC",                   "cik": "0001045520", "forms": ["40-F", "6-K"]},
]

ALL_BANKS = US_BANKS + CA_BANKS

# ─── Manifest ─────────────────────────────────────────────────────────────────
def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text())
    return {"generated": str(date.today()), "filings": []}

def save_manifest(manifest: dict):
    ok       = [f for f in manifest["filings"] if f["status"] == "ok"]
    failed   = [f for f in manifest["filings"] if f["status"] == "failed"]
    skipped  = [f for f in manifest["filings"] if f["status"] == "skipped"]
    missing  = [f for f in manifest["filings"] if f["status"] == "missing"]
    planned  = [f for f in manifest["filings"] if f["status"] == "planned"]
    manifest["summary"] = {
        "total_planned": len(manifest["filings"]),
        "downloaded": len(ok),
        "failed": len(failed),
        "skipped": len(skipped),
        "missing": len(missing),
        "pending": len(planned),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))

def already_recorded(manifest: dict, accession: str) -> bool:
    return any(f["accession"] == accession for f in manifest["filings"])

# ─── EDGAR helpers ────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update(HEADERS)
_last_request = 0.0

def edgar_get(url: str, stream: bool = False) -> requests.Response:
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < 0.12:
        time.sleep(0.12 - elapsed)
    for attempt in range(4):
        try:
            r = SESSION.get(url, timeout=60, stream=stream)
            _last_request = time.time()
            if r.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"    [429] rate limited — waiting {wait}s")
                time.sleep(wait)
                continue
            return r
        except requests.RequestException as e:
            wait = 5 * (attempt + 1)
            print(f"    [ERR] {e} — retry in {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"Failed after retries: {url}")

def get_submissions(cik: str) -> dict:
    cik_padded = cik.lstrip("0").zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
    r = edgar_get(url)
    r.raise_for_status()
    return r.json()

def acc_no_dashes(accession: str) -> str:
    return accession.replace("-", "")

def in_date_range(period_str: str) -> bool:
    """Check if a filing's period-of-report falls in our window."""
    try:
        d = date.fromisoformat(period_str)
        return START_DATE <= d <= END_DATE
    except Exception:
        return False

def is_relevant_6k(description: str) -> bool:
    desc = (description or "").lower()
    return any(k in desc for k in SIX_K_KEYWORDS)

# ─── Folder helpers ───────────────────────────────────────────────────────────
FORM_FOLDER = {
    "10-K": "10k", "10-K/A": "10k",
    "10-Q": "10q", "10-Q/A": "10q",
    "40-F": "40f", "40-F/A": "40f",
    "6-K":  "6k",  "6-K/A":  "6k",
}

def filing_dir(region: str, ticker: str, form: str) -> Path:
    folder = FORM_FOLDER.get(form, form.lower().replace("/", "_"))
    return BASE_DIR / region / ticker / folder

def filing_filename(ticker: str, form: str, period: str, accession: str) -> str:
    period_clean = period.replace("-", "")
    form_clean   = form.replace("/", "_").replace("-", "")
    short_acc    = accession.split("-")[-1] if "-" in accession else accession[-6:]
    return f"{ticker.upper()}_{form_clean}_{period_clean}_{short_acc}"

# ─── Phase 1: Build inventory ─────────────────────────────────────────────────
def _parse_filings_page(data: dict, target_forms: list, bank: dict,
                         region: str, manifest: dict) -> tuple[int, bool]:
    """Parse one filings page. Returns (added_count, should_stop)."""
    added = 0
    ticker  = bank["ticker"]
    cik     = bank["cik"]
    name    = bank["name"]
    cik_num = cik.lstrip("0")

    forms       = data.get("form", [])
    accessions  = data.get("accessionNumber", [])
    periods     = data.get("reportDate", [])          # correct key
    filed_dates = data.get("filingDate", [])
    documents   = data.get("primaryDocument", [])
    descriptions= data.get("primaryDocDescription", [""] * len(forms))

    earliest_filed = None
    for form, acc, period, filed, doc, desc in zip(
        forms, accessions, periods, filed_dates, documents, descriptions
    ):
        if filed:
            earliest_filed = filed   # pages are newest-first; last value = oldest

        if form not in target_forms:
            continue
        # Use filed date for range check (reportDate often empty for older filings)
        date_check = period or filed
        if not in_date_range(date_check):
            continue
        if form in ("6-K", "6-K/A") and not is_relevant_6k(desc):
            continue
        if already_recorded(manifest, acc):
            continue

        acc_clean  = acc_no_dashes(acc)
        doc_url    = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/{doc}"
        fname_base = filing_filename(ticker, form, period or filed, acc)
        dest_dir   = filing_dir(region, ticker, form)
        dest_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "bank": name, "ticker": ticker, "region": region,
            "cik": cik, "form": form, "period": period, "filed": filed,
            "accession": acc, "description": desc, "source_url": doc_url,
            "raw_file":  str(dest_dir / f"{fname_base}.htm"),
            "md_file":   str(dest_dir / f"{fname_base}.md"),
            "meta_file": str(dest_dir / f"{fname_base}.json"),
            "status": "planned", "size_kb": None, "downloaded_at": None,
        }
        manifest["filings"].append(entry)
        added += 1

    # Stop paginating once we've gone past our start date
    should_stop = bool(earliest_filed and earliest_filed < "2020-01-01")
    return added, should_stop


def build_inventory(banks: list, region: str, manifest: dict) -> int:
    added = 0
    for bank in banks:
        ticker = bank["ticker"]
        cik    = bank["cik"]
        name   = bank["name"]
        print(f"\n  [{ticker.upper()}] {name} — fetching submissions...")

        try:
            data = get_submissions(cik)
        except Exception as e:
            print(f"    [FAIL] {e}")
            continue

        target_forms = bank["forms"]

        # Recent filings page
        recent = data.get("filings", {}).get("recent", {})
        n, stop = _parse_filings_page(recent, target_forms, bank, region, manifest)
        added += n

        # Paginated older filings — only fetch pages whose dates overlap our range
        if not stop:
            for old in data.get("filings", {}).get("files", []):
                filing_to = old.get("filingTo", "9999-12-31")
                if filing_to < "2020-01-01":
                    break   # this page and all subsequent are too old
                old_url = f"https://data.sec.gov/submissions/{old['name']}"
                try:
                    r2 = edgar_get(old_url)
                    r2.raise_for_status()
                    n, stop = _parse_filings_page(r2.json(), target_forms, bank, region, manifest)
                    added += n
                    if stop:
                        break
                except Exception as e:
                    print(f"    [WARN] {old['name']}: {e}")

        bank_total = sum(1 for f in manifest["filings"] if f["ticker"] == ticker)
        print(f"    → {bank_total} filings queued")

    save_manifest(manifest)
    return added

# ─── Phase 2/3: Download filings ──────────────────────────────────────────────
def download_filings(manifest: dict, region: str | None = None):
    targets = [
        f for f in manifest["filings"]
        if f["status"] in ("planned", "failed")
        and (region is None or f["region"] == region)
    ]

    print(f"\n  {len(targets)} filings to download" + (f" [{region}]" if region else ""))

    for i, entry in enumerate(targets, 1):
        ticker = entry["ticker"]
        form   = entry["form"]
        period = entry["period"]
        url    = entry["source_url"]
        raw    = Path(entry["raw_file"])
        meta   = Path(entry["meta_file"])

        label = f"[{i}/{len(targets)}] {ticker.upper()} {form} {period}"

        # Already downloaded
        if raw.exists() and raw.stat().st_size > 1024:
            print(f"  [SKIP] {label}")
            entry["status"] = "ok"
            entry["size_kb"] = raw.stat().st_size // 1024
            continue

        try:
            r = edgar_get(url, stream=True)
            if r.status_code == 404:
                # Try index page to find alternate document
                alt_url = _find_alt_doc(entry)
                if alt_url:
                    r = edgar_get(alt_url, stream=True)
                    entry["source_url"] = alt_url
                    url = alt_url

            r.raise_for_status()

            # Check content length
            content_length = int(r.headers.get("Content-Length", 0))
            if content_length > MAX_FILE_MB * 1024 * 1024:
                print(f"  [SKIP] {label} — too large ({content_length//1024//1024} MB)")
                entry["status"] = "skipped"
                entry["skip_reason"] = f"file too large: {content_length//1024//1024} MB"
                save_manifest(manifest)
                continue

            raw.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            with open(raw, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if downloaded > MAX_FILE_MB * 1024 * 1024:
                        break

            raw_kb = raw.stat().st_size // 1024

            # Convert to MD immediately, then delete raw to save disk space
            md_path = Path(entry["md_file"])
            try:
                content_text = raw.read_text(encoding="utf-8", errors="ignore")
                md_path.write_text(_to_md(content_text), encoding="utf-8")
                raw.unlink()   # delete raw HTML — MD is all we keep
                size_kb = md_path.stat().st_size // 1024
            except Exception as conv_err:
                size_kb = raw_kb  # keep raw if conversion fails
                print(f"    [WARN] MD conversion failed: {conv_err}")

            entry["status"] = "ok"
            entry["size_kb"] = size_kb
            entry["downloaded_at"] = datetime.now(timezone.utc).isoformat()

            # Write sidecar metadata
            meta.write_text(json.dumps({k: v for k, v in entry.items()
                                        if k not in ("status",)}, indent=2))

            print(f"  [OK]   {label} ({size_kb} KB md)")

        except Exception as e:
            print(f"  [FAIL] {label} — {e}")
            entry["status"] = "failed"
            entry["error"]  = str(e)

        save_manifest(manifest)

def _find_alt_doc(entry: dict) -> str | None:
    """Fetch filing index page and return URL of largest htm document."""
    try:
        cik_num   = entry["cik"].lstrip("0")
        acc_clean = acc_no_dashes(entry["accession"])
        index_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik_num}&type={entry['form']}&dateb=&owner=include&count=1"
        idx_json  = f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/{acc_clean}-index.json"
        r = edgar_get(idx_json)
        if r.status_code == 200:
            idx = r.json()
            docs = idx.get("documents", [])
            # prefer primary htm
            for doc in docs:
                if doc.get("type") in (entry["form"], entry["form"].replace("/A", "")):
                    name = doc.get("filename") or doc.get("document", "")
                    if name:
                        cik_num = entry["cik"].lstrip("0")
                        return f"https://www.sec.gov/Archives/edgar/data/{cik_num}/{acc_clean}/{name}"
    except Exception:
        pass
    return None

# ─── Gaps report ──────────────────────────────────────────────────────────────
def write_gaps(manifest: dict):
    failed  = [f for f in manifest["filings"] if f["status"] == "failed"]
    skipped = [f for f in manifest["filings"] if f["status"] == "skipped"]
    planned = [f for f in manifest["filings"] if f["status"] == "planned"]

    lines = [
        "# Bank Filings — Gaps Report",
        f"Generated: {datetime.utcnow().isoformat()}Z",
        "",
        f"## Summary",
        f"- Downloaded: {manifest['summary']['downloaded']}",
        f"- Failed: {len(failed)}",
        f"- Skipped (too large): {len(skipped)}",
        f"- Still pending: {len(planned)}",
        "",
    ]

    if failed:
        lines += ["## Failed Downloads", ""]
        for f in failed:
            lines.append(f"- **{f['ticker'].upper()} {f['form']} {f['period']}**")
            lines.append(f"  - URL: {f['source_url']}")
            lines.append(f"  - Error: {f.get('error','unknown')}")
            lines.append("")

    if skipped:
        lines += ["## Skipped (File Too Large)", ""]
        for f in skipped:
            lines.append(f"- **{f['ticker'].upper()} {f['form']} {f['period']}** — {f.get('skip_reason','')}")
        lines.append("")

    if planned:
        lines += ["## Still Pending", ""]
        for f in planned:
            lines.append(f"- {f['ticker'].upper()} {f['form']} {f['period']}")
        lines.append("")

    GAPS_PATH.write_text("\n".join(lines))
    print(f"\n  Gaps report: {GAPS_PATH}")

# ─── Entry point ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["inventory", "us", "canada", "all"], default="all")
    args = parser.parse_args()

    BASE_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    if args.phase in ("inventory", "all"):
        print("\n=== Phase 1: Building inventory ===")
        print("  US banks...")
        build_inventory(US_BANKS, "us", manifest)
        print("  Canadian banks...")
        build_inventory(CA_BANKS, "canada", manifest)
        s = manifest["summary"]
        print(f"\n  Inventory complete — {s['total_planned']} filings queued")

    if args.phase in ("us", "all"):
        print("\n=== Phase 2: Downloading US bank filings ===")
        download_filings(manifest, region="us")

    if args.phase in ("canada", "all"):
        print("\n=== Phase 3: Downloading Canadian bank filings ===")
        download_filings(manifest, region="canada")

    write_gaps(manifest)
    s = manifest["summary"]
    print(f"\n{'='*60}")
    print(f"Done — Downloaded: {s['downloaded']}  Failed: {s['failed']}  Skipped: {s['skipped']}  Pending: {s['pending']}")
    print(f"Manifest: {MANIFEST_PATH}")

if __name__ == "__main__":
    main()
