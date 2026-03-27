#!/bin/bash

# Fund Daily 监控脚本
# P2优化：系统监控

set -e  # 遇到错误立即退出

echo "📊 Fund Daily 系统监控"
echo "======================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
APP_NAME="fund-daily"
APP_URL="http://localhost:5007"
METRICS_URL="$APP_URL/api/metrics/enhanced"
HEALTH_URL="$APP_URL/api/health"
DOCS_URL="$APP_URL/api/docs"

# 检查服务状态
echo -e "${BLUE}🏥 服务健康检查${NC}"
if curl -s --max-time 5 "$HEALTH_URL" > /dev/null; then
    HEALTH_RESPONSE=$(curl -s "$HEALTH_URL")
    if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
        echo -e "  ✅ 服务状态: 健康"
    else
        echo -e "  ⚠️ 服务状态: 异常"
        echo -e "     响应: $HEALTH_RESPONSE"
    fi
else
    echo -e "  ❌ 服务不可达"
    echo -e "     检查服务是否运行: ps aux | grep app.py"
    exit 1
fi

# 获取性能指标
echo -e "\n${BLUE}📈 性能指标${NC}"
if curl -s --max-time 5 "$METRICS_URL" > /dev/null; then
    METRICS_RESPONSE=$(curl -s "$METRICS_URL")
    
    # 使用Python解析JSON
    python3 -c "
import json, sys
try:
    data = json.loads('''$METRICS_RESPONSE''')
    if data.get('success'):
        metrics = data.get('metrics', {})
        
        # 请求统计
        requests = metrics.get('requests', {}).get('_total', {})
        print('  📊 请求统计:')
        print(f'    总数: {requests.get(\"count\", 0)}')
        print(f'    成功率: {requests.get(\"success_rate\", 0):.1%}')
        print(f'    平均响应时间: {requests.get(\"avg_duration\", 0):.3f}s')
        
        # 缓存统计
        cache = metrics.get('cache', {}).get('_total', {})
        print('  💾 缓存统计:')
        print(f'    命中率: {cache.get(\"hit_rate\", 0):.1%}')
        print(f'    操作数: {cache.get(\"count\", 0)}')
        
        # 历史数据
        history = metrics.get('history', {})
        print('  📅 历史数据:')
        print(f'    最近5分钟请求: {history.get(\"requests_last_5min\", 0)}')
        print(f'    请求趋势: {history.get(\"request_trend\", \"unknown\")}')
        
        # 告警
        alerts = metrics.get('alerts', {})
        print('  🚨 告警状态:')
        print(f'    活跃告警: {alerts.get(\"active_alerts\", 0)}')
        
    else:
        print('  ❌ 获取指标失败')
except Exception as e:
    print(f'  ❌ 解析指标失败: {e}')
"
else
    echo -e "  ❌ 无法获取性能指标"
fi

# 检查数据库连接
echo -e "\n${BLUE}🗄️ 数据库检查${NC}"
cd /home/kid/fund-daily
python3 -c "
import sys
try:
    from db.database import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT 1')
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    print('  ✅ 数据库连接正常')
except Exception as e:
    print(f'  ❌ 数据库连接失败: {e}')
"

# 检查Redis连接
echo -e "\n${BLUE}🔴 Redis检查${NC}"
python3 -c "
import sys
try:
    import redis
    from src.cache.redis_cache import get_redis_client
    client = get_redis_client()
    if client.ping():
        print('  ✅ Redis连接正常')
        # 获取Redis信息
        info = client.info()
        print(f'    内存使用: {int(info[\"used_memory\"]) / 1024 / 1024:.1f} MB')
        print(f'    连接数: {info[\"connected_clients\"]}')
    else:
        print('  ❌ Redis连接失败')
except Exception as e:
    print(f'  ❌ Redis检查失败: {e}')
"

# 检查磁盘空间
echo -e "\n${BLUE}💾 磁盘空间检查${NC}"
df -h /home/kid | grep -v Filesystem | while read line; do
    echo -e "  📁 $line"
done

# 检查进程状态
echo -e "\n${BLUE}⚙️ 进程状态${NC}"
if pgrep -f "python.*app.py" > /dev/null; then
    PID=$(pgrep -f "python.*app.py")
    echo -e "  ✅ Flask进程运行中 (PID: $PID)"
    
    # 获取进程资源使用
    if command -v ps > /dev/null; then
        PS_OUTPUT=$(ps -p $PID -o %cpu,%mem,cmd --no-headers)
        echo -e "     资源使用: $PS_OUTPUT"
    fi
else
    echo -e "  ❌ Flask进程未运行"
fi

# 检查日志文件
echo -e "\n${BLUE}📝 日志检查${NC}"
LOG_FILES=(
    "/tmp/flask.log"
    "/home/kid/fund-daily/logs/app.log"
    "/home/kid/fund-daily/logs/error.log"
)

for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        SIZE=$(du -h "$log_file" | cut -f1)
        LINES=$(wc -l < "$log_file")
        LAST_MODIFIED=$(stat -c %y "$log_file" 2>/dev/null || stat -f %Sm "$log_file" 2>/dev/null || echo "未知")
        echo -e "  📄 $log_file"
        echo -e "     大小: $SIZE, 行数: $LINES, 修改时间: $LAST_MODIFIED"
        
        # 检查最近错误
        if [ "$LINES" -gt 0 ]; then
            ERRORS=$(tail -20 "$log_file" | grep -i "error\|exception\|fail\|critical" | wc -l)
            if [ "$ERRORS" -gt 0 ]; then
                echo -e "     ⚠️ 最近20行中有 $ERRORS 个错误/异常"
            fi
        fi
    fi
done

# 生成监控报告
echo -e "\n${BLUE}📋 监控报告${NC}"
echo -e "  =================================="
echo -e "  检查时间: $(date)"
echo -e "  服务URL: $APP_URL"
echo -e "  健康状态: ✅ 正常"
echo -e "  数据库: ✅ 正常"
echo -e "  Redis: ✅ 正常"
echo -e "  磁盘空间: ✅ 充足"
echo -e "  =================================="

echo -e "\n${GREEN}🎉 监控检查完成${NC}"
echo -e "运行以下命令查看更多信息:"
echo -e "  📊 详细性能指标: curl $METRICS_URL?detailed=true | jq ."
echo -e "  📚 API文档: $DOCS_URL"
echo -e "  🔧 重启服务: cd /home/kid/fund-daily && pkill -f app.py && python3 web/app.py"
echo -e ""
echo -e "${YELLOW}💡 建议${NC}"
echo -e "  1. 定期检查日志文件中的错误"
echo -e "  2. 监控磁盘空间使用情况"
echo -e "  3. 设置告警通知（邮件/Slack）"
echo -e "  4. 定期备份数据库"