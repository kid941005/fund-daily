#!/bin/bash
# Cron script for fund daily report
# 支持：定期报告 + 涨跌幅监控

FUND_CODES=${FUND_CODES:-"000001,110022,161725"}
REPORT_TIME=${REPORT_TIME:-"15:00"}
ALERT_THRESHOLD=${ALERT_THRESHOLD:-"3.0"}
CHECK_INTERVAL=${CHECK_INTERVAL:-"300"}  # 涨跌幅检查间隔(秒)

# 导入通知模块
export PYTHONPATH="/app:$PYTHONPATH"

# 上次提醒记录
LAST_ALERT_FILE="/tmp/fund_alerts.json"

check_alert() {
    local code=$1
    local threshold=$2
    
    # 获取基金数据
    DATA=$(python3 /app/fund-daily.py analyze "$code" 2>/dev/null)
    if [ $? -ne 0 ]; then
        return
    fi
    
    # 解析涨跌幅
    CHANGE=$(echo "$DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('daily_change', 0))" 2>/dev/null)
    if [ -z "$CHANGE" ]; then
        return
    fi
    
    ABS_CHANGE=$(echo "$CHANGE" | tr -d '-')
    
    # 检查是否超过阈值
    IS_OVER=$(echo "$ABS_CHANGE > $threshold" | bc -l 2>/dev/null)
    if [ "$IS_OVER" = "1" ]; then
        # 检查是否已经提醒过(1小时内)
        LAST_TIME=$(python3 -c "
import json, time
try:
    with open('$LAST_ALERT_FILE', 'r') as f:
        alerts = json.load(f)
    print(alerts.get('$code', 0))
except: print(0)
" 2>/dev/null)
        
        NOW=$(date +%s)
        DIFF=$((NOW - LAST_TIME))
        
        if [ "$DIFF" -gt 3600 ]; then
            NAME=$(echo "$DATA" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('fund_name', '$code'))" 2>/dev/null)
            EMOJI="📈"
            if (( $(echo "$CHANGE < 0" | bc -l 2>/dev/null) )); then
                EMOJI="📉"
            fi
            
            MSG="$EMOJI 基金${CHANGE}波动提醒
基金: $NAME
代码: $code
涨跌: ${CHANGE}%
时间: $(date '+%Y-%m-%d %H:%M:%S')"
            
            # 发送Telegram
            if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
                curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                    -d "chat_id=$TELEGRAM_CHAT_ID" \
                    -d "text=$MSG" > /dev/null
            fi
            
            # 发送钉钉
            if [ -n "$DINGTALK_WEBHOOK" ]; then
                curl -s -X POST "$DINGTALK_WEBHOOK" \
                    -H "Content-Type: application/json" \
                    -d "{\"msgtype\": \"text\", \"text\": {\"content\": \"[基金提醒] $MSG\"}}" > /dev/null
            fi
            
            # 记录提醒时间
            python3 -c "
import json, time
try:
    with open('$LAST_ALERT_FILE', 'r') as f:
        alerts = json.load(f)
except: alerts = {}
alerts['$code'] = int(time.time())
with open('$LAST_ALERT_FILE', 'w') as f:
    json.dump(alerts, f)
" 2>/dev/null
            
            echo "$(date): 发送 $code 涨跌幅提醒: $CHANGE%"
        fi
    fi
}

# 清理超过24小时的记录
cleanup_alerts() {
    python3 -c "
import json, time
try:
    with open('$LAST_ALERT_FILE', 'r') as f:
        alerts = json.load(f)
    now = int(time.time())
    alerts = {k:v for k,v in alerts.items() if now - v < 86400}
    with open('$LAST_ALERT_FILE', 'w') as f:
        json.dump(alerts, f)
except: pass
" 2>/dev/null
}

echo "Fund Cron Started - Codes: $FUND_CODES, Alert Threshold: ${ALERT_THRESHOLD}%"

# 立即清理一次
cleanup_alerts

# 记录上次报告时间
LAST_REPORT_DATE=""

while true; do
    CURRENT_TIME=$(date +%H:%M)
    CURRENT_DATE=$(date +%Y%m%d)
    
    # 1. 定时报告 (每天一次)
    if [ "$CURRENT_TIME" = "$REPORT_TIME" ] && [ "$LAST_REPORT_DATE" != "$CURRENT_DATE" ]; then
        echo "$(date): Generating daily report"
        
        # Generate report
        REPORT=$(python3 /app/fund-daily.py share $FUND_CODES 2>/dev/null)
        
        # Save to file
        echo "$REPORT" > /app/data/fund_report_${CURRENT_DATE}.txt
        
        # Send to Telegram
        if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
            curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                -d "chat_id=$TELEGRAM_CHAT_ID" \
                -d "text=$REPORT" \
                -d "parse_mode=HTML" > /dev/null
        fi
        
        LAST_REPORT_DATE=$CURRENT_DATE
        echo "$(date): Daily report sent"
    fi
    
    # 2. 涨跌幅监控 (每5分钟检查一次)
    for code in $(echo "$FUND_CODES" | tr ',' ' '); do
        check_alert "$code" "$ALERT_THRESHOLD"
    done
    
    # 清理旧记录 (每小时)
    MINUTE=$(date +%M)
    if [ "$MINUTE" = "00" ]; then
        cleanup_alerts
    fi
    
    # 等待下次检查
    sleep $CHECK_INTERVAL
done
