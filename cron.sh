#!/bin/bash
# Cron script for fund daily report

FUND_CODES=${FUND_CODES:-"000001,110022,161725"}
REPORT_TIME=${REPORT_TIME:-"15:00"}

while true; do
    CURRENT_TIME=$(date +%H:%M)
    
    if [ "$CURRENT_TIME" = "$REPORT_TIME" ]; then
        echo "Generating fund report at $(date)"
        
        # Generate report
        REPORT=$(python3 /app/fund-daily.py share $FUND_CODES)
        
        # Save to file
        echo "$REPORT" > /app/data/fund_report_$(date +%Y%m%d).txt
        
        # Send to Telegram if configured
        if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
            curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
                -d "chat_id=$TELEGRAM_CHAT_ID" \
                -d "text=$REPORT" \
                -d "parse_mode=HTML"
        fi
        
        # Wait 1 minute to avoid duplicate
        sleep 60
    fi
    
    # Check every minute
    sleep 60
done
