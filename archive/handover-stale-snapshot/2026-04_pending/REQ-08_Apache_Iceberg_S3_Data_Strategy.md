# REQ-08 — Apache Iceberg & S3 Data Strategy
**Status:** Pending — Architecture Review
**Version:** 1.0
**Date:** 2026-04-04
**Scope:** Evaluate Apache Iceberg as a replacement/enhancement for the current filesystem-based data layer, define the S3-first data strategy for domain data and uploads, and establish the right boundary between Iceberg (analytical), S3 (object storage), and PostgreSQL (operational — REQ-07).

---

## 1. Background: Current Data Architecture

### 1.1 How Data Is Currently Stored

All non-database data lives on the local filesystem of the server running `sajhamcpserver`:

```
sajhamcpserver/data/
  workers/
    w-market-risk/
      domain_data/
        counterparties/
          trades.json        # Trade inventory
          exposure.json      # Current exposure
          credit_limits.json # Limits by counterparty
          var.json           # VaR by counterparty
          historical/        # Historical snapshots (daily)
        duckdb/
          duckdb_analytics.db  # DuckDB analytical database
        uploads/             # User-uploaded files (CSV, PDF, DOCX, etc.)
        msdocs/              # Generated Word documents
      my_data/
        risk_agent/          # User-scoped uploads
      verified_workflows/    # Curated .md workflow files
      my_workflows/          # User-created .md workflow files
  osfi/                      # OSFI regulatory documents
  iris/                      # IRIS CCR reference data
    iris_combined.csv        # Counterparty credit reference (large)
```

### 1.2 Current Analytical Query Pattern

The platform uses **DuckDB** for analytical queries against:
- The local filesystem files (CSV, JSON, Parquet)
- In-memory datasets loaded from the above

DuckDB tools (`duckdb_query`, `duckdb_olap_advanced`, etc.) query against `duckdb_analytics.db` which references local files via DuckDB's native file reading.

### 1.3 Limitations of Current Architecture

| Limitation | Impact |
|---|---|
| Local filesystem only | No horizontal scaling; single server is a bottleneck |
| No data versioning | Overwriting `trades.json` loses history silently |
| No schema evolution | Adding a column to `trades.json` is a manual find-and-replace |
| Poor query performance on large data | Full-file scans on large JSONL/CSV files |
| No partitioning | IRIS CSV (large, growing) scanned entirely for every query |
| No time travel | Cannot query "what was the exposure on March 1?" |
| No concurrent write safety | Two workers writing to the same file simultaneously → corruption |
| No fine-grained access control | File-level permissions only |

---

## 2. The Proposed Architecture: S3 + Iceberg + DuckDB + PostgreSQL

