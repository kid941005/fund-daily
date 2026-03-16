#!/bin/bash
cd /home/kid/fund-daily
export FUND_DAILY_DB_PATH=/home/kid/fund-daily/data/fund-daily.db
exec python3 -m flask run --host=0.0.0.0 --port=5000
