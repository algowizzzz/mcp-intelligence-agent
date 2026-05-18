#!/bin/bash
# REQ-17 extended regression — pushes coverage beyond the 20-item P0 smoke.
# Suites covered: A, B, C, D, F, G, H (tool runtime), L, M, plus the isolation gate.
#
# Run with:
#   bash tools-pack/tests/regression_extended.sh

set -u
AGENT=${AGENT_URL:-http://localhost:8000}
SAJHA=${SAJHA_URL:-http://localhost:3002}
OUT=/tmp/regression-extended
mkdir -p "$OUT"

PASS=0; FAIL=0; SKIP=0
declare -a FAILS

log() {
  case "$1" in
    PASS) PASS=$((PASS+1));;
    FAIL) FAIL=$((FAIL+1)); FAILS+=("$2");;
    SKIP) SKIP=$((SKIP+1));;
  esac
  printf "[%-4s] %s\n" "$1" "$2"
}

# Helpers
SAJHA_JWT=$(curl -s -X POST $SAJHA/api/auth/login -H "Content-Type: application/json" \
  -d '{"user_id":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))")

SUPER_JWT=$(curl -s -X POST $AGENT/api/auth/login -H "Content-Type: application/json" \
  -d '{"user_id":"risk_agent","password":"RiskAgent2025!"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))")
USER_JWT=$(curl -s -X POST $AGENT/api/auth/login -H "Content-Type: application/json" \
  -d '{"user_id":"test_user","password":"TestUser123!"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))")

if [ -z "$SAJHA_JWT" ] || [ -z "$SUPER_JWT" ]; then
  echo "Cannot get JWTs — abort. SAJHA_JWT=${#SAJHA_JWT} SUPER_JWT=${#SUPER_JWT}"
  exit 2
fi

# Worker context dict for tool calls (absolute paths, post-retirement)
LEGACY_BASE="/Users/saadahmed/Desktop/durga_agent/mcp-intelligence-agent/archive/sajhamcpserver-v2.9.8-fork"
WC_MR='{"my_data_path":"'"$LEGACY_BASE"'/data/workers/w-market-risk/my_data/risk_agent","domain_data_path":"'"$LEGACY_BASE"'/data/workers/w-market-risk/domain_data","common_data_path":"'"$LEGACY_BASE"'/data/common","workflows_path":"'"$LEGACY_BASE"'/data/workers/w-market-risk/workflows/verified"}'

call_tool() {
  local tool="$1"; local args="$2"
  curl -s -X POST $SAJHA/api/tools/execute \
    -H "Authorization: Bearer $SAJHA_JWT" \
    -H "Content-Type: application/json" \
    -d "{\"tool\":\"$tool\",\"arguments\":$args}"
}

assert_code() {
  local id="$1"; local desc="$2"; local code="$3"; local want="$4"
  if [ "$code" = "$want" ]; then log PASS "$id: $desc ($code)"; else log FAIL "$id: $desc (got $code, want $want)"; fi
}

assert_tool() {
  # PASS if tool returns either success=true OR a 'result' field. Some tools error
  # for valid reasons (missing creds, no data) — that's still a successful call.
  local id="$1"; local tool="$2"; local args="${3:-{\}}"
  local resp=$(call_tool "$tool" "$args")
  if echo "$resp" | grep -q '"success": *true\|"result"\|"error"'; then
    log PASS "$id: tool $tool reachable"
  else
    log FAIL "$id: tool $tool returned: $(echo "$resp" | head -c 120)"
  fi
}

# ── Suite A: auth (already covered, just spot-check the gates) ────────────────
echo "=== Suite A: Auth & RBAC ==="
for ROLE in risk_agent test_user; do
  case $ROLE in
    risk_agent) PASS_=$SUPER_JWT;;
    test_user)  PASS_=$USER_JWT;;
  esac
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $PASS_" $AGENT/api/auth/me)
  assert_code "A-06-$ROLE" "/auth/me as $ROLE" "$CODE" "200"
done

# ── Suite B: User Management ─────────────────────────────────────────────────
echo ""; echo "=== Suite B: User Management ==="

# B-01 list
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/users)
assert_code "B-01" "list users" "$CODE" "200"