```
┌─────────────────────────────────────────────────────────────────────┐
│                         B-Pulse Data Platform                       │
│                                                                     │
│  ┌────────────────┐   ┌─────────────────┐   ┌──────────────────┐  │
│  │  PostgreSQL    │   │  Apache Iceberg  │   │   S3 (Object     │  │
│  │  (REQ-07)      │   │  (Analytical)   │   │   Storage)       │  │
│  │                │   │                 │   │                  │  │
│  │  - Users       │   │  - Trade data   │   │  - Documents     │  │
│  │  - Workers     │   │  - Exposure     │   │  - Uploads       │  │
│  │  - Threads     │   │  - VaR series   │   │  - Workflows     │  │
│  │  - Audit log   │   │  - IRIS CCR     │   │  - Charts        │  │
│  │  - Auth        │   │  - Market data  │   │  - Generated     │  │
│  │  - Connectors  │   │                 │   │    reports       │  │
│  └────────────────┘   └────────┬────────┘   └──────┬───────────┘  │
│                                │                    │              │
│                                │ (Iceberg reads     │              │
│                                │  Parquet from S3)  │              │
│                                ▼                    ▼              │
│                         ┌─────────────────────────────────┐        │
│                         │       DuckDB Query Engine        │        │
│                         │  (reads Iceberg via duckdb-      │        │
│                         │   iceberg extension + S3 direct) │        │
│                         └──────────────┬──────────────────┘        │
│                                        │                           │
│                                        ▼                           │
│                              SAJHA MCP Tool Layer                  │
│                         (duckdb_query, analytics tools)            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Should You Use Apache Iceberg?

### 3.1 What Iceberg Provides

Apache Iceberg is an open table format for large analytical datasets stored in object storage (S3, GCS, Azure Blob). Key capabilities:

| Feature | Value for B-Pulse |
|---|---|
| **ACID transactions** | Safe concurrent writes to trade/exposure data |
| **Schema evolution** | Add columns without rewriting existing data |
| **Time travel** | Query historical state: `SELECT * FROM trades AS OF '2026-01-01'` |
| **Partition evolution** | Change partitioning without rewriting data |
| **File-level statistics** | Skip reading files that don't match filters → 10x–100x faster queries |
| **Hidden partitioning** | Partition by date/counterparty transparently |
| **Snapshot isolation** | Read consistent view while writes are in progress |

### 3.2 Is Iceberg Right for This Use Case?

**YES — Iceberg is a strong fit for:**
- Trade inventory and historical exposure data (daily snapshots, growing over time)
- IRIS CCR reference data (updated daily, queried frequently with filters)
- VaR time series (append-heavy, time-partitioned queries)
- Market data series (if ingested)
- Any dataset that grows continuously and requires historical queries

**NO — Iceberg is overkill for:**
- Small config files (< 1MB) → PostgreSQL
- User-uploaded documents (PDF, DOCX, XLSX) → S3 directly
- Workflow files (.md) → S3 directly
- Single-file reference data updated once per day → S3 + Parquet is sufficient

### 3.3 Iceberg vs Plain Parquet on S3

| Scenario | Plain Parquet | Iceberg |
|---|---|---|
| Data never changes | ✅ Simpler | Overkill |
| Append-only, daily batch | ✅ Partition by date manually | ✅ Better — automatic partitioning |
| Concurrent writes | ❌ No atomic guarantees | ✅ ACID |
| Need time travel | ❌ Must keep old files manually | ✅ Built-in |
| Schema changes expected | ❌ Painful | ✅ Schema evolution |
| Query with DuckDB | ✅ duckdb reads parquet natively | ✅ duckdb-iceberg extension |
| Data < 100MB total | ✅ Fine | Overkill |
| Data > 1GB, growing | ⚠️ Performance degrades | ✅ Designed for this |

**Recommendation:** Use Iceberg for datasets that meet ≥2 of: growing beyond 500MB, updated by multiple processes, require historical queries, schema is expected to evolve. Otherwise, plain Parquet on S3 is sufficient.

---

## 4. Recommended Data Strategy by Dataset

### 4.1 Trade & Exposure Data

**Current:** `trades.json`, `exposure.json`, `credit_limits.json` (local JSON)
**Recommended:** Apache Iceberg table on S3, partitioned by `trade_date` and `worker_id`

```sql
-- Iceberg table definition
CREATE TABLE bpulse_catalog.market_risk.trades (
    trade_id          STRING NOT NULL,
    counterparty_id   STRING NOT NULL,
    instrument_type   STRING,
    notional          DOUBLE,
    mtm               DOUBLE,
    pfe               DOUBLE,
    trade_date        DATE,
    maturity_date     DATE,
    currency          STRING,
    worker_id         STRING NOT NULL,
    loaded_at         TIMESTAMP NOT NULL
)
USING iceberg
PARTITIONED BY (worker_id, months(trade_date))
TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.parquet.compression-codec' = 'zstd'
);
```

**Time travel query example:**
```sql
SELECT * FROM bpulse_catalog.market_risk.trades
VERSION AS OF '2026-03-01T00:00:00'
WHERE counterparty_id = 'ABC' AND worker_id = 'w-market-risk';
```

### 4.2 IRIS CCR Reference Data

**Current:** `data/iris/iris_combined.csv` (referenced in application.properties)
**Recommended:** Iceberg table, partitioned by `reporting_date`

IRIS data is large (100MB+), queried with heavy filters (by counterparty, date range, risk type). Iceberg's file-level statistics will skip unnecessary files, making queries 10–50× faster.

### 4.3 VaR Time Series

**Current:** `var.json` (flat file, entire history in one file)
**Recommended:** Iceberg table, partitioned by `var_date` and `worker_id`

Time-series queries (e.g. "show VaR trend for last 90 days") will benefit from date partitioning — only the relevant files are read.

### 4.4 Documents and User Uploads

**Current:** Local filesystem
**Recommended:** S3 directly (not Iceberg)

Documents (PDF, DOCX, XLSX, CSV) and user uploads are binary files, not columnar data. They go directly to S3 as objects. The file tree metadata (path, size, type, mtime) is stored in PostgreSQL (or a DynamoDB-style key-value store).

```
s3://bpulse-data-{env}/
  workers/
    w-market-risk/
      domain_data/
        counterparties/   ← structured data → Iceberg
        documents/        ← binary files → S3 direct
      uploads/            ← user uploads → S3 direct
      workflows/
        verified/         ← .md files → S3 direct
        my/               ← .md files → S3 direct
  users/
    risk_agent/
      my_data/            ← user uploads → S3 direct
