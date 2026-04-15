"""
test_e2e_data_layers.py — End-to-end data layer access tests via live SAJHA MCP server.

Prerequisites:
  - Agent server running on http://localhost:8000
  - SAJHA MCP server running on http://localhost:3002
  - Test CSV files planted in all 3 layers (created by setup below)
  - Worker w-e74b5836 has common_data_path set to './data/common'

Tests call SAJHA tool endpoints directly with the correct worker/user headers,
exactly as the agent server does, and verify each tool sees files from all 3 layers.
"""
import json
import requests
import unittest
import os

AGENT_BASE  = "http://localhost:8000"
SAJHA_BASE  = "http://localhost:3002"
SAJHA_KEY   = "sja_full_access_admin"
WORKER_ID   = "w-e74b5836"
USER_ID     = "risk_agent"

# Paths set in the worker record
DOMAIN_DATA = "./data/workers/w-e74b5836/domain_data"
MY_DATA     = f"./data/workers/w-e74b5836/my_data/{USER_ID}"
COMMON_DATA = "./data/common"

# ── helpers ──────────────────────────────────────────────────────────────────

def login() -> str:
    r = requests.post(f"{AGENT_BASE}/api/auth/login",
                      json={"user_id": USER_ID, "password": "RiskAgent2025!"})
    r.raise_for_status()
    return r.json()["token"]


def sajha_headers():
    """Headers that SAJHA expects — mirrors what agent_server injects."""
    return {
        "Authorization":          SAJHA_KEY,   # sja_ key directly, no Bearer prefix
        "X-Worker-Id":            WORKER_ID,
        "X-Worker-Data-Root":     DOMAIN_DATA,
        "X-Worker-My-Data-Root":  MY_DATA,
        "X-Worker-Common-Root":   COMMON_DATA,
        "X-User-Id":              USER_ID,
        "Content-Type":           "application/json",
    }


def call_tool(tool_name: str, args: dict) -> dict:
    """Call a SAJHA tool via the /api/tools/execute endpoint."""
    r = requests.post(
        f"{SAJHA_BASE}/api/tools/execute",
        headers=sajha_headers(),
        json={"tool": tool_name, "arguments": args},
        timeout=30
    )
    r.raise_for_status()
    return r.json()


# ── test cases ────────────────────────────────────────────────────────────────

class TestE2EListUploadedFiles(unittest.TestCase):
    """list_uploaded_files must return files from all 3 layers."""

    def test_lists_all_three_layers(self):
        result = call_tool("list_uploaded_files", {"section": "all"})
        output = result.get("output", "") or json.dumps(result)
        self.assertIn("e2e_domain.csv",  output, f"domain_data file missing.\n{output[:500]}")
        self.assertIn("e2e_mydata.csv",  output, f"my_data file missing.\n{output[:500]}")
        self.assertIn("e2e_common.csv",  output, f"common file missing.\n{output[:500]}")

    def test_lists_only_my_data(self):
        result = call_tool("list_uploaded_files", {"section": "my_data"})
        output = result.get("output", "") or json.dumps(result)
        self.assertIn("e2e_mydata.csv", output)
        self.assertNotIn("e2e_domain.csv", output)
        self.assertNotIn("e2e_common.csv",  output)

    def test_lists_only_domain_data(self):
        result = call_tool("list_uploaded_files", {"section": "domain_data"})
        output = result.get("output", "") or json.dumps(result)
        self.assertIn("e2e_domain.csv", output)
        self.assertNotIn("e2e_mydata.csv", output)

    def test_lists_only_common(self):
        result = call_tool("list_uploaded_files", {"section": "common"})
        output = result.get("output", "") or json.dumps(result)
        self.assertIn("e2e_common.csv", output)
        self.assertNotIn("e2e_domain.csv", output)


class TestE2EDuckDBListTables(unittest.TestCase):
    """duckdb_list_tables must register and show tables from all 3 layers."""

    def test_tables_from_all_layers(self):
        result = call_tool("duckdb_list_tables", {})
        output = json.dumps(result).lower()
        self.assertIn("e2e_domain",  output, f"domain table missing.\n{json.dumps(result)[:600]}")
        self.assertIn("e2e_mydata",  output, f"my_data table missing.\n{json.dumps(result)[:600]}")
        self.assertIn("e2e_common",  output, f"common table missing.\n{json.dumps(result)[:600]}")