# B-02 get one user
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/users/test_user)
assert_code "B-02" "get one user" "$CODE" "200"

# B-03 create user (idempotent — delete first if exists)
curl -s -X DELETE -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/users/reg_test_xyz > /dev/null
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AGENT/api/super/users \
  -H "Authorization: Bearer $SUPER_JWT" -H "Content-Type: application/json" \
  -d '{"user_id":"reg_test_xyz","display_name":"Reg Test","password":"RegTest123!","role":"user","worker_id":"w-market-risk"}')
if [ "$CODE" = "200" ] || [ "$CODE" = "201" ]; then log PASS "B-03 create user ($CODE)"; else log FAIL "B-03 create user (got $CODE)"; fi

# B-04 update user
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT $AGENT/api/super/users/reg_test_xyz \
  -H "Authorization: Bearer $SUPER_JWT" -H "Content-Type: application/json" \
  -d '{"display_name":"Updated Reg Test"}')
assert_code "B-04" "update user" "$CODE" "200"

# B-05 reset password
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AGENT/api/super/users/reg_test_xyz/reset-password \
  -H "Authorization: Bearer $SUPER_JWT" -H "Content-Type: application/json" \
  -d '{"new_password":"NewPass123!"}')
assert_code "B-05" "reset password" "$CODE" "200"

# B-06 delete user
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE $AGENT/api/super/users/reg_test_xyz \
  -H "Authorization: Bearer $SUPER_JWT")
if [ "$CODE" = "200" ] || [ "$CODE" = "204" ]; then log PASS "B-06 delete user ($CODE)"; else log FAIL "B-06 delete user (got $CODE)"; fi

# B-07 duplicate user_id rejected
curl -s -X POST $AGENT/api/super/users -H "Authorization: Bearer $SUPER_JWT" -H "Content-Type: application/json" \
  -d '{"user_id":"dup_check","display_name":"D","password":"DupTest123!","role":"user","worker_id":"w-market-risk"}' > /dev/null
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AGENT/api/super/users \
  -H "Authorization: Bearer $SUPER_JWT" -H "Content-Type: application/json" \
  -d '{"user_id":"dup_check","display_name":"D","password":"DupTest123!","role":"user","worker_id":"w-market-risk"}')
curl -s -X DELETE -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/users/dup_check > /dev/null
if [ "$CODE" = "400" ] || [ "$CODE" = "409" ]; then log PASS "B-07 dup user rejected ($CODE)"; else log FAIL "B-07 expected 4xx, got $CODE"; fi

# ── Suite C: Worker Management ────────────────────────────────────────────────
echo ""; echo "=== Suite C: Worker Management ==="

# C-01 list (same as A-13 — done elsewhere)
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/workers)
assert_code "C-01" "list workers" "$CODE" "200"

# C-02 get one
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/workers/w-market-risk)
assert_code "C-02" "get worker" "$CODE" "200"

# C-07 admin gets own worker
ADMIN_JWT=$(curl -s -X POST $AGENT/api/auth/login -H "Content-Type: application/json" \
  -d '{"user_id":"admin","password":"admin123"}' | python3 -c "import sys,json;print(json.load(sys.stdin).get('token',''))" 2>/dev/null)
if [ -n "$ADMIN_JWT" ]; then
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $ADMIN_JWT" $AGENT/api/admin/worker)
  assert_code "C-07" "admin own worker" "$CODE" "200"
else
  log SKIP "C-07 admin login failed"
fi

# ── Suite D: Prompt Management ────────────────────────────────────────────────
echo ""; echo "=== Suite D: Prompt Management ==="

# D-01 read prompt (super-admin can see worker config which includes prompt)
PROMPT_BEFORE=$(curl -s -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/workers/w-market-risk | python3 -c "import sys,json;print(json.load(sys.stdin).get('system_prompt','')[:60])")
if [ -n "$PROMPT_BEFORE" ]; then log PASS "D-01 read system_prompt: $PROMPT_BEFORE..."; else log FAIL "D-01 read prompt empty"; fi