```

### 4.5 Generated Charts and Reports

**Current:** Local filesystem (`data/workers/{id}/charts/`)
**Recommended:** S3 directly

Generated charts (HTML, PNG) and Word/PDF reports are stored as S3 objects with a lifecycle policy (delete after 30 days unless pinned).

---

## 5. DuckDB + Iceberg Integration

DuckDB supports reading Iceberg tables natively via the `duckdb-iceberg` extension. This means existing DuckDB tool queries work with minimal changes:

```python
# Current DuckDB query (reads local CSV):
conn.execute("SELECT * FROM 'sajhamcpserver/data/iris/iris_combined.csv' WHERE counterparty = ?", [cp_id])

# With Iceberg (reads from S3 via catalog):
conn.execute("INSTALL iceberg; LOAD iceberg;")
conn.execute("SET s3_region='us-east-1'; SET s3_access_key_id=...; SET s3_secret_access_key=...;")
conn.execute("SELECT * FROM iceberg_scan('s3://bpulse-data/catalog/iris/') WHERE counterparty = ?", [cp_id])
```

**Catalog options:**

| Catalog | Best For | Setup Complexity |
|---|---|---|
| AWS Glue Data Catalog | AWS deployments | Low — native AWS service |
| REST Catalog (Project Nessie) | Multi-cloud or on-prem | Medium |
| Polaris Catalog (Apache) | Open-source, all clouds | Medium |
| Hive Metastore | Legacy Hadoop environments | High — not recommended |

**Recommendation:** AWS Glue for AWS deployments; Nessie (via Docker) for local development and multi-cloud.

---

## 6. S3 File Server: Replacing Local File Serving

Currently, `agent_server.py` reads files from local paths and streams them to clients. With S3, this changes:

### 6.1 File Access Pattern

**Option A — Pre-signed URLs (Recommended):**

```python
# Agent server generates a pre-signed URL for S3 download
@app.get('/api/fs/{section}/file')
async def fs_file(section: str, path: str, payload = Depends(require_jwt)):
    s3_key = _resolve_s3_key(payload['worker_id'], payload['user_id'], section, path)
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': 'bpulse-data', 'Key': s3_key},
        ExpiresIn=300  # 5 minute expiry
    )
    return {'url': url}
```

Frontend fetches the pre-signed URL directly from S3 for binary files (PDF, DOCX, etc.).

**Option B — Proxy through agent server (current pattern, works for text files):**

Agent server reads from S3 and streams to client. Works well for small files; not ideal for large binaries (adds latency and CPU).

**Recommendation:** Use pre-signed URLs for binary files >100KB; proxy for small text files.

### 6.2 File Upload Pattern

```python
# Upload: client → agent server validates → S3
@app.post('/api/fs/{section}/upload')
async def fs_upload(section: str, file: UploadFile, payload = Depends(require_jwt)):
    # Validate file type and size (as per REQ-01 NFRs)
    s3_key = _resolve_s3_key(payload['worker_id'], payload['user_id'], section, file.filename)
    await s3_client.upload_fileobj(file.file, 'bpulse-data', s3_key)
    # Update file metadata in PostgreSQL
    await insert_file_metadata(...)
    return {'path': file.filename, 'section': section}
