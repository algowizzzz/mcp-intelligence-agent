#!/usr/bin/env python3
"""
generate_data.py — One-time seed data generator for sajhamcpserver/data/.

Uses the same hash-based logic as the counterparty tools to produce deterministic
JSON files for 20 common financial institution counterparties.

Usage:
    python scripts/generate_data.py

Output directory: sajhamcpserver/data/counterparties/
"""

import json
import os
import sys
from pathlib import Path

# Resolve project root (one level up from this script)
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
SERVER_DIR = PROJECT_ROOT / "sajhamcpserver"
DATA_DIR = SERVER_DIR / "data"

# Add the server directory to sys.path so we can import tool modules
sys.path.insert(0, str(SERVER_DIR))

from sajha.tools.impl.counterparty_exposure_tool import CounterpartyExposureTool
from sajha.tools.impl.trade_inventory_tool import TradeInventoryTool
from sajha.tools.impl.credit_limits_tool import CreditLimitsTool
from sajha.tools.impl.var_contribution_tool import VarContributionTool
from sajha.tools.impl.historical_exposure_tool import HistoricalExposureTool

# 20 common financial institution counterparties
COUNTERPARTIES = [
    "Goldman Sachs",
    "JPMorgan Chase",
    "Morgan Stanley",
    "Citigroup",
    "Bank of America",
    "Barclays",
    "Deutsche Bank",
    "HSBC",
    "Royal Bank of Canada",
    "BNP Paribas",
    "Credit Suisse",
    "UBS",
    "Societe Generale",
    "Wells Fargo",
    "Nomura",
    "Mizuho Financial",
    "MUFG",
    "Standard Chartered",
    "ING Group",
    "Macquarie Group",
]

HISTORICAL_DATES = [
    "2025-03-31",
    "2025-06-30",
    "2025-09-30",
    "2025-12-31",
]

VALUATION_DATE = "2025-12-31"


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"  Wrote {path.relative_to(PROJECT_ROOT)}")


def generate_exposure(tool: CounterpartyExposureTool) -> None:
    print("\n[1/5] Generating exposure.json ...")
    records = []
    for cp in COUNTERPARTIES:
        result = tool.execute({"counterparty": cp, "date": VALUATION_DATE})
        # Strip _source — it will be set at query time
        result.pop("_source", None)
        records.append(result)
    write_json(DATA_DIR / "counterparties" / "exposure.json", records)


def generate_trades(tool: TradeInventoryTool) -> None:
    print("\n[2/5] Generating trades.json ...")
    all_trades = []
    for cp in COUNTERPARTIES:
        result = tool.execute({"counterparty": cp, "asset_class": "All"})
        for trade in result["trades"]:
            trade["counterparty"] = cp
            trade.pop("_source", None)
            all_trades.append(trade)
    write_json(DATA_DIR / "counterparties" / "trades.json", all_trades)


def generate_credit_limits(tool: CreditLimitsTool) -> None:
    print("\n[3/5] Generating credit_limits.json ...")
    all_limits = []
    for cp in COUNTERPARTIES:
        result = tool.execute({"counterparty": cp})
        for lim in result["limits"]:
            record = {
                "counterparty": cp,
                "limit_type": lim["limit_type"],
                "limit_usd": lim["approved_limit_usd"],
                "utilized_usd": lim["current_utilization_usd"],
                "utilization_pct": lim["utilization_pct"],
                "breach": lim["breach_status"] == "BREACH",
            }
            all_limits.append(record)
    write_json(DATA_DIR / "counterparties" / "credit_limits.json", all_limits)


def generate_var(tool: VarContributionTool) -> None:
    print("\n[4/5] Generating var.json ...")
    records = []
    for cp in COUNTERPARTIES:
        result = tool.execute({"counterparty": cp, "confidence_level": "99%"})
        result.pop("_source", None)
        records.append(result)
    write_json(DATA_DIR / "counterparties" / "var.json", records)


def generate_historical(tool: HistoricalExposureTool) -> None:
    print("\n[5/5] Generating historical quarterly files ...")
    for date_str in HISTORICAL_DATES:
        records = []
        for cp in COUNTERPARTIES:
            result = tool.execute({"counterparty": cp, "date": date_str})
            result.pop("_source", None)
            records.append(result)
        write_json(
            DATA_DIR / "counterparties" / "historical" / f"{date_str}.json",
            records,
        )


def main():
    print(f"Generating seed data into: {DATA_DIR}")

    exposure_tool = CounterpartyExposureTool()
    trade_tool = TradeInventoryTool()
    credit_tool = CreditLimitsTool()
    var_tool = VarContributionTool()
    historical_tool = HistoricalExposureTool()

    generate_exposure(exposure_tool)
    generate_trades(trade_tool)
    generate_credit_limits(credit_tool)
    generate_var(var_tool)
    generate_historical(historical_tool)

    print("\nDone. All seed files written successfully.")


if __name__ == "__main__":
    main()
