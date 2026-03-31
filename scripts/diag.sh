#!/bin/bash
# Fund Daily 日志诊断脚本
# 用法: ./scripts/diag.sh [LOG_FILE]

LOG="${1:-/tmp/fund-daily.log}"

RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}========== Fund Daily 日志诊断 ==========${NC}"
echo "日志文件: $LOG"
echo ""

# 1. 错误和警告统计
ERRORS=$(grep -c "ERROR" "$LOG" 2>/dev/null || echo "0")
WARNINGS=$(grep -c "WARNING" "$LOG" 2>/dev/null || echo "0")
CRITICAL=$(grep -c "CRITICAL" "$LOG" 2>/dev/null || echo "0")

echo -e "${CYAN}错误统计:${NC}"
echo -e "  ERROR: ${RED}$ERRORS${NC}"
echo -e "  WARNING: ${YELLOW}$WARNINGS${NC}"
echo -e "  CRITICAL: ${RED}$CRITICAL${NC}"
echo ""

# 2. 最新错误 (最近 10 条)
echo -e "${CYAN}最新错误 (最近 10 条):${NC}"
grep "ERROR\|CRITICAL" "$LOG" 2>/dev/null | tail -10 | while read -r line; do
    echo -e "  ${RED}$line${NC}"
done
echo ""

# 3. Scheduler 相关问题
echo -e "${CYAN}Scheduler 问题:${NC}"
SCHED_ISSUES=$(grep -i "scheduler\|missed\|failed.*job\|conflicts" "$LOG" 2>/dev/null | tail -10)
if [[ -n "$SCHED_ISSUES" ]]; then
    echo "$SCHED_ISSUES" | while read -r line; do
        echo -e "  ${YELLOW}$line${NC}"
    done
else
    echo -e "  ${GREEN}无 Scheduler 问题${NC}"
fi
echo ""

# 4. 数据库连接问题
echo -e "${CYAN}数据库问题:${NC}"
DB_ISSUES=$(grep -i "database\|postgres\|psycopg\|connection.*fail\|pool" "$LOG" 2>/dev/null | tail -10)
if [[ -n "$DB_ISSUES" ]]; then
    echo "$DB_ISSUES" | while read -r line; do
        echo -e "  ${YELLOW}$line${NC}"
    done
else
    echo -e "  ${GREEN}无数据库问题${NC}"
fi
echo ""

# 5. Redis 问题
echo -e "${CYAN}Redis 问题:${NC}"
REDIS_ISSUES=$(grep -i "redis\|cache\|ConnectionError\|TimeoutError" "$LOG" 2>/dev/null | tail -10)
if [[ -n "$REDIS_ISSUES" ]]; then
    echo "$REDIS_ISSUES" | while read -r line; do
        echo -e "  ${YELLOW}$line${NC}"
    done
else
    echo -e "  ${GREEN}无 Redis 问题${NC}"
fi
echo ""

# 6. 最近 20 行日志
echo -e "${CYAN}最近 20 行:${NC}"
tail -20 "$LOG" 2>/dev/null | while read -r line; do
    if echo "$line" | grep -q "ERROR\|CRITICAL"; then
        echo -e "  ${RED}$line${NC}"
    elif echo "$line" | grep -q "WARNING"; then
        echo -e "  ${YELLOW}$line${NC}"
    else
        echo "  $line"
    fi
done

echo ""
echo -e "${CYAN}=========================================${NC}"
