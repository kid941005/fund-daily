#!/bin/bash

# Fund Daily 部署脚本
# P2优化：部署自动化

set -e  # 遇到错误立即退出

echo "🚀 Fund Daily 部署脚本"
echo "======================"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
APP_NAME="fund-daily"
APP_DIR="/home/kid/fund-daily"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="$APP_DIR/logs"
DATA_DIR="$APP_DIR/data"
CONFIG_DIR="$APP_DIR/config"

# 显示配置
echo -e "${BLUE}📋 部署配置${NC}"
echo -e "  应用名称: $APP_NAME"
echo -e "  应用目录: $APP_DIR"
echo -e "  虚拟环境: $VENV_DIR"
echo -e "  日志目录: $LOG_DIR"
echo -e "  数据目录: $DATA_DIR"

# 检查目录
echo -e "\n${BLUE}📁 检查目录...${NC}"
for dir in "$LOG_DIR" "$DATA_DIR" "$CONFIG_DIR"; do
    if [ ! -d "$dir" ]; then
        mkdir -p "$dir"
        echo -e "  ✅ 创建目录: $dir"
    else
        echo -e "  ✅ 目录已存在: $dir"
    fi
done

# 检查Python环境
echo -e "\n${BLUE}🐍 检查Python环境...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "  🆕 创建虚拟环境..."
    python3 -m venv "$VENV_DIR"
    echo -e "  ✅ 虚拟环境创建完成"
else
    echo -e "  ✅ 虚拟环境已存在"
fi

# 激活虚拟环境并安装依赖
echo -e "\n${BLUE}📦 安装依赖...${NC}"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip > /dev/null 2>&1

if [ -f "$APP_DIR/requirements.txt" ]; then
    pip install -r "$APP_DIR/requirements.txt" > /dev/null 2>&1
    echo -e "  ✅ 依赖安装完成"
else
    echo -e "  ❌ 未找到requirements.txt"
    exit 1
fi

# 初始化数据库
echo -e "\n${BLUE}🗄️ 初始化数据库...${NC}"
cd "$APP_DIR"
python3 -c "
from db.database import init_db
init_db()
print('✅ 数据库初始化完成')
"

# 构建前端
echo -e "\n${BLUE}🌐 构建前端...${NC}"
if [ -d "$APP_DIR/web/vue3" ]; then
    cd "$APP_DIR/web/vue3"
    if [ -f "package.json" ]; then
        echo -e "  📦 安装前端依赖..."
        npm ci > /dev/null 2>&1 || npm install > /dev/null 2>&1
        
        echo -e "  🔨 构建前端..."
        npm run build > /dev/null 2>&1
        echo -e "  ✅ 前端构建完成"
    else
        echo -e "  ⚠️ 未找到package.json，跳过前端构建"
    fi
    cd "$APP_DIR"
else
    echo -e "  ⚠️ 未找到前端目录，跳过前端构建"
fi

# 生成API文档
echo -e "\n${BLUE}📚 生成API文档...${NC}"
cd "$APP_DIR"
python3 -c "
from src.openapi import OpenAPIGenerator
generator = OpenAPIGenerator()
generator.save_to_file('docs/openapi.json')
print('✅ API文档生成完成')
"

# 创建服务配置文件
echo -e "\n${BLUE}⚙️ 创建服务配置...${NC}"
SERVICE_FILE="/etc/systemd/system/$APP_NAME.service"
if [ ! -f "$SERVICE_FILE" ] && [ "$(id -u)" -eq 0 ]; then
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Fund Daily Investment Analysis System
After=network.target redis.service postgresql.service

[Service]
Type=simple
User=kid
WorkingDirectory=$APP_DIR
Environment="PATH=$VENV_DIR/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONPATH=$APP_DIR"
ExecStart=$VENV_DIR/bin/python3 $APP_DIR/web/app.py
Restart=on-failure
RestartSec=10
StandardOutput=append:$LOG_DIR/app.log
StandardError=append:$LOG_DIR/error.log

[Install]
WantedBy=multi-user.target
EOF
    echo -e "  ✅ Systemd服务文件创建完成"
    echo -e "     启动服务: sudo systemctl start $APP_NAME"
    echo -e "     启用自启动: sudo systemctl enable $APP_NAME"
