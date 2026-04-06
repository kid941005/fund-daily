#!/bin/bash
# Fund Daily 服务重启脚本 - 修复数据库连接问题

set -e

# 配置
PORT=${1:-5007}
PID_FILE="/tmp/fund-daily.pid"
LOG_FILE="/tmp/fund-daily.log"

# 数据库配置（正确的 kid 用户）
export FUND_DAILY_DB_USER=kid
export FUND_DAILY_DB_PASSWORD=941005
export FUND_DAILY_DB_HOST=localhost
export FUND_DAILY_DB_PORT=5432
export FUND_DAILY_DB_NAME=fund_daily

echo "========================================="
echo "  Fund Daily 重启脚本"
echo "========================================="
echo "数据库: ${FUND_DAILY_DB_USER}@${FUND_DAILY_DB_HOST}:${FUND_DAILY_DB_PORT}/${FUND_DAILY_DB_NAME}"

# 查找并终止旧进程
OLD_PID=$(pgrep -f "uvicorn web.api_fastapi.main:app" 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
    echo "终止旧进程: PID=$OLD_PID"
    kill $OLD_PID 2>/dev/null || sudo kill $OLD_PID 2>/dev/null || true
    sleep 2
fi

# 确保端口可用
if netstat -tlnp 2>/dev/null | grep -q ":$PORT "; then
    echo "警告: 端口 $PORT 仍被占用，强制终止..."
    fuser -k $PORT/tcp 2>/dev/null || true
    sleep 1
fi

cd /home/kid/fund-daily

# 启动服务
echo "启动服务 (端口: $PORT)..."
nohup python3 -m uvicorn web.api_fastapi.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    >> $LOG_FILE 2>&1 &

NEW_PID=$!
echo $NEW_PID > $PID_FILE
echo "新进程 PID: $NEW_PID"

# 等待服务启动
sleep 3

# 验证服务
if curl -s http://localhost:$PORT/api/config > /dev/null 2>&1; then
    echo "✅ 服务启动成功!"
else
    echo "❌ 服务启动失败，请检查日志: $LOG_FILE"
    tail -20 $LOG_FILE
    exit 1
fi

echo "========================================="
echo "日志文件: $LOG_FILE"
echo "进程ID: $NEW_PID"
echo "========================================="
