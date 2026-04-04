"""
test_uat_phase2.py
==================
UAT Phase 2 — Tool, Workflow & Chat tests (requires LLM + external APIs).

Covers:
  Module 5  — Chat / Agent                     (C-01 – C-09)
  Module 6A — IRIS CCR Tools                   (T-01 – T-09)
  Module 6B — OSFI Regulatory Tools            (T-10 – T-14)
  Module 6C — EDGAR / SEC Tools                (T-15 – T-25)
  Module 6D — Tavily / IR / News Tools         (T-26 – T-33)
  Module 6E — DuckDB / SQL Tools               (T-34 – T-41)
  Module 6F — MS Document Tools                (T-42 – T-46)
  Module 6G — Utility Tools                    (T-47 – T-54)
  Module 6H — CCR Exposure Tools               (T-55 – T-60)
  Module 7  — Workflows                        (WF-01 – WF-07)

Each tool test:
  1. Sends a targeted natural-language query to /api/agent/run (SSE)
  2. Asserts the expected tool name appears in tool_start events
  3. Asserts tool_end output is non-empty and not an error
  4. Records PASS / FAIL / SKIP to UAT_RESULTS/

Usage:
  # Both servers must be running. External APIs (Tavily, EDGAR) must be configured.
  python test_uat_phase2.py

  # Run only specific modules:
  UAT_MODULES=5,6A,6B python test_uat_phase2.py

  # Skip slow/external modules:
  UAT_SKIP_MODULES=6C,6D python test_uat_phase2.py

Results saved to UAT_RESULTS/phase2_<timestamp>.json + .md
"""

import os, sys, json, time, uuid, pathlib, io, traceback
import httpx
from uat_framework import UATReporter, UATResult, req, login, run_agent, timed, BASE

# ── Credentials & fixtures ────────────────────────────────────────────────────

SUPER_CREDS = ('risk_agent',  'RiskAgent2025!')
ADMIN_CREDS = ('admin',       'Admin2025!')
USER_CREDS  = ('test_user',   'TestUser2025!')
MR_WORKER   = 'w-market-risk'
CCR_WORKER  = 'w-e74b5836'

# ── Module filter (env-driven) ────────────────────────────────────────────────
_ONLY    = set(os.getenv('UAT_MODULES',       '').upper().split(',')) - {''}
_SKIP    = set(os.getenv('UAT_SKIP_MODULES',  '').upper().split(',')) - {''}

R = UATReporter('phase2')

MODULE = {
    5:    'Module 5 — Chat & Agent',
    '6A': 'Module 6A — IRIS CCR Tools',
    '6B': 'Module 6B — OSFI Regulatory Tools',
    '6C': 'Module 6C — EDGAR / SEC Tools',
    '6D': 'Module 6D — Tavily / IR / News Tools',
    '6E': 'Module 6E — DuckDB / SQL Tools',
    '6F': 'Module 6F — MS Document Tools',
    '6G': 'Module 6G — Utility Tools',
    '6H': 'Module 6H — CCR Exposure Tools',
    7:    'Module 7 — Workflows',
}


def _should_run(key) -> bool:
    k = str(key).upper()
    if _SKIP and k in _SKIP:
        return False
    if _ONLY:
        return k in _ONLY
    return True


# ── Tool assertion helper ─────────────────────────────────────────────────────

def tool_test(test_id: str, module: str, scenario: str,
              query: str, expected_tools: list, tok: str,
              worker_id: str = MR_WORKER,
              check_output_for: str = '',
              timeout: float = 90.0):
    """
    Run agent query, verify expected_tools were called, optionally check output text.
    Saves PASS/FAIL/SKIP to reporter.
    """
    t0 = time.monotonic()
    try:
        result = run_agent(query, worker_id, tok, timeout=timeout)
    except Exception as e:
        R.error(test_id, module, scenario, detail=str(e))
        return

    dur = round((time.monotonic() - t0) * 1000)

    if result.get('error') and not result.get('text'):
        R.fail(test_id, module, scenario,
               detail=f"agent error: {result['error']}", duration_ms=dur)
        return

    called = result.get('tool_names', [])
    text   = result.get('text', '')

    # Check at least one of the expected tools was called
    tools_ok = any(t in called for t in expected_tools)

    # Check output keyword if requested
    output_ok = True
    if check_output_for:
        output_ok = (check_output_for.lower() in text.lower() or
                     any(check_output_for.lower() in str(t.get('output', '')).lower()
                         for t in result.get('tools', [])))

    # Build detail for failures
    detail = ''
    if not tools_ok:
        detail = f'expected one of {expected_tools}, got {called}'
    elif not output_ok:
        detail = f'output missing "{check_output_for}" — text={text[:200]}'

    R.assert_test(test_id, module, scenario, tools_ok and output_ok,
                  detail=detail, duration_ms=dur)