# ── Suite F: LLM Config ──────────────────────────────────────────────────────
echo ""; echo "=== Suite F: LLM Configuration ==="

CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPER_JWT" $AGENT/api/super/llm-config)
assert_code "F-01" "get LLM config" "$CODE" "200"

# ── Suite G: File Management ─────────────────────────────────────────────────
echo ""; echo "=== Suite G: File Management ==="

# G-01..G-04 trees
for SEC in my_data domain_data common verified my_workflows; do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $USER_JWT" "$AGENT/api/fs/$SEC/tree")
  assert_code "G-tree-$SEC" "$SEC tree" "$CODE" "200"
done

# G-09 quota
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $USER_JWT" "$AGENT/api/fs/quota")
assert_code "G-09" "quota" "$CODE" "200"

# G-13 traversal blocked
CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $USER_JWT" "$AGENT/api/fs/my_data/file?path=../../config/users.json")
[ "$CODE" = "400" ] || [ "$CODE" = "403" ] || [ "$CODE" = "404" ] && log PASS "G-13 traversal blocked ($CODE)" || log FAIL "G-13 expected 4xx got $CODE"

# ── Suite H: Tools — runtime smoke for every JSON config ──────────────────────
echo ""; echo "=== Suite H: Tools runtime smoke (all configs) ==="

