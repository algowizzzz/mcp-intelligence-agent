# REQ-09 UAT Results — Generic Document Retrieval (BM25)

**Date:** 2026-04-05  
**Executed by:** Claude Code (Saad Ahmed session)  
**Environment:** Local Mac, venv Python (rank_bm25 v0.2.2, pdfplumber v0.11.9)

---

## CI Test Results (10/10 PASS)

| ID | Test | Result | Notes |
|----|------|--------|-------|
| CI-BM25-01 | Import DocumentSearchTool | ✅ PASS | |
| CI-BM25-02 | 100 words → 1 chunk | ✅ PASS | |
| CI-BM25-03 | 3000 words → 2 chunks (2500-word boundary) | ✅ PASS | |
| CI-BM25-04 | `.md` text extraction | ✅ PASS | |
| CI-BM25-05 | Excerpt contains matching token | ✅ PASS | |
| CI-BM25-06 | No-match excerpt returns beginning of text | ✅ PASS | |
| CI-BM25-07 | `_build_index()` on 2-file temp dir → BM25 + 2 chunks | ✅ PASS | |
| CI-BM25-08 | BM25 ranks matching doc higher than non-matching | ✅ PASS | Note: single-doc IDF=0 is expected BM25 behaviour; test uses 2 docs |
| CI-BM25-09 | `force_refresh=True` resets cache timestamp | ✅ PASS | |
| CI-BM25-10 | `file_types=[".md"]` filter excludes .csv chunks | ✅ PASS | |

**CI Score: 10/10 PASS**

---

## BT Test Results (requires running SAJHA server)

| ID | Test | Result | Notes |
|----|------|--------|-------|
| BT-BM25-01 | Query "capital adequacy" → results from domain_data | ⬜ PENDING | Run when server is up |
| BT-BM25-02 | `top_k=3` → ≤ 3 results | ⬜ PENDING | |
| BT-BM25-03 | `top_n_full_content=1` → full_content in result[0] | ⬜ PENDING | |
| BT-BM25-04 | `force_refresh=true` → cache_age_seconds == 0 | ⬜ PENDING | |
| BT-BM25-05 | `file_types=[".md"]` → only .md results | ⬜ PENDING | |
| BT-BM25-06 | Nonsense query "xyzzy12345" → 0 results | ⬜ PENDING | |
| BT-BM25-07 | `osfi_search_guidance` call → tool disabled error | ⬜ PENDING | |

---

## Implementation Notes

- **CI-BM25-08 design note**: BM25 IDF for a term is ~0 when that term appears in all documents (log((N-n+0.5)/(n+0.5)) → log(0) clamped). This is correct BM25 behaviour; test was updated to use 2 documents so the ranking contrast is observable.
- **OSFI retirement**: All 4 OSFI tool configs set to `"enabled": false` with `"retired_by": "document_search (REQ-09)"`. OSFI `.md` files remain in `domain_data/osfi/` and are indexed by BM25 automatically.
- **New libraries**: `rank_bm25 v0.2.2`, `pdfplumber v0.11.9` installed in venv. Added to requirements.txt (below).

---

## Overall Status

**CI: 10/10 PASS**  
**BT: 0/7 executed (server not running)**  
**Ready for BT execution on local Mac with server running.**