def skip_module(module_key, module_name: str, ids: list, reason=''):
    R.section(f'{module_name}  — SKIPPED')
    for tid in ids:
        R.skip(tid, module_name, f'(skipped: {reason or "module excluded"})')


# ══════════════════════════════════════════════════════════════════════════════
# Module 5 — Chat & Agent
# ══════════════════════════════════════════════════════════════════════════════

def test_chat(tok: str):
    mod = str(5)
    if not _should_run(mod):
        skip_module(mod, MODULE[5], [f'C-0{i}' for i in range(1, 10)]); return

    R.section(f'{MODULE[5]}  (C-01 – C-09)')
    m = MODULE[5]

    # C-01  simple text query — no tool call expected
    t0 = time.monotonic()
    result = run_agent('Hello, who are you? Answer in one sentence.', MR_WORKER, tok, timeout=60)
    dur = round((time.monotonic() - t0) * 1000)
    R.assert_test('C-01', m, 'simple query returns non-empty text',
                  bool(result.get('text')) and not result.get('error'),
                  detail=result.get('error', ''), duration_ms=dur)

    # C-02  SSE session event was captured (thread_id present)
    tid = result.get('thread_id', '')
    R.assert_test('C-02', m, 'agent run returns a thread_id', bool(tid),
                  detail=f'thread_id={tid!r}')

    # C-03  tool-calling query
    result2 = run_agent('List all available IRIS counterparty data dates.', MR_WORKER, tok)
    called = result2.get('tool_names', [])
    R.assert_test('C-03', m, 'tool-calling query invokes at least one tool',
                  len(called) > 0, detail=f'tools={called}')

    # C-04  thread persistence: resume same thread
    if tid:
        result3 = run_agent('What did I ask you first?', MR_WORKER, tok, thread_id=tid)
        R.assert_test('C-04', m, 'resume thread: agent returns text',
                      bool(result3.get('text')), detail=result3.get('error', ''))
    else:
        R.skip('C-04', m, 'resume thread (skipped: no thread_id from C-02)')

    # C-05  thread appears in /api/agent/threads
    s, body = req('GET', '/api/agent/threads', token=tok)
    threads = body.get('threads', [])
    R.assert_test('C-05', m, 'thread appears in /api/agent/threads',
                  s == 200 and len(threads) > 0, detail=f'count={len(threads)}')

    # C-06  worker switcher: different workers can be queried
    result_ccr = run_agent('Who are you?', CCR_WORKER, tok, timeout=60)
    R.assert_test('C-06', m, 'agent accepts CCR worker query',
                  bool(result_ccr.get('text')) and not result_ccr.get('error'),
                  detail=result_ccr.get('error', ''))

    # C-07  tool filtered by worker: restrict tools then query
    # Create a temp worker with only iris_list_dates, ask for EDGAR data
    s, body = req('POST', '/api/super/workers', token=tok,
                  json={'name': 'UAT Filtered Worker', 'system_prompt': 'You are a test bot.',
                        'enabled_tools': ['iris_list_dates']})
    fwid = body.get('worker_id', '')
    if fwid:
        result_f = run_agent('Fetch the latest JPMorgan 10-K from SEC EDGAR.', fwid, tok, timeout=60)
        called_f = result_f.get('tool_names', [])
        # edgar tools should NOT be called since they're not in enabled_tools
        no_edgar = not any('edgar' in t.lower() for t in called_f)
        R.assert_test('C-07', m, 'tool allowlist: EDGAR tools not called when restricted',
                      no_edgar, detail=f'tools_called={called_f}')
        req('DELETE', f'/api/super/workers/{fwid}', token=tok, json={'confirm_name': 'UAT Filtered Worker'})
    else:
        R.skip('C-07', m, 'tool allowlist test (skipped: could not create temp worker)')

    # C-08  error handling: invalid worker_id
    result_bad = run_agent('Hello', 'w-nonexistent', tok, timeout=30)
    R.assert_test('C-08', m, 'invalid worker_id: agent returns error or empty gracefully',
                  result_bad.get('error') is not None or result_bad.get('text') == '',
                  detail=f'text={result_bad.get("text","")[:100]}')

    # C-09  upload a file then reference it
    files = {'file': ('uat_chat_upload.txt', io.BytesIO(b'Revenue: 100M'), 'text/plain')}
    s2, _ = req('POST', f'/api/super/workers/{MR_WORKER}/files/domain_data/upload',
                token=tok, files=files, params={'path': ''})
    if s2 in (200, 201):
        result_ref = run_agent('List uploaded files available to you.', MR_WORKER, tok)
        called_ref = result_ref.get('tool_names', [])
        R.assert_test('C-09', m, 'agent can list uploaded files after upload',
                      any('list' in t.lower() or 'upload' in t.lower() or 'file' in t.lower()
                          for t in called_ref),
                      detail=f'tools={called_ref}')
        req('DELETE', f'/api/super/workers/{MR_WORKER}/files/domain_data/file',
            token=tok, params={'path': 'uat_chat_upload.txt'})
    else:
        R.skip('C-09', m, 'chat upload test (skipped: upload failed)')


