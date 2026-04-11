# REQ-08b — Apache Iceberg Analytical Tables
**Status:** Pending Implementation
**Version:** 1.1 (Updated 2026-04-11 — scoped to structured data migration only; local dev stack moved to REQ-08a)
**Prerequisite:** REQ-08a complete — S3 bucket exists, `S3StorageBackend` implemented, local MinIO dev stack running
**Scope:** Migrate structured analytical datasets (trades, exposure, VaR, IRIS CCR) from local JSON/CSV files to Apache Iceberg tables on S3. Update all DuckDB tools to query Iceberg. REQ-08a already handles documents, uploads, and unstructured files.

---

## 1. What Iceberg Adds Over Plain S3

REQ-08a moves all files to S3. For documents and uploads, plain S3 objects are sufficient. Iceberg is the right layer for structured, growing, query-heavy datasets:

| Feature | Value for B-Pulse |
|---|---|
| **ACID transactions** | Safe concurrent writes — two workers can append exposure rows simultaneously |
| **Time travel** | `SELECT * FROM trades AS OF '2026-01-01'` — query any historical snapshot |
| **Schema evolution** | Add a column without rewriting existing Parquet files |
| **Partition evolution** | Change partitioning without a full rewrite |
| **File-level statistics** | DuckDB skips files that can't match WHERE clause — 10–100× faster on large datasets |
| **Snapshot isolation** | Consistent read view while writes are in progress |

### Iceberg vs plain S3 Parquet — decision table

| Scenario | Plain Parquet on S3 | Iceberg |
|---|---|---|
| Binary files (PDF, DOCX) | ✅ — just use S3 objects | Overkill |
| Reference data < 100MB, updated once/day, read-only | ✅ Simpler | Overkill |
| Data growing > 500MB, updated frequently | ⚠️ Performance degrades | ✅ Designed for this |
| Concurrent writes from multiple workers | ❌ No atomic guarantees | ✅ ACID |
| Historical queries required | ❌ Must keep old files manually | ✅ Built-in time travel |
| Schema expected to evolve | ❌ Painful | ✅ Schema evolution |

### Datasets that get Iceberg tables

| Dataset | Current Location | Why Iceberg |
|---|---|---|
| Trade inventory | `counterparties/trades.json` | Grows daily, concurrent appends, needs time travel |
| Exposure snapshots | `counterparties/exposure.json` | Daily snapshots, historical queries |
| VaR time series | `counterparties/var.json` | Time series, 90-day trend queries |
| IRIS CCR reference | `iris/iris_combined.csv` | 100MB+, heavy date/counterparty filters |

---

## 2. Iceberg Catalog

The catalog tracks where each Iceberg table's metadata lives in S3.

| Catalog | Best For | Notes |
|---|---|---|
| **Project Nessie** | Local dev testing (add to `docker-compose.local.yml` from REQ-08a) | Git-like branch/merge for data |
| **AWS Glue Data Catalog** | AWS production | Native AWS, $1/month, DuckDB-compatible |
| **Apache Polaris** | Open-source multi-cloud | Medium setup complexity |

**Recommendation:** Add Nessie to the existing `docker-compose.local.yml` (REQ-08a already has MinIO). AWS Glue for production — zero servers to manage.

**Add to `docker-compose.local.yml`:**
```yaml
  nessie:
    image: projectnessie/nessie:latest
    ports:
      - "19120:19120"   # Nessie REST catalog API
    environment:
      QUARKUS_PROFILE: prod
      NESSIE_VERSION_STORE_TYPE: IN_MEMORY
```

---

## 3. DuckDB + Iceberg Integration

DuckDB reads Iceberg tables natively via the `duckdb-iceberg` extension. The same MinIO endpoint from REQ-08a is reused:

```python
import duckdb, os

def _configure_iceberg(conn):
    conn.install_extension('iceberg')
    conn.load_extension('iceberg')
    endpoint = os.getenv('S3_ENDPOINT_URL', '')    # blank = real AWS
    if endpoint:
        # Local MinIO (already started by REQ-08a docker-compose)
        conn.execute(f"SET s3_endpoint='{endpoint.replace('http://','').replace('https://','')}'")
        conn.execute("SET s3_use_ssl=false")
        conn.execute("SET s3_url_style='path'")
    conn.execute(f"SET s3_region='{os.getenv('AWS_REGION','us-east-1')}'")
    conn.execute(f"SET s3_access_key_id='{os.getenv('AWS_ACCESS_KEY_ID','')}'")
    conn.execute(f"SET s3_secret_access_key='{os.getenv('AWS_SECRET_ACCESS_KEY','')}'")
```