class TestE2EDuckDBQuery(unittest.TestCase):
    """duckdb_query must be able to SELECT from tables in each layer."""

    def _query(self, view_name: str) -> dict:
        return call_tool("duckdb_query", {"sql_query": f"SELECT * FROM {view_name} LIMIT 5"})

    def test_query_domain_table(self):
        result = self._query("e2e_domain")
        self.assertNotIn("error", json.dumps(result).lower()[:100],
                         f"Query failed: {result}")
        output = json.dumps(result)
        self.assertIn("domain_data", output)

    def test_query_mydata_table(self):
        result = self._query("e2e_mydata")
        self.assertNotIn("error", json.dumps(result).lower()[:100],
                         f"Query failed: {result}")
        output = json.dumps(result)
        self.assertIn("my_data", output)

    def test_query_common_table(self):
        result = self._query("e2e_common")
        self.assertNotIn("error", json.dumps(result).lower()[:100],
                         f"Query failed: {result}")
        output = json.dumps(result)
        self.assertIn("common", output)


class TestE2ESqlSelectListSources(unittest.TestCase):
    """sqlselect_list_sources must auto-discover tables from all 3 layers."""

    def test_sources_all_layers(self):
        result = call_tool("sqlselect_list_sources", {})
        output = json.dumps(result).lower()
        self.assertIn("e2e_domain",  output, f"domain source missing.\n{json.dumps(result)[:600]}")
        self.assertIn("e2e_mydata",  output, f"my_data source missing.\n{json.dumps(result)[:600]}")
        self.assertIn("e2e_common",  output, f"common source missing.\n{json.dumps(result)[:600]}")


class TestE2ESqlSelectQuery(unittest.TestCase):
    """sqlselect_execute_query must query tables from each layer."""

    def _query(self, table: str) -> dict:
        return call_tool("sqlselect_execute_query", {"query": f"SELECT * FROM {table} LIMIT 5"})

    def test_query_domain(self):
        result = self._query("e2e_domain")
        output = json.dumps(result)
        self.assertIn("domain_data", output, f"domain query failed: {output[:400]}")

    def test_query_mydata(self):
        result = self._query("e2e_mydata")
        output = json.dumps(result)
        self.assertIn("my_data", output, f"my_data query failed: {output[:400]}")

    def test_query_common(self):
        result = self._query("e2e_common")
        output = json.dumps(result)
        self.assertIn("common", output, f"common query failed: {output[:400]}")


class TestE2EParquetRead(unittest.TestCase):
    """parquet_read must accept file paths from all 3 layers."""

    BASE = "/Users/saadahmed/Desktop/react_agent/sajhamcpserver"

    def _read(self, rel_path: str) -> dict:
        abs_path = os.path.join(self.BASE, rel_path)
        return call_tool("parquet_read", {"file_path": abs_path, "sample_rows": 3})

    def test_read_domain_csv(self):
        result = self._read("data/workers/w-e74b5836/domain_data/e2e_domain.csv")
        inner = result.get("result", result)
        self.assertNotIn("error", json.dumps(result).lower()[:100], f"parquet_read domain failed: {result}")
        self.assertIn("row_count", inner, f"row_count missing: {result}")

    def test_read_mydata_csv(self):
        result = self._read(f"data/workers/w-e74b5836/my_data/{USER_ID}/e2e_mydata.csv")
        inner = result.get("result", result)
        self.assertNotIn("error", json.dumps(result).lower()[:100], f"parquet_read my_data failed: {result}")
        self.assertIn("row_count", inner, f"row_count missing: {result}")

    def test_read_common_csv(self):
        result = self._read("data/common/e2e_common.csv")
        inner = result.get("result", result)
        self.assertNotIn("error", json.dumps(result).lower()[:100], f"parquet_read common failed: {result}")
        self.assertIn("row_count", inner, f"row_count missing: {result}")


class TestE2ESearchFiles(unittest.TestCase):
    """search_files must find content in files across all 3 layers."""

    def test_search_finds_domain_content(self):
        result = call_tool("search_files", {"query": "Domain Record"})
        output = json.dumps(result)
        self.assertIn("e2e_domain", output, f"search_files didn't find domain file: {output[:500]}")

    def test_search_finds_mydata_content(self):
        result = call_tool("search_files", {"query": "My Data Record"})
        output = json.dumps(result)
        self.assertIn("e2e_mydata", output, f"search_files didn't find my_data file: {output[:500]}")

    def test_search_finds_common_content(self):
        result = call_tool("search_files", {"query": "Common Record"})
        output = json.dumps(result)
        self.assertIn("e2e_common", output, f"search_files didn't find common file: {output[:500]}")


if __name__ == "__main__":
    # Quick connectivity check
    try:
        requests.get(f"{AGENT_BASE}/health", timeout=3).raise_for_status()
        requests.get(f"{SAJHA_BASE}/health", timeout=3).raise_for_status()
    except Exception as e:
        print(f"ERROR: Server not reachable — {e}")
        exit(1)

    unittest.main(verbosity=2)
