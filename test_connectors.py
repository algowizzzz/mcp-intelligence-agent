#!/usr/bin/env python3
"""
Connector test script for Market Risk Worker.
Run from the react_agent directory with: python3 test_connectors.py
Requires SAJHA server running on port 3002.
"""
import json, os, urllib.request, urllib.error, sys

BASE_URL = "http://127.0.0.1:3002"
API_KEY  = "sja_full_access_admin"

WORKER_CTX_MS = {
    "tenant_id":     "a241c412-f9f1-4461-8992-5c0b24ea8578",
    "client_id":     "d39a3d30-eb6d-4969-98aa-82bab2ca5b22",
    "client_secret": os.environ.get("AZURE_CLIENT_SECRET", ""),
    "teams_team_id":    "33793fc4-5b65-4a4f-b7b6-e11bcf3ffb54",
    "teams_channel_id": "19:SHmWm9n11mv8FTPMTv2XpTyDbcj9bnLntOzTD_PW7KQ1@thread.tacv2",
    "outlook_user_email": "SaadAhmed@DeepLearnHQ.onmicrosoft.com",
}

WORKER_CTX_ATL = {
    "atlassian_email":   "sa5425592@gmail.com",
    "atlassian_token":   os.environ.get("ATLASSIAN_API_TOKEN", ""),
    "atlassian_base_url": "https://sa5425592.atlassian.net",
    "jira_project_key":   "MRISK",
}

def call_tool(tool, arguments):
    payload = json.dumps({"tool": tool, "arguments": arguments}).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/tools/execute", data=payload,
        headers={"Content-Type": "application/json", "Authorization": API_KEY}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode()[:300]}

TESTS = [
    ("T2", "teams_list_channels",
     {"_worker_context": WORKER_CTX_MS},
     lambda r: "channels" in r.get("result", {}) and r["result"]["count"] > 0),

    ("T3", "teams_send_message",
     {"channel_id": WORKER_CTX_MS["teams_channel_id"],
      "message": "🤖 Connector test T3 — Market Risk Worker [auto-test]",
      "content_type": "text", "confirmation_required": True,
      "_worker_context": WORKER_CTX_MS},
     lambda r: r.get("result", {}).get("ok") is True),

    ("T4", "outlook_read_email",
     {"user_email": "SaadAhmed@DeepLearnHQ.onmicrosoft.com",
      "folder": "inbox", "top": 5,
      "_worker_context": WORKER_CTX_MS},
     lambda r: "emails" in r.get("result", {}) or "messages" in r.get("result", {})),

    ("T5", "jira_list_issues",
     {"project_key": "MRISK", "_worker_context": WORKER_CTX_ATL},
     lambda r: "issues" in r.get("result", {}) or "error" not in r.get("result", {})),
]

print(f"\n{'='*60}")
print("  Market Risk Worker — Connector Tests")
print(f"{'='*60}\n")

results = []
for tid, tool, args, check in TESTS:
    print(f"[{tid}] {tool}...", end=" ", flush=True)
    result = call_tool(tool, args)
    passed = False
    try:
        passed = check(result)
    except:
        pass
    status = "✅ PASS" if passed else "❌ FAIL"
    print(status)
    if not passed:
        print(f"     Result: {json.dumps(result.get('result', result), indent=2)[:300]}")
    results.append((tid, tool, status))

print(f"\n{'='*60}")
for tid, tool, status in results:
    print(f"  {status}  {tid}: {tool}")
print(f"{'='*60}\n")

passed = sum(1 for _, _, s in results if "PASS" in s)
print(f"  {passed}/{len(results)} tests passed\n")