```

### 6.3 File Tree from PostgreSQL (not filesystem walk)

Currently, `_build_tree()` in `agent_server.py` walks the local filesystem. With S3, the tree must be driven by PostgreSQL metadata:

```sql
-- File metadata table (in PostgreSQL — REQ-07)
CREATE TABLE file_metadata (
    file_id     BIGSERIAL PRIMARY KEY,
    worker_id   VARCHAR(64) NOT NULL,
    user_id     VARCHAR(64),            -- NULL for shared files
    section     VARCHAR(64) NOT NULL,   -- 'domain_data', 'uploads', etc.
    s3_key      TEXT NOT NULL,          -- Full S3 key
    rel_path    TEXT NOT NULL,          -- Relative path within section
    file_name   VARCHAR(512) NOT NULL,
    mime_type   VARCHAR(128),
    size_bytes  BIGINT,
    is_folder   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by  VARCHAR(64)
);

CREATE INDEX idx_file_meta_tree ON file_metadata(worker_id, section, rel_path);
```

Tree API then queries PostgreSQL:
```python
async def fs_tree(section, worker_id, user_id):
    rows = await db.execute(
        select(FileMetadata)
        .where(FileMetadata.worker_id == worker_id,
               FileMetadata.section == section)
        .order_by(FileMetadata.rel_path)
    )
    return build_tree_from_rows(rows)
```

---

## 7. Migration Path from Local Filesystem to S3

### Phase 1 — S3 Infrastructure (Week 1)

1. Create S3 bucket: `bpulse-data-{env}` (dev/staging/prod variants)
2. Configure bucket policy:
   - Versioning enabled
   - Server-side encryption (SSE-S3 or SSE-KMS)
   - Lifecycle rules: delete incomplete multipart uploads after 7 days
   - No public access
3. Create IAM role with minimal S3 permissions for the application:
   ```json
   {
     "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"],
     "Resource": ["arn:aws:s3:::bpulse-data-*", "arn:aws:s3:::bpulse-data-*/*"]
   }
   ```
4. Add `boto3` to application dependencies: `pip install boto3`

### Phase 2 — Document Files to S3 (Week 2)

1. Implement S3 file service layer (`sajha/storage/s3_client.py`)
2. Migrate `domain_data/` documents and uploads to S3 (batch sync via `aws s3 sync`)
3. Add `file_metadata` table to PostgreSQL (REQ-07)
4. Update file tree API to read from PostgreSQL instead of filesystem walk
5. Update file upload endpoint to write to S3
6. Update file read endpoint to generate pre-signed URLs

### Phase 3 — Structured Data to Iceberg (Week 3–4)

1. Set up Iceberg catalog (AWS Glue or Nessie)
2. Install `duckdb-iceberg` extension in sandbox and production DuckDB
3. Create Iceberg tables for trades, exposure, VaR, IRIS CCR
4. Write data loading pipeline: JSON/CSV source → Parquet → Iceberg table
5. Update DuckDB tool queries to use Iceberg tables instead of local files
6. Validate query results match original data exactly
7. Archive local files to S3 Glacier after successful migration

### Phase 4 — Validation & Cutover (Week 5)

1. Run dual-read mode: both local files and S3/Iceberg return same results
2. Performance benchmark: confirm Iceberg queries are ≥2× faster on IRIS and trade data
3. Disable local file fallback
4. Update `application.properties`: remove local data paths

---

## 8. Cost Estimation (AWS)

For a typical deployment with ~10 users and moderate data volume:

| Service | Estimated Monthly Cost | Notes |
|---|---|---|
| S3 storage (100GB) | ~$2.30 | Standard tier |
| S3 requests (1M GET, 100K PUT) | ~$5 | Higher for heavy use |
| AWS Glue Data Catalog | $1/month for 1M objects | Very low |
| DuckDB (in-process) | $0 | No additional cost |
| Total S3/Iceberg layer | ~$10/month | Very affordable |
| PostgreSQL RDS (db.t3.medium) | ~$60/month | REQ-07 |
| **Total** | **~$70/month** | Development/small production |

For production with significant data volumes (>1TB Iceberg):
- S3 Intelligent-Tiering reduces storage cost for infrequently accessed historical data
- Iceberg compaction (small file merging) should be scheduled weekly to control file count

---

## 9. DuckDB Tool Changes Required

The following DuckDB tools need updating to use S3/Iceberg:

| Tool | Current Data Source | Updated Data Source |
|---|---|---|
| `duckdb_query` | Local `duckdb_analytics.db` | S3 Parquet + Iceberg tables |
| `duckdb_olap_trades` | `trades.json` local | Iceberg `market_risk.trades` |
| `duckdb_olap_exposure` | `exposure.json` local | Iceberg `market_risk.exposure` |
| `duckdb_olap_var` | `var.json` local | Iceberg `market_risk.var_series` |
| `iris_ccr_tools` | `iris_combined.csv` local | Iceberg `reference.iris_ccr` |
| `sql_select` | Local DuckDB file | S3 Parquet via DuckDB |

The DuckDB connection configuration must be updated:
```python
import duckdb

