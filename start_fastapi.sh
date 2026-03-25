#!/bin/bash
# Fund Daily FastAPI 启动脚本
# 用法: ./start_fastapi.sh [端口]

set -e

# 配置
PORT=${1:-5007}
DB_PASSWORD=${FUND_DAILY_DB_PASSWORD:-941005}
ENV=${FUND_DAILY_ENV:-development}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Fund Daily - FastAPI Mode${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查依赖
check_deps() {
    echo -e "\n${YELLOW}[1/4] 检查依赖...${NC}"
    
    # Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}错误: Python3 未安装${NC}"
        exit 1
    fi
    echo -e "  Python: $(python3 --version)"
    
    # Redis
    if command -v redis-cli &> /dev/null; then
        echo -e "  Redis: $(redis-cli --version)"
    else
        echo -e "${YELLOW}  Redis: 未检测到（可能已在Docker中运行）${NC}"
    fi
    
    # PostgreSQL
    if command -v psql &> /dev/null; then
        echo -e "  PostgreSQL: $(psql --version)"
    else
        echo -e "${YELLOW}  PostgreSQL: 未检测到（可能已在Docker中运行）${NC}"
    fi
}

# 安装依赖
install_deps() {
    echo -e "\n${YELLOW}[2/4] 安装Python依赖...${NC}"
    
    if [ ! -d ".venv" ]; then
        echo -e "  创建虚拟环境..."
        python3 -m venv .venv
    fi
    
    source .venv/bin/activate
    pip install --quiet -q fastapi uvicorn[standard] python-multipart python-jose[cryptography] passlib[bcrypt] pydantic
    echo -e "  依赖安装完成"
}

# 检查服务
check_services() {
    echo -e "\n${YELLOW}[3/4] 检查外部服务...${NC}"
    
    # PostgreSQL
    if python3 -c "import psycopg2; conn = psycopg2.connect(host='localhost', port=5432, user='kid', password='$DB_PASSWORD', dbname='fund_daily'); conn.close()" 2>/dev/null; then
        echo -e "  ${GREEN}PostgreSQL: 已连接${NC}"
    else
        echo -e "${RED}  PostgreSQL: 无法连接 (host=localhost:5432)${NC}"
        echo -e "${YELLOW}  提示: 确保PostgreSQL服务正在运行${NC}"
    fi
    
    # Redis
    if python3 -c "import redis; r = redis.Redis(host='localhost', port=6379); r.ping()" 2>/dev/null; then
        echo -e "  ${GREEN}Redis: 已连接${NC}"
    else
        echo -e "${YELLOW}  Redis: 无法连接 (host=localhost:6379)${NC}"
    fi
}

# 启动服务
start_server() {
    echo -e "\n${YELLOW}[4/4] 启动FastAPI服务...${NC}"
    
    source .venv/bin/activate
    
    export FUND_DAILY_SERVER_PORT=$PORT
    export FUND_DAILY_DB_PASSWORD=$DB_PASSWORD
    export FUND_DAILY_ENV=$ENV
    
    echo -e "  端口: $PORT"
    echo -e "  环境: $ENV"
    echo -e "  数据库: localhost:5432/fund_daily"
    echo -e ""
    
    # 使用 uvicorn 启动
    exec uvicorn web.api_fastapi.main:app \
        --host 0.0.0.0 \
        --port $PORT \
        --reload \
        --log-level info
}

# 主流程
check_deps
install_deps
check_services
start_server