elif [ "$(id -u)" -ne 0 ]; then
    echo -e "  ⚠️ 需要root权限创建systemd服务"
    echo -e "     手动启动: $VENV_DIR/bin/python3 $APP_DIR/web/app.py"
fi

# 创建环境配置文件
echo -e "\n${BLUE}🔧 创建环境配置...${NC}"
ENV_FILE="$APP_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    cat > "$ENV_FILE" << 'EOF'
# Fund Daily 环境配置
# 数据库配置
FUND_DAILY_DB_TYPE=postgres
FUND_DAILY_DB_HOST=localhost
FUND_DAILY_DB_PORT=5432
FUND_DAILY_DB_NAME=fund_daily
FUND_DAILY_DB_USER=kid
FUND_DAILY_DB_PASSWORD=941005

# Redis配置
FUND_DAILY_REDIS_URL=redis://localhost:6379/0

# 安全配置
FUND_DAILY_SECRET_KEY=your-secret-key-here-change-in-production
FUND_DAILY_SESSION_TIMEOUT=86400

# 应用配置
FUND_DAILY_ENV=production
FUND_DAILY_DEBUG=false
FUND_DAILY_LOG_LEVEL=INFO

# API配置
FUND_DAILY_REQUEST_INTERVAL=0.5
FUND_DAILY_CACHE_DURATION=1800
EOF
    echo -e "  ✅ 环境配置文件创建完成: $ENV_FILE"
    echo -e "     ⚠️ 请修改SECRET_KEY和其他敏感配置"
else
    echo -e "  ✅ 环境配置文件已存在: $ENV_FILE"
fi

# 创建Nginx配置（可选）
echo -e "\n${BLUE}🌐 创建Nginx配置（可选）...${NC}"
NGINX_FILE="/etc/nginx/sites-available/$APP_NAME"
if [ ! -f "$NGINX_FILE" ] && [ -d "/etc/nginx" ] && [ "$(id -u)" -eq 0 ]; then
    cat > "$NGINX_FILE" << EOF
server {
    listen 80;
    server_name fund-daily.local;
    
    # 前端静态文件
    location / {
        root $APP_DIR/web/dist;
        try_files \$uri \$uri/ /index.html;
        expires 1h;
    }
    
    # API代理
    location /api {
        proxy_pass http://localhost:5007;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    # 静态文件缓存
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
        root $APP_DIR/web/dist;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # 访问日志
    access_log $LOG_DIR/nginx-access.log;
    error_log $LOG_DIR/nginx-error.log;
}
EOF
    
    # 启用站点
    ln -sf "$NGINX_FILE" "/etc/nginx/sites-enabled/$APP_NAME"
    echo -e "  ✅ Nginx配置文件创建完成"
    echo -e "     重新加载Nginx: sudo nginx -t && sudo systemctl reload nginx"
elif [ "$(id -u)" -ne 0 ]; then
    echo -e "  ⚠️ 需要root权限创建Nginx配置"
fi

# 显示部署完成信息
echo -e "\n${GREEN}🎉 部署完成！${NC}"
echo -e "=================================="
echo -e "${BLUE}📊 部署摘要${NC}"
echo -e "  应用目录: $APP_DIR"
echo -e "  虚拟环境: $VENV_DIR"
echo -e "  日志目录: $LOG_DIR"
echo -e "  数据目录: $DATA_DIR"
echo -e "  API文档: $APP_DIR/docs/openapi.json"
echo -e ""
echo -e "${BLUE}🚀 启动应用${NC}"
echo -e "  手动启动:"
echo -e "    cd $APP_DIR"
echo -e "    source $VENV_DIR/bin/activate"
echo -e "    python3 web/app.py"
echo -e ""
echo -e "  或使用systemd（需要root）:"
echo -e "    sudo systemctl start $APP_NAME"
echo -e "    sudo systemctl enable $APP_NAME"
echo -e ""
echo -e "${BLUE}🌐 访问应用${NC}"
echo -e "  Web界面: http://localhost:5007"
echo -e "  API文档: http://localhost:5007/api/docs"
echo -e "  性能监控: http://localhost:5007/api/metrics/enhanced"
echo -e ""
echo -e "${YELLOW}⚠️ 注意事项${NC}"
echo -e "  1. 修改 $ENV_FILE 中的敏感配置"
echo -e "  2. 确保数据库服务正在运行"
echo -e "  3. 生产环境请使用HTTPS"
echo -e "=================================="