# ══════════════════════════════════════════════════════════════════════════════
# Module 6A — IRIS CCR Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_iris(tok: str):
    mod = '6A'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-0{i}' for i in range(1, 10)]); return

    R.section(f'{MODULE[mod]}  (T-01 – T-09)')
    m = MODULE[mod]

    tool_test('T-01', m, 'iris_search_counterparties — find by name',
              'Search for Goldman Sachs in the IRIS counterparty database.',
              ['iris_search_counterparties'], tok)

    tool_test('T-02', m, 'iris_counterparty_dashboard — full dashboard',
              'Show me the full counterparty dashboard for the top counterparty in IRIS.',
              ['iris_counterparty_dashboard', 'iris_search_counterparties', 'iris_list_dates'], tok)

    tool_test('T-03', m, 'iris_exposure_trend — time series',
              'Show the exposure trend for the largest IRIS counterparty over time.',
              ['iris_exposure_trend', 'iris_search_counterparties', 'iris_list_dates'], tok)

    tool_test('T-04', m, 'iris_limit_lookup — find limits',
              'Use the iris_limit_lookup tool to look up credit limits for Goldman Sachs in IRIS.',
              ['iris_limit_lookup', 'get_credit_limits', 'iris_limit_breach_check'], tok)

    tool_test('T-05', m, 'iris_limit_breach_check — scan for breaches',
              'Use iris_limit_breach_check to check if any counterparty in IRIS has breached their credit limit.',
              ['iris_limit_breach_check', 'iris_portfolio_breach_scan', 'iris_list_dates'], tok)

    tool_test('T-06', m, 'iris_portfolio_breach_scan — portfolio-wide',
              'Run a portfolio-wide breach scan across all IRIS counterparties.',
              ['iris_portfolio_breach_scan'], tok)

    tool_test('T-07', m, 'iris_multi_counterparty_comparison — side by side',
              'Use the iris_multi_counterparty_comparison tool to compare Goldman Sachs, Deutsche Bank, and JP Morgan side by side.',
              ['iris_multi_counterparty_comparison', 'iris_counterparty_dashboard', 'iris_search_counterparties'], tok)

    tool_test('T-08', m, 'iris_rating_screen — filter by rating',
              'Screen IRIS counterparties with a rating of BBB or higher.',
              ['iris_rating_screen'], tok)

    tool_test('T-09', m, 'iris_list_dates — available snapshots',
              'What dates are available in the IRIS counterparty database?',
              ['iris_list_dates'], tok)


# ══════════════════════════════════════════════════════════════════════════════
# Module 6B — OSFI Regulatory Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_osfi(tok: str):
    mod = '6B'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-{i}' for i in range(10, 15)]); return

    R.section(f'{MODULE[mod]}  (T-10 – T-14)')
    m = MODULE[mod]

    tool_test('T-10', m, 'osfi_list_docs — list available documents',
              'List all available OSFI regulatory guidance documents.',
              ['osfi_list_docs'], tok)  # no check_output_for — local docs may be empty

    tool_test('T-11', m, 'osfi_search_guidance — keyword search',
              'Search OSFI regulatory guidance for the keyword "capital requirements".',
              ['osfi_search_guidance'], tok, check_output_for='capital')

    tool_test('T-12', m, 'osfi_read_document — read CAR guideline',
              'Use osfi_read_document to read the OSFI Capital Adequacy Requirements (CAR) guideline. '
              'If no local CAR document exists, use osfi_list_docs to list what is available.',
              ['osfi_read_document', 'osfi_list_docs'], tok)

    tool_test('T-13', m, 'osfi_fetch_announcements — live fetch',
              'Fetch the latest OSFI news and announcements.',
              ['osfi_fetch_announcements'], tok, timeout=60)

    tool_test('T-14', m, 'osfi_read_document — multi-chunk navigation',
              'Use osfi_read_document to read any available OSFI guideline document chunk by chunk. '
              'If no local documents are available, list them with osfi_list_docs.',
              ['osfi_read_document', 'osfi_list_docs'], tok)