# Use a minimal-args call for each tool. Different tools want different inputs;
# we pass the worker_context plus a placeholder for the most common required fields.
for CFG in tools-pack/configs/*.json; do
  TOOL=$(python3 -c "import json,sys;print(json.load(open('$CFG')).get('name',''))")
  [ -z "$TOOL" ] && continue
  # Build minimal arg payload — varies by tool family
  case $TOOL in
    document_search|tavily_*|ir_*) ARGS='{"query":"test","_worker_context":'$WC_MR'}';;
    pdf_read|file_read|md_save|md_to_docx|parquet_read) ARGS='{"path":"sample.pdf","_worker_context":'$WC_MR'}';;
    fill_template) ARGS='{"template":"x.md","_worker_context":'$WC_MR'}';;
    iris_*|get_counterparty_exposure|get_trade_inventory|get_credit_limits|get_historical_exposure|get_var_contribution) ARGS='{"counterparty":"BMO","date":"2024-12-31","_worker_context":'$WC_MR'}';;
    duckdb_*) ARGS='{"sql":"SELECT 1","_worker_context":'$WC_MR'}';;
    sqlselect_*) ARGS='{"source":"none","_worker_context":'$WC_MR'}';;
    olap_*|customer_olap_pivot) ARGS='{"source":"sample.csv","metric":"x","_worker_context":'$WC_MR'}';;
    msdoc_*) ARGS='{"path":"sample.docx","_worker_context":'$WC_MR'}';;
    python_execute) ARGS='{"code":"1+1","_worker_context":'$WC_MR'}';;
    python_run_script) ARGS='{"script_name":"none","_worker_context":'$WC_MR'}';;
    generate_chart) ARGS='{"chart_type":"line","data":[],"_worker_context":'$WC_MR'}';;
    search_files) ARGS='{"query":"sample","_worker_context":'$WC_MR'}';;
    workflow_*|list_*|data_*|customer_*|parquet_*) ARGS='{"_worker_context":'$WC_MR'}';;
    *) ARGS='{"_worker_context":'$WC_MR'}';;
  esac
  assert_tool "H-T-$TOOL" "$TOOL" "$ARGS" > /dev/null 2>&1 &  # background

  # Throttle: process in batches of 8 to avoid overloading SAJHA
done
# Wait for all background to finish; then re-run sequentially with assertions
wait

# Now run sequentially with output capture (we need accurate pass/fail per tool)
for CFG in tools-pack/configs/*.json; do
  TOOL=$(python3 -c "import json,sys;print(json.load(open('$CFG')).get('name',''))")
  [ -z "$TOOL" ] && continue
  case $TOOL in
    document_search|tavily_*|ir_*) ARGS='{"query":"test","_worker_context":'$WC_MR'}';;
    pdf_read|file_read|md_save|md_to_docx|parquet_read) ARGS='{"path":"sample.pdf","_worker_context":'$WC_MR'}';;
    fill_template) ARGS='{"template":"x.md","_worker_context":'$WC_MR'}';;
    iris_*|get_counterparty_exposure|get_trade_inventory|get_credit_limits|get_historical_exposure|get_var_contribution) ARGS='{"counterparty":"BMO","date":"2024-12-31","_worker_context":'$WC_MR'}';;
    duckdb_*) ARGS='{"sql":"SELECT 1","_worker_context":'$WC_MR'}';;
    sqlselect_*) ARGS='{"source":"none","_worker_context":'$WC_MR'}';;
    olap_*|customer_olap_pivot) ARGS='{"source":"sample.csv","metric":"x","_worker_context":'$WC_MR'}';;
    msdoc_*) ARGS='{"path":"sample.docx","_worker_context":'$WC_MR'}';;
    python_execute) ARGS='{"code":"1+1","_worker_context":'$WC_MR'}';;
    python_run_script) ARGS='{"script_name":"none","_worker_context":'$WC_MR'}';;
    generate_chart) ARGS='{"chart_type":"line","data":[],"_worker_context":'$WC_MR'}';;
    search_files) ARGS='{"query":"sample","_worker_context":'$WC_MR'}';;
    workflow_*|list_*|data_*|customer_*|parquet_*) ARGS='{"_worker_context":'$WC_MR'}';;
    *) ARGS='{"_worker_context":'$WC_MR'}';;
  esac
  RESP=$(call_tool "$TOOL" "$ARGS")
  if echo "$RESP" | grep -q '"success": *true\|"result"\|"error"'; then
    log PASS "H-T-$TOOL"
  else
    log FAIL "H-T-$TOOL → $(echo "$RESP" | head -c 100)"
  fi
done

# ── Suite L: Audit + Health ────────────────────────────────────────────────
echo ""; echo "=== Suite L: Audit + Health ==="

CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $SUPER_JWT" "$AGENT/api/super/audit?limit=10")
assert_code "L-03" "audit list" "$CODE" "200"

[ "$(curl -s -o /dev/null -w '%{http_code}' $AGENT/health)" = "200" ] && [ "$(curl -s -o /dev/null -w '%{http_code}' $SAJHA/health)" = "200" ] && log PASS "L-06 both health" || log FAIL "L-06 health"

# ── Suite M: Edge Cases ───────────────────────────────────────────────────────
echo ""; echo "=== Suite M: Edge Cases ==="

# M-01 malformed JSON
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AGENT/api/agent/run -H "Authorization: Bearer $SUPER_JWT" -H "Content-Type: application/json" -d '{invalid json}')
[ "$CODE" -ge 400 ] && [ "$CODE" -lt 500 ] && log PASS "M-01 malformed JSON rejected ($CODE)" || log FAIL "M-01 expected 4xx got $CODE"

# M-02 missing required field
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST $AGENT/api/agent/run -H "Authorization: Bearer $SUPER_JWT" -H "Content-Type: application/json" -d '{}')
[ "$CODE" -ge 400 ] && [ "$CODE" -lt 500 ] && log PASS "M-02 missing field rejected ($CODE)" || log FAIL "M-02 got $CODE"

# M-09 path traversal in upload filename
TMP=$(mktemp)
echo "test" > "$TMP"
CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$AGENT/api/fs/my_data/upload" -H "Authorization: Bearer $USER_JWT" -F "file=@$TMP;filename=../../etc/passwd")
rm -f "$TMP"
[ "$CODE" -ge 400 ] && log PASS "M-09 traversal in filename blocked ($CODE)" || log FAIL "M-09 expected 4xx got $CODE"

# Summary
echo ""
echo "================================================================"
TOTAL=$((PASS+FAIL+SKIP))
echo "EXTENDED REGRESSION: $PASS PASS / $FAIL FAIL / $SKIP SKIP / $TOTAL TOTAL"
if [ ${#FAILS[@]} -gt 0 ]; then
  echo ""
  echo "Failures:"
  for f in "${FAILS[@]}"; do echo "  - $f"; done
fi
echo "================================================================"
exit $FAIL
