#!/bin/bash
# Fund Daily 健康检查 + 告警脚本
# 用法: ./scripts/health_check.sh [ALERT_THRESHOLD]
# 推荐 crontab: */5 * * * * /home/kid/fund-daily/scripts/health_check.sh >> /var/log/fund-daily-health.log 2>&1

set -euo pipefail

# ========== 配置 ==========
FUND_DAILY_HOST="${FUND_DAILY_HOST:-localhost}"
FUND_DAILY_PORT="${FUND_DAILY_PORT:-5007}"
ALERT_THRESHOLD="${1:-${ALERT_THRESHOLD_HOURS:-24}}"
WEBHOOK_URL="${WEBHOOK_URL:-}"          # 飞书机器人 WebHook（可选）
PAGERDUTY_KEY="${PAGERDUTY_KEY:-}"       # PagerDuty key（可选）
LOG_FILE="${LOG_FILE:-/tmp/fund-daily-health.log}"

BASE_URL="http://${FUND_DAILY_HOST}:${FUND_DAILY_PORT}"
TIMEOUT=10

# 颜色输出
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m'

# ========== 工具函数 ==========
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

send_alert() {
    local severity="$1"   # CRITICAL / WARNING / INFO
    local message="$2"
    local now="$(date '+%Y-%m-%d %H:%M:%S')"

    echo -e "${RED}[${severity}]${NC} ${message}"
    echo "[${now}] [${severity}] ${message}" >> "$LOG_FILE"

    # 飞书 WebHook
    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -s -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"msg_type\":\"text\",\"content\":{\"text\":\"[Fund Daily ${severity}] ${message}\"}}" \
            --max-time 10 || true
    fi
}

check_http() {
    local url="$1"
    local name="$2"
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")
    echo "$code"
}

# ========== 主检查 ==========
log "========== 开始健康检查 =========="

# 1. 基础连通性
HTTP_CODE=$(check_http "${BASE_URL}/api/health" "basic")
if [[ "$HTTP_CODE" != "200" ]]; then
    send_alert "CRITICAL" "服务不可达 (HTTP $HTTP_CODE) - ${BASE_URL}/api/health"
    exit 2
fi
echo -e "${GREEN}[OK]${NC} 服务响应正常 (HTTP 200)"

# 2. 详细健康检查
RESPONSE=$(curl -s --max-time "$TIMEOUT" "${BASE_URL}/health/detailed" 2>/dev/null || '{}')
SCHEDULER_STATUS=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); c=d.get('components',{}); s=c.get('scheduler',{}); print(s.get('status','unknown'))" 2>/dev/null || echo "unknown")
NAV_STALE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); f=d.get('components',{}).get('data_freshness',{}).get('nav',{}); print(f.get('stale','unknown'))" 2>/dev/null || echo "unknown")
SCORE_STALE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); f=d.get('components',{}).get('data_freshness',{}).get('scores',{}); print(f.get('stale','unknown'))" 2>/dev/null || echo "unknown")
NAV_AGE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); f=d.get('components',{}).get('data_freshness',{}).get('nav',{}); print(f.get('age_hours','N/A'))" 2>/dev/null || echo "N/A")
SCORE_AGE=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); f=d.get('components',{}).get('data_freshness',{}).get('scores',{}); print(f.get('age_hours','N/A'))" 2>/dev/null || echo "N/A")
TODAY_COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('components',{}).get('data_freshness',{}).get('nav',{}).get('today_count',0))" 2>/dev/null || echo "0")

# 3. Scheduler 状态
if [[ "$SCHEDULER_STATUS" == "error" ]]; then
    send_alert "CRITICAL" "Scheduler 运行异常 - 请检查日志"
elif [[ "$SCHEDULER_STATUS" == "unknown" ]]; then
    send_alert "WARNING" "无法获取 Scheduler 状态"
fi

# 4. 数据新鲜度
if [[ "$NAV_STALE" == "True" ]]; then
    send_alert "CRITICAL" "净值数据已 stale (${NAV_AGE}h 未更新) - 可能定时任务失效"
fi

if [[ "$SCORE_STALE" == "True" ]]; then
    send_alert "WARNING" "评分数据已 stale (${SCORE_AGE}h 未更新)"
fi

# 5. 今日数据检查
if [[ "$TODAY_COUNT" == "0" ]]; then
    send_alert "WARNING" "今日无净值数据更新 (交易日数据缺失)"
fi

# 6. Scheduler jobs missing next_run_time
MISSING_JOBS=$(echo "$RESPONSE" | python3 -c "
import sys,json
d=json.load(sys.stdin)
jobs = d.get('components',{}).get('scheduler',{}).get('jobs',[])
missing = [j['id'] for j in jobs if j.get('missed')]
print(','.join(missing))" 2>/dev/null || echo "")
if [[ -n "$MISSING_JOBS" ]]; then
    send_alert "CRITICAL" "Scheduler 任务失效: ${MISSING_JOBS} - 定时任务未安排"
fi

# 7. 全部正常
if [[ "$SCHEDULER_STATUS" == "ok" ]] && [[ "$NAV_STALE" != "True" ]] && [[ "$SCORE_STALE" != "True" ]] && [[ "$TODAY_COUNT" != "0" ]]; then
    echo -e "${GREEN}[OK]${NC} Scheduler: $SCHEDULER_STATUS | NAV: ${NAV_AGE}h | Score: ${SCORE_AGE}h | Today records: ${TODAY_COUNT}"
    log "========== 健康检查完成（正常）=========="
    exit 0
fi

log "========== 健康检查完成（发现警告）=========="
exit 1