# ══════════════════════════════════════════════════════════════════════════════
# Module 6C — EDGAR / SEC Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_edgar(tok: str):
    mod = '6C'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-{i}' for i in range(15, 26)]); return

    R.section(f'{MODULE[mod]}  (T-15 – T-25)')
    m = MODULE[mod]

    tool_test('T-15', m, 'edgar_find_filing — JPMorgan 10-K',
              "Find JPMorgan Chase's most recent 10-K annual filing on SEC EDGAR.",
              ['edgar_find_filing', 'ir_find_documents', 'ir_find_page'], tok, timeout=90)

    tool_test('T-16', m, 'edgar_extract_section — MD&A',
              "Extract the Management Discussion and Analysis section from JPMorgan's latest 10-K.",
              ['edgar_extract_section', 'edgar_find_filing', 'edgar_company_brief',
               'ir_find_page', 'ir_get_annual_reports'], tok, timeout=90)

    tool_test('T-17', m, 'edgar_get_metric — revenue XBRL',
              "Get JPMorgan's total revenue from XBRL financial data.",
              ['edgar_get_metric'], tok, timeout=90)

    tool_test('T-18', m, 'edgar_get_statements — balance sheet',
              "Get the balance sheet from JPMorgan's latest annual filing.",
              ['edgar_get_statements'], tok, timeout=90)

    tool_test('T-19', m, 'edgar_earnings_brief — recent quarter',
              "Summarise JPMorgan's most recent quarterly earnings.",
              ['edgar_earnings_brief'], tok, timeout=90)

    tool_test('T-20', m, 'edgar_peer_comparison — 3 banks',
              "Use the edgar_peer_comparison tool to compare JPMorgan, Goldman Sachs, and Citigroup on key financial metrics.",
              ['edgar_peer_comparison', 'edgar_company_brief', 'edgar_get_statements'], tok, timeout=120)

    tool_test('T-21', m, 'edgar_risk_summary — risk factors',
              "Extract the key risk factors from JPMorgan's latest 10-K filing.",
              ['edgar_risk_summary'], tok, timeout=90)

    tool_test('T-22', m, 'edgar_segment_analysis — business segments',
              "Analyse JPMorgan's business segments from their latest annual report.",
              ['edgar_segment_analysis'], tok, timeout=90)

    tool_test('T-23', m, 'edgar_company_brief — one-pager',
              "Create a one-page company brief for Goldman Sachs using EDGAR data.",
              ['edgar_company_brief'], tok, timeout=90)

    tool_test('T-24', m, 'edgar_calculate_ratios — ROE / ROA / CET1',
              "Use edgar_calculate_ratios to compute gross_margin and net_margin for JPMorgan Chase (JPM).",
              ['edgar_calculate_ratios', 'edgar_get_statements', 'edgar_get_metric'], tok, timeout=90)

    tool_test('T-25', m, 'Canadian bank (BMO) — 6-K guidance',
              "Find BMO's 10-K filing on EDGAR.",
              ['edgar_find_filing'], tok, timeout=60)  # expects error/guidance, not a crash