**When switching from MinIO to AWS:** change 4 env vars (`S3_ENDPOINT_URL` removed, credentials updated). No code changes in tools.

---

## 4. Iceberg Table Definitions

### 4.1 Trade Inventory

```sql
CREATE TABLE bpulse_catalog.market_risk.trades (
    trade_id        VARCHAR NOT NULL,
    counterparty_id VARCHAR NOT NULL,
    instrument_type VARCHAR,
    notional        DOUBLE,
    mtm             DOUBLE,
    pfe             DOUBLE,
    trade_date      DATE,
    maturity_date   DATE,
    currency        VARCHAR,
    worker_id       VARCHAR NOT NULL,
    loaded_at       TIMESTAMP NOT NULL
)
USING iceberg
PARTITIONED BY (worker_id, months(trade_date))
TBLPROPERTIES ('write.format.default'='parquet', 'write.parquet.compression-codec'='zstd');
```

### 4.2 Exposure Snapshots

```sql
CREATE TABLE bpulse_catalog.market_risk.exposure (
    counterparty_id VARCHAR NOT NULL,
    snapshot_date   DATE    NOT NULL,
    notional        DOUBLE,
    mtm             DOUBLE,
    pfe             DOUBLE,
    net_exposure    DOUBLE,
    worker_id       VARCHAR NOT NULL,
    loaded_at       TIMESTAMP NOT NULL
)
USING iceberg
PARTITIONED BY (worker_id, months(snapshot_date));
```

### 4.3 VaR Time Series

```sql
CREATE TABLE bpulse_catalog.market_risk.var_series (
    counterparty_id  VARCHAR NOT NULL,
    var_date         DATE    NOT NULL,
    confidence_level VARCHAR NOT NULL,
    var_amount       DOUBLE,
    marginal_var     DOUBLE,
    component_var    DOUBLE,
    stress_loss      DOUBLE,
    worker_id        VARCHAR NOT NULL,
    loaded_at        TIMESTAMP NOT NULL
)
USING iceberg
PARTITIONED BY (worker_id, months(var_date));
```

### 4.4 IRIS CCR Reference Data

```sql
CREATE TABLE bpulse_catalog.reference.iris_ccr (
    -- columns match current iris_combined.csv schema (confirm from CSV headers before creating)
    reporting_date  DATE    NOT NULL,
    counterparty_id VARCHAR NOT NULL,
    worker_id       VARCHAR NOT NULL,
    loaded_at       TIMESTAMP NOT NULL
    -- ... full column list from iris_combined.csv
)
USING iceberg
PARTITIONED BY (worker_id, months(reporting_date));
```

---

## 5. DuckDB Tool Changes Required

### 5.1 Tools to Update

| Tool | Current Data Source | Updated |
|---|---|---|
| `iris_ccr_tools` | `pd.read_csv('iris_combined.csv')` | `iceberg_scan()` on `reference.iris_ccr` |
| `duckdb_query` | Local `duckdb_analytics.db` | S3 Parquet + Iceberg tables |
| `get_counterparty_exposure` | `exposure.json` | Iceberg `market_risk.exposure` |
| `get_trade_inventory` | `trades.json` | Iceberg `market_risk.trades` |
| `get_var_contribution` | `var.json` | Iceberg `market_risk.var_series` |
| `get_historical_exposure` | Snapshot JSON files | Time-travel query on `market_risk.exposure` |

### 5.2 Time Travel — get_historical_exposure Simplified

```python
# Before: reads separate historical snapshot files
# After: single time-travel query
conn.execute("""
    SELECT * FROM iceberg_scan(?)
    FOR SYSTEM_TIME AS OF ?
    WHERE counterparty_id = ? AND worker_id = ?
""", [exposure_table_path, date, counterparty, worker_id])
```

The `get_historical_exposure` static tool (currently hardcoded in `agent/tools.py`) becomes a thin wrapper around this query — no separate snapshot file management needed.

---

## 6. Data Loading Pipeline

Nightly loader replaces manual CSV/JSON updates:

