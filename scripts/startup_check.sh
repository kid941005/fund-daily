#!/bin/bash
# Fund Daily 启动检查脚本 (Smoke Test)
# 用法: ./scripts/startup_check.sh [HOST] [PORT]
set -uo pipefail

HOST="${1:-${FUND_DAILY_HOST:-localhost}}"
PORT="${2:-${FUND_DAILY_PORT:-5007}}"
BASE_URL="http://${HOST}:${PORT}"
TIMEOUT=10

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASS=0
FAIL=0

check() {
    local name="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo -e "${GREEN}[PASS]${NC} $name"
        PASS=$((PASS + 1))
    else
        echo -e "${RED}[FAIL]${NC} $name (expected: $expected, got: $actual)"
        FAIL=$((FAIL + 1))
    fi
}

check_http() {
    local url="$1"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
    echo "$code"
}

echo "========== Fund Daily 启动检查 =========="
echo "目标: $BASE_URL"
echo ""

# 1. 基础连通性
CODE=$(check_http "${BASE_URL}/api/health")
check "基础连通性 (HTTP 200)" "200" "$CODE"

# 2. JSON 格式响应
BODY=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/api/health" 2>/dev/null || echo '{}')
STATUS=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',''))" 2>/dev/null || echo '')
check "JSON 响应 status=healthy" "healthy" "$STATUS"

# 3. 数据库连接
DB_STATUS=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('database',''))" 2>/dev/null || echo '')
check "数据库连接" "connected" "$DB_STATUS"

# 4. Redis 连接
REDIS_STATUS=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('redis',''))" 2>/dev/null || echo '')
check "Redis 连接" "connected" "$REDIS_STATUS"

# 5. liveness probe
LIVE=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/health/live" 2>/dev/null || echo '{}')
LIVE_STATUS=$(echo "$LIVE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('alive',''))" 2>/dev/null || echo '')
check "Liveness probe" "True" "$LIVE_STATUS"

# 6. readiness probe
READY=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/health/ready" 2>/dev/null || echo '{}')
READY_STATUS=$(echo "$READY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('ready',''))" 2>/dev/null || echo '')
check "Readiness probe" "True" "$READY_STATUS"

# 7. Scheduler 状态
SCHED=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/health/detailed" 2>/dev/null || echo '{}')
SCHED_STATUS=$(echo "$SCHED" | python3 -c "import sys,json; d=json.load(sys.stdin); c=d.get('components',{}); print(c.get('scheduler',{}).get('status',''))" 2>/dev/null || echo '')
check "Scheduler 状态" "ok" "$SCHED_STATUS"

# 8. Scheduler jobs 有 next_run
MISSING=$(echo "$SCHED" | python3 -c "
import sys,json
d=json.load(sys.stdin)
jobs = d.get('components',{}).get('scheduler',{}).get('jobs',[])
missing = [j['id'] for j in jobs if not j.get('next_run_time')]
print(len(missing))
" 2>/dev/null || echo '1')
check "Scheduler 任务已排期 (无 missing)" "0" "$MISSING"

# 9. 版本信息
VERSION=$(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('version',''))" 2>/dev/null || echo '')
check "版本信息正常" "2.7.17" "$VERSION"

echo ""
echo "========== 检查结果: $PASS 通过, $FAIL 失败 =========="

if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}所有检查通过！服务已就绪。${NC}"
    exit 0
else
    echo -e "${RED}有 $FAIL 项检查失败，请查看日志${NC}"
    exit 1
fi