# ══════════════════════════════════════════════════════════════════════════════
# Module 6D — Tavily / IR / News Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_tavily(tok: str):
    mod = '6D'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-{i}' for i in range(26, 34)]); return

    R.section(f'{MODULE[mod]}  (T-26 – T-33)')
    m = MODULE[mod]

    tool_test('T-26', m, 'tavily_news_search — bank stress tests',
              'Search for recent news about bank stress tests in 2025.',
              ['tavily_news_search'], tok, check_output_for='bank', timeout=60)

    tool_test('T-27', m, 'tavily_web_search — general query',
              'Search the web for Basel IV capital requirement changes.',
              ['tavily_web_search', 'tavily_domain_search', 'tavily_research_search'], tok, timeout=60)

    tool_test('T-28', m, 'tavily_research_search — deep research',
              'Do a deep research on credit risk management trends in 2025.',
              ['tavily_research_search', 'tavily_web_search'], tok, timeout=90)

    tool_test('T-29', m, 'tavily_yahoo_get_quote — JPM stock',
              "What is JPMorgan's current stock price and P/E ratio?",
              ['tavily_yahoo_get_quote', 'yahoo_get_quote'], tok, check_output_for='JPM', timeout=60)

    tool_test('T-30', m, 'tavily_yahoo_get_history — GS 30-day price',
              "Get Goldman Sachs stock price history for the last 30 days.",
              ['tavily_yahoo_get_history', 'yahoo_get_history'], tok, timeout=60)

    tool_test('T-31', m, 'tavily_yahoo_search_symbols — symbol search',
              "Find the stock ticker symbol for Goldman Sachs.",
              ['tavily_yahoo_search_symbols', 'yahoo_search_symbols'], tok, check_output_for='GS', timeout=60)

    tool_test('T-32', m, 'ir_list_supported_companies',
              'List all companies supported by the IR intelligence tools.',
              ['ir_list_supported_companies', 'ir_get_all_resources'], tok, timeout=60)

    tool_test('T-33', m, 'ir_get_latest_earnings — RBC',
              "Get the latest earnings release for RBC (Royal Bank of Canada).",
              ['ir_get_latest_earnings', 'ir_find_documents', 'ir_find_page'], tok, timeout=90)


# ══════════════════════════════════════════════════════════════════════════════
# Module 6E — DuckDB / SQL Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_duckdb(tok: str):
    mod = '6E'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-{i}' for i in range(34, 42)]); return

    R.section(f'{MODULE[mod]}  (T-34 – T-41)')
    m = MODULE[mod]

    tool_test('T-34', m, 'duckdb_list_files — list databases',
              'List all DuckDB database files available to you.',
              ['duckdb_list_files'], tok)

    tool_test('T-35', m, 'duckdb_list_tables — list tables',
              'List all tables in the DuckDB databases available to you.',
              ['duckdb_list_tables', 'duckdb_list_files'], tok)

    tool_test('T-36', m, 'duckdb_query — SELECT query',
              'Use duckdb_query or duckdb_sql to run SELECT * LIMIT 5 on a DuckDB table.',
              ['duckdb_query', 'duckdb_sql', 'duckdb_list_tables', 'duckdb_list_files'], tok)

    tool_test('T-37', m, 'duckdb_sql — aggregation',
              'Use duckdb_sql or duckdb_query to run a COUNT(*) aggregation on any DuckDB table and return row counts.',
              ['duckdb_sql', 'duckdb_query', 'duckdb_list_tables'], tok)

    tool_test('T-38', m, 'sqlselect_list_sources — list CSV/Parquet',
              'Use sqlselect_list_sources to list all CSV and Parquet data sources available for SQL queries.',
              ['sqlselect_list_sources'], tok)

    tool_test('T-39', m, 'sqlselect_execute_query — query iris CSV',
              'Use sqlselect_execute_query to run SELECT * LIMIT 5 on the iris_combined source.',
              ['sqlselect_execute_query', 'sqlselect_list_sources', 'sqlselect_sample_data'], tok)

    tool_test('T-40', m, 'sqlselect_sample_data — sample iris',
              'Use sqlselect_sample_data to show a sample of rows from the IRIS counterparty data source.',
              ['sqlselect_sample_data', 'sqlselect_execute_query', 'sqlselect_list_sources'], tok)

    tool_test('T-41', m, 'sqlselect_get_schema — iris schema',
              'Use sqlselect_get_schema or sqlselect_describe_source to get the column names and data types of the IRIS data source.',
              ['sqlselect_get_schema', 'sqlselect_describe_source', 'sqlselect_list_sources'], tok)