```
Source (IRIS feed / trade system / risk engine)
        │
        ▼
Python loader (scheduled — cron or Lambda)
    1. Read source data
    2. Validate schema
    3. Append to Iceberg table (atomic, idempotent via snapshot ID check)
        │
        ▼
Iceberg table on S3
        │
        ▼
DuckDB tools (unchanged query interface to agent)
```

Weekly maintenance — merge small files:
```python
conn.execute("CALL iceberg_compact('s3://bpulse-data-prod/catalog/market_risk/trades/')")
```

---

## 7. Migration Phases

### Phase 1 — Local Validation (Use MinIO from REQ-08a)
1. Add Nessie service to existing `docker-compose.local.yml`
2. Create Iceberg tables on local MinIO via Nessie catalog
3. Load `iris_combined.csv` into local Iceberg table
4. Run existing IRIS tool queries against Iceberg — verify identical results
5. Benchmark: confirm filter-pushdown on date column is faster than full CSV scan
6. Test time-travel query on exposure table

### Phase 2 — AWS Glue Catalog Setup
1. Create AWS Glue Data Catalog database `bpulse_catalog`
2. Create Iceberg tables in Glue (same DDL as Phase 1, bucket = `bpulse-data-prod` from REQ-08a)
3. Run data loading pipeline for all four datasets (trades, exposure, VaR, IRIS)
4. Validate query results match local baseline exactly

### Phase 3 — Tool Cutover
1. Update `iris_ccr_tools.py` to use `iceberg_scan()` instead of `pd.read_csv()`
2. Update DuckDB base tool to call `_configure_iceberg()` on connection init
3. Update `get_counterparty_exposure`, `get_trade_inventory`, `get_var_contribution`, `get_historical_exposure` to query Iceberg
4. Run dual-read validation: local JSON/CSV and Iceberg return identical results for same query
5. Disable local file fallback

### Phase 4 — Validation & Cleanup
1. Time-travel query returns correct historical data for sample date
2. Concurrent write test: two workers append simultaneously, no corruption or data loss
3. Schema evolution: add a column to `trades` — existing queries unaffected
4. Performance: IRIS query with date + counterparty filter is ≥2× faster than CSV baseline
5. Archive local JSON/CSV source files to S3 Glacier

---

## 8. Additional Environment Variables

| Variable | Value | Notes |
|---|---|---|
| `ICEBERG_CATALOG` | `glue` or `nessie` | Catalog type |
| `ICEBERG_CATALOG_DB` | `bpulse_catalog` | Glue DB name or Nessie namespace |
| `ICEBERG_CATALOG_URI` | `http://localhost:19120/api/v1` | Nessie URL for local dev only |
| `S3_ENDPOINT_URL` | *(blank for AWS)* | Already set from REQ-08a for local dev |

---

## 9. Cost (AWS Incremental — on top of REQ-08a S3)

| Service | Est. Monthly | Notes |
|---|---|---|
| Iceberg Parquet files on S3 | ~$2 | Parquet is compact; same bucket as REQ-08a |
| Extra S3 requests (partition pruning reduces reads) | ~$1–2 | |
| AWS Glue Data Catalog | ~$1 | Per million objects |
| **Incremental total** | **~$4–5/month** | Very affordable |

---

## 10. Acceptance Criteria

- [ ] Nessie added to `docker-compose.local.yml` (alongside MinIO from REQ-08a)
- [ ] IRIS CCR data loaded into local Iceberg table; existing IRIS tool queries return identical results
- [ ] DuckDB IRIS query with date filter is ≥2× faster than current CSV scan
- [ ] `get_historical_exposure` uses Iceberg time-travel — no separate snapshot files needed
- [ ] Concurrent append test: two parallel writes complete without data corruption
- [ ] Schema evolution: add column to `trades` — existing queries unaffected
- [ ] All 4 datasets migrated to Iceberg on AWS S3 with Glue catalog
- [ ] Switching from local MinIO/Nessie to AWS requires only env var changes — no code changes
- [ ] Weekly compaction job documented and scheduled
- [ ] No regression: all DuckDB and IRIS tool queries return correct results

---

## 11. Out of Scope

- Local dev stack (MinIO docker-compose) → REQ-08a
- S3 bucket creation and file migration → REQ-08a
- Documents, uploads, workflows, charts → REQ-08a
- Real-time streaming ingestion (Kinesis, Kafka)
- Apache Spark for distributed compute
- Multi-region S3 replication
- Data lineage tracking
