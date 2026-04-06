# REQ-09 UAT Plan — Generic Document Retrieval (BM25)

**Date:** 2026-04-05  
**Author:** Saad Ahmed  
**Requirement:** REQ-09 — BM25 full-text search across domain_data + my_data  
**Tool:** `document_search`  
**Library:** rank_bm25 v0.2.2, pdfplumber v0.11.9  
**Test Method:** Direct SAJHA API calls — no LLM

---

## Test Environment
- SAJHA server: `http://127.0.0.1:3002`
- API key: `sja_full_access_admin`
- Index root: `data/workers/w-market-risk/domain_data` + `my_data/risk_agent`

---

## CI Tests (Code-level, no server required)

| ID | Test | Expected |
|----|------|----------|
| CI-BM25-01 | Import `DocumentSearchTool` class | No ImportError |
| CI-BM25-02 | `_chunk_text()` with 100 words → 1 chunk | `len == 1` |
| CI-BM25-03 | `_chunk_text()` with 3000 words → 2 chunks | `len == 2` |
| CI-BM25-04 | `_extract_text()` on `.md` file → returns str | `isinstance(result, str)` |
| CI-BM25-05 | `_extract_excerpt()` with matching token → excerpt contains token | `token in excerpt` |
| CI-BM25-06 | `_extract_excerpt()` with no match → returns beginning of text | `len(result) <= 360` |
| CI-BM25-07 | `_build_index()` on temp dir with 2 `.md` files → returns BM25 + 2 chunks | `bm25 is not None`, `len(chunks) == 2` |
| CI-BM25-08 | BM25 score for exact match term > 0 | `score > 0` |
| CI-BM25-09 | `force_refresh=True` rebuilds cache (timestamp resets) | `new_ts >= old_ts` |
| CI-BM25-10 | `file_types=[".md"]` filter excludes `.csv` chunks | no `.csv` in results |

## BT Tests (API, requires running SAJHA server)

| ID | Test | Expected |
|----|------|----------|
| BT-BM25-01 | `document_search` with query="capital adequacy" | `total_results >= 1`, OSFI docs matched |
| BT-BM25-02 | `document_search` with `top_k=3` | `len(results) <= 3` |
| BT-BM25-03 | `document_search` with `top_n_full_content=1` | `results[0]` has `full_content` key |
| BT-BM25-04 | `document_search` with `force_refresh=true` | `cache_age_seconds == 0` |
| BT-BM25-05 | `document_search` with `file_types=[".md"]` | all results have `.md` extension |
| BT-BM25-06 | `document_search` with nonsense query "xyzzy12345" | `total_results == 0` |
| BT-BM25-07 | OSFI tools disabled — `osfi_search_guidance` call returns tool-not-found | error or disabled response |

---

## Pass Criteria
- All CI tests: PASS
- BT-BM25-01 through BT-BM25-06: PASS (requires server)
- BT-BM25-07: PASS (OSFI retired)