conn = duckdb.connect()
conn.install_extension('iceberg')
conn.load_extension('iceberg')
conn.execute("SET s3_region=?", [os.getenv('AWS_REGION', 'us-east-1')])
conn.execute("SET s3_access_key_id=?", [os.getenv('AWS_ACCESS_KEY_ID', '')])
conn.execute("SET s3_secret_access_key=?", [os.getenv('AWS_SECRET_ACCESS_KEY', '')])
# Or use IAM role (recommended for production)
conn.execute("SET s3_use_ssl=true; SET s3_url_style='path';")
```

---

## 10. Summary: Recommended Architecture Decisions

| Decision | Recommendation | Rationale |
|---|---|---|
| User/worker config storage | PostgreSQL (REQ-07) | Relational, queryable, ACID |
| Conversation history | PostgreSQL via LangGraph checkpointer (REQ-07) | Persistent, structured |
| Audit logs | PostgreSQL (REQ-07) | Queryable, indexable |
| Trade/exposure/VaR/IRIS data | **Apache Iceberg on S3** | Time travel, schema evolution, fast queries |
| Documents (PDF, DOCX, CSV uploads) | **S3 directly** | Object storage is the right fit |
| Workflow files (.md) | **S3 directly** | Small text files; no columnar query needed |
| Analytics engine | **DuckDB** (unchanged) | Reads both S3/Parquet and Iceberg natively |
| Iceberg catalog | **AWS Glue** (AWS) or **Nessie** (multi-cloud) | Low overhead, DuckDB-compatible |
| File tree metadata | **PostgreSQL `file_metadata` table** | Eliminates filesystem walk |
| File serving | **Pre-signed S3 URLs** for binary, **proxy** for text | Balance latency and security |

---

## 11. Acceptance Criteria

- [ ] S3 bucket created and configured with versioning and SSE encryption
- [ ] Domain data files (trades.json, exposure.json, var.json) migrated to S3
- [ ] IRIS CCR data migrated to Iceberg table, DuckDB queries return same results
- [ ] Iceberg time-travel query returns correct historical data: `SELECT * FROM trades AS OF '2026-01-01'`
- [ ] File upload endpoint writes to S3 (not local filesystem)
- [ ] File tree API reads from PostgreSQL `file_metadata` table (not filesystem walk)
- [ ] Pre-signed URL file serving working for PDF and XLSX files
- [ ] DuckDB IRIS query with date filter is ≥2× faster than current CSV scan
- [ ] Local filesystem data directories are empty (all data migrated)
- [ ] No regression: all existing DuckDB tool queries return correct results

---

## 12. Out of Scope

- Real-time streaming ingestion (Kinesis, Kafka) — Phase 2
- Apache Spark or Ray for distributed compute — not needed at current scale
- Data catalog UI for end users — managed via admin console
- Multi-region replication — Phase 2 for disaster recovery
- Data lineage tracking — Phase 2
