#!/bin/bash
# Fund Daily 启动脚本

cd /home/kid/fund-daily

# 设置数据库环境变量
export FUND_DAILY_DB_HOST=localhost
export FUND_DAILY_DB_PASSWORD=941005
export FUND_DAILY_SERVER_PORT=5007

# 启动服务
exec python3 web/app.py