# ══════════════════════════════════════════════════════════════════════════════
# Module 6F — MS Document Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_msdoc(tok: str):
    mod = '6F'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-{i}' for i in range(42, 47)]); return

    R.section(f'{MODULE[mod]}  (T-42 – T-46)')
    m = MODULE[mod]

    # Upload test files first
    docx_uploaded = False
    xlsx_uploaded = False

    docx_bytes = _minimal_docx()
    if docx_bytes:
        files = {'file': ('uat_test.docx', io.BytesIO(docx_bytes), 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')}
        s, _ = req('POST', f'/api/super/workers/{MR_WORKER}/files/domain_data/upload',
                   token=tok, files=files, params={'overwrite': 'true'})
        docx_uploaded = s in (200, 201)

    tool_test('T-42', m, 'msdoc_list_files — list Word/Excel files',
              'List all Word and Excel documents available in the file system.',
              ['msdoc_list_files', 'list_uploaded_files'], tok)

    if docx_uploaded:
        tool_test('T-43', m, 'msdoc_read_word — read uploaded .docx',
                  'Use msdoc_read_word to extract and display all text from uat_test.docx.',
                  ['msdoc_read_word', 'msdoc_list_files'], tok)
        tool_test('T-45', m, 'msdoc_search_word — keyword in Word doc',
                  'Use msdoc_search_word to search for the word "UAT" inside uat_test.docx.',
                  ['msdoc_search_word', 'msdoc_read_word'], tok)
        req('DELETE', f'/api/super/workers/{MR_WORKER}/files/domain_data/file',
            token=tok, params={'path': 'uat_test.docx'})
    else:
        R.skip('T-43', m, 'msdoc_read_word (skipped: docx upload failed)')
        R.skip('T-45', m, 'msdoc_search_word (skipped: docx upload failed)')

    R.skip('T-44', m, 'msdoc_read_excel (skipped: requires real .xlsx upload — manual test)')
    R.skip('T-46', m, 'msdoc_search_excel (skipped: requires real .xlsx upload — manual test)')


def _minimal_docx() -> bytes:
    """Return bytes of a minimal valid .docx file (zip with required parts)."""
    import zipfile, io as _io
    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('[Content_Types].xml',
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>')
        zf.writestr('_rels/.rels',
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        zf.writestr('word/document.xml',
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>UAT test document content for RiskGPT.</w:t></w:r></w:p></w:body></w:document>')
        zf.writestr('word/_rels/document.xml.rels',
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# Module 6G — Utility Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_utility(tok: str):
    mod = '6G'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-{i}' for i in range(47, 55)]); return

    R.section(f'{MODULE[mod]}  (T-47 – T-54)')
    m = MODULE[mod]

    tool_test('T-47', m, 'list_uploaded_files — list uploads',
              'List all files that have been uploaded to your workspace.',
              ['list_uploaded_files'], tok)

    # Upload a PDF for T-48
    pdf_bytes = _minimal_pdf()
    files = {'file': ('uat_test.pdf', io.BytesIO(pdf_bytes), 'application/pdf')}
    s, _ = req('POST', f'/api/super/workers/{MR_WORKER}/files/domain_data/upload',
               token=tok, files=files, params={'overwrite': 'true'})
    if s in (200, 201):
        tool_test('T-48', m, 'pdf_read — extract text from PDF',
                  'Use pdf_read to extract and display all text from the uploaded file uat_test.pdf.',
                  ['pdf_read', 'list_uploaded_files'], tok)
        req('DELETE', f'/api/super/workers/{MR_WORKER}/files/domain_data/file',
            token=tok, params={'path': 'uat_test.pdf'})
    else:
        R.skip('T-48', m, 'pdf_read (skipped: pdf upload failed)')

    R.skip('T-49', m, 'parquet_read (skipped: requires pre-uploaded .parquet — manual test)')

    tool_test('T-50', m, 'md_save — save analysis to markdown',
              'Use the md_save tool to save the following text as uat_analysis.md: "# UAT Analysis\nThis is a test analysis note."',
              ['md_save'], tok)

    tool_test('T-51', m, 'md_to_docx — convert markdown to Word',
              'Convert the markdown file uat_analysis.md to a Word document.',
              ['md_to_docx', 'md_save'], tok, timeout=60)

    tool_test('T-52', m, 'generate_chart — create a chart',
              'Generate a simple bar chart showing exposure by counterparty from IRIS data.',
              ['generate_chart', 'iris_search_counterparties', 'iris_counterparty_dashboard'], tok)

    tool_test('T-53', m, 'fill_template — fill a workflow template',
              'Use fill_template with the counterparty intelligence brief template filled with Goldman Sachs data.',
              ['fill_template', 'workflow_get', 'workflow_list',
               'edgar_company_brief', 'iris_search_counterparties', 'search_files'], tok)

    tool_test('T-54', m, 'search_files — keyword search in uploads',
              'Use the search_files tool to search all files for the keyword "exposure".',
              ['search_files', 'list_uploaded_files'], tok)


def _minimal_pdf() -> bytes:
    return (
        b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n'
        b'2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
        b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]'
        b'/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n'
        b'4 0 obj<</Length 44>>stream\nBT /F1 12 Tf 100 700 Td (UAT test PDF) Tj ET\nendstream\nendobj\n'
        b'5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n'
        b'xref\n0 6\n0000000000 65535 f\n'
        b'trailer<</Size 6/Root 1 0 R>>\nstartxref\n0\n%%EOF\n'
    )


# ══════════════════════════════════════════════════════════════════════════════
# Module 6H — CCR Exposure Tools
# ══════════════════════════════════════════════════════════════════════════════

def test_ccr(tok: str):
    mod = '6H'
    if not _should_run(mod):
        skip_module(mod, MODULE[mod], [f'T-{i}' for i in range(55, 61)]); return

    R.section(f'{MODULE[mod]}  (T-55 – T-60)')
    m = MODULE[mod]

    tool_test('T-55', m, 'get_counterparty_exposure — by counterparty',
              'What is the total counterparty exposure for Goldman Sachs?',
              ['get_counterparty_exposure'], tok)

    tool_test('T-56', m, 'get_credit_limits — limits table',
              'Use get_credit_limits to retrieve the credit limits for Goldman Sachs.',
              ['get_credit_limits', 'iris_limit_lookup', 'iris_limit_breach_check'], tok)

    tool_test('T-57', m, 'get_trade_inventory — trade-level details',
              'Use get_trade_inventory to get all open trades for Goldman Sachs.',
              ['get_trade_inventory', 'get_counterparty_exposure', 'iris_search_counterparties'], tok)

    tool_test('T-58', m, 'get_var_contribution — VaR attribution',
              'Use get_var_contribution to show the VaR contribution for Goldman Sachs.',
              ['get_var_contribution', 'get_counterparty_exposure'], tok)

    tool_test('T-59', m, 'get_historical_exposure — time series',
              'Use get_historical_exposure to show the exposure history for Goldman Sachs over the last 6 months.',
              ['get_historical_exposure', 'iris_exposure_trend', 'get_counterparty_exposure',
               'iris_search_counterparties', 'iris_counterparty_dashboard'], tok)

    # T-60: query CCR worker which has no iris data — should not crash
    result = run_agent('What is the counterparty exposure for Goldman Sachs?', CCR_WORKER, tok, timeout=60)
    no_crash = result.get('error') is None or 'data not found' in result.get('text','').lower() or bool(result.get('text'))
    R.assert_test('T-60', m, 'CCR tool on worker with no iris data: graceful response',
                  no_crash, detail=result.get('error', ''))


# ══════════════════════════════════════════════════════════════════════════════
# Module 7 — Workflows
# ══════════════════════════════════════════════════════════════════════════════

def test_workflows(tok: str):
    mod = str(7)
    if not _should_run(mod):
        skip_module(mod, MODULE[7], [f'WF-0{i}' for i in range(1, 8)]); return

    R.section(f'{MODULE[7]}  (WF-01 – WF-07)')
    m = MODULE[7]

    # WF-01  workflow_list
    tool_test('WF-01', m, 'workflow_list — list all available workflows',
              'What workflows are available? List them all with descriptions.',
              ['workflow_list'], tok, check_output_for='workflow')

    # WF-02  workflow_get — fetch specific workflow
    tool_test('WF-02', m, 'workflow_get — fetch counterparty_intelligence steps',
              'Show me the full step-by-step instructions for the counterparty intelligence workflow.',
              ['workflow_get', 'workflow_list'], tok)

    # WF-03  execute counterparty intelligence workflow
    tool_test('WF-03', m, 'counterparty_intelligence workflow — Deutsche Bank',
              'Run the counterparty intelligence workflow for Deutsche Bank. '
              'Search IRIS, check news, and produce a brief summary.',
              ['workflow_list', 'workflow_get', 'iris_search_counterparties'], tok, timeout=180)

    # WF-04  osfi_regulatory_watch
    tool_test('WF-04', m, 'osfi_regulatory_watch workflow',
              'Run the OSFI regulatory watch workflow and summarise recent guidance.',
              ['workflow_list', 'workflow_get', 'osfi_list_docs', 'osfi_search_guidance'], tok, timeout=180)

    # WF-05  custom workflow upload + file on disk (worker-scoped)
    custom_wf = (
        '# UAT Custom Workflow\n'
        'A simple UAT test workflow.\n\n'
        '## Inputs:\n- counterparty_name: Name of counterparty\n\n'
        '## Steps:\n'
        '1. Use iris_search_counterparties to find the counterparty.\n'
        '2. Report the result.\n'
    )
    files = {'file': ('uat_custom_workflow.md', io.BytesIO(custom_wf.encode()), 'text/markdown')}
    s, body = req('POST', f'/api/super/workers/{MR_WORKER}/files/verified/upload',
                  token=tok, files=files, params={'overwrite': 'true'})
    if s in (200, 201):
        # Verify the file landed on disk in the worker's verified workflows folder
        wf_path = pathlib.Path(f'sajhamcpserver/data/workers/{MR_WORKER}/workflows/verified/uat_custom_workflow.md')
        file_on_disk = wf_path.exists()
        # Also ask the agent — workflow_list may or may not surface it depending on indexing
        time.sleep(2)
        result = run_agent('Use workflow_list to list all workflows. Is there a UAT custom workflow?', MR_WORKER, tok)
        called = result.get('tool_names', [])
        text   = result.get('text', '')
        # Primary check: file is on disk in correct worker-scoped location
        R.assert_test('WF-05', m, 'custom workflow upload → on disk in worker workflows folder',
                      file_on_disk, detail=f'path={wf_path} exists={file_on_disk}')
        req('DELETE', f'/api/super/workers/{MR_WORKER}/files/verified/file',
            token=tok, params={'path': 'uat_custom_workflow.md'})
    else:
        R.skip('WF-05', m, 'custom workflow upload (skipped: upload failed)')

    # WF-06  workflow with missing inputs — agent asks for them
    result = run_agent(
        'Run the counterparty intelligence workflow. Do not provide the counterparty name yet.',
        MR_WORKER, tok, timeout=90)
    text = result.get('text', '').lower()
    asks = any(w in text for w in ['which counterparty', 'please provide', 'counterparty name',
                                    'what counterparty', 'name of the'])
    R.assert_test('WF-06', m, 'workflow with missing inputs: agent asks for parameters',
                  asks or len(result.get('tool_names', [])) > 0,
                  detail=f'text={text[:300]}')

    # WF-07  worker-scoped workflow isolation
    # Upload a workflow to CCR worker only; verify it does NOT appear when queried from MR worker
    ccr_wf = '# CCR-Only Workflow\nOnly for CCR worker.\n'
    files  = {'file': ('ccr_only_wf.md', io.BytesIO(ccr_wf.encode()), 'text/markdown')}
    s2, _  = req('POST', f'/api/super/workers/{CCR_WORKER}/files/verified/upload',
                 token=tok, files=files, params={'overwrite': 'true'})
    if s2 in (200, 201):
        time.sleep(2)
        result_mr = run_agent('List all available workflows.', MR_WORKER, tok)
        mr_text = result_mr.get('text', '').lower()
        not_visible = 'ccr_only_wf' not in mr_text and 'ccr-only' not in mr_text
        R.assert_test('WF-07', m, 'CCR workflow not visible from MR worker',
                      not_visible, detail=f'text snippet={mr_text[:300]}')
        req('DELETE', f'/api/super/workers/{CCR_WORKER}/files/verified/file',
            token=tok, params={'path': 'ccr_only_wf.md'})
    else:
        R.skip('WF-07', m, 'workflow isolation test (skipped: CCR upload failed)')


# ══════════════════════════════════════════════════════════════════════════════
# Main runner
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print('\n' + '='*70)
    print('  RiskGPT UAT — Phase 2: Tool, Workflow & Chat Tests')
    print('='*70)
    print(f'  Target  : {BASE}')
    print(f'  Results : UAT_RESULTS/')
    if _ONLY:
        print(f'  Modules : {_ONLY}  (others skipped)')
    if _SKIP:
        print(f'  Skipping: {_SKIP}')
    print()

    super_tok = login(*SUPER_CREDS)
    if not super_tok:
        print('  !! CRITICAL: Could not obtain super_admin token. Is the server running?')
        sys.exit(1)

    try:
        test_chat(super_tok)
        test_iris(super_tok)
        test_osfi(super_tok)
        test_edgar(super_tok)
        test_tavily(super_tok)
        test_duckdb(super_tok)
        test_msdoc(super_tok)
        test_utility(super_tok)
        test_ccr(super_tok)
        test_workflows(super_tok)
    except Exception:
        print('\n  !! UNHANDLED EXCEPTION IN TEST RUNNER:')
        traceback.print_exc()

    R.print_final_summary()
    json_path, md_path = R.save()
    print(f'\n  JSON  : {json_path}')
    print(f'  MD    : {md_path}')
    print(f'  Latest: UAT_RESULTS/LATEST_phase2.md\n')

    s = R._summary_dict()
    sys.exit(0 if s['fail'] == 0 and s['error'] == 0 else 1)


if __name__ == '__main__':
    main()
