#!/bin/bash
# Fund Daily Docker 环境设置脚本

set -e

echo "🔧 设置 Fund Daily Docker 环境..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装。请先安装 Docker。"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装。请先安装 Docker Compose。"
    exit 1
fi

# 创建必要的目录
echo "📁 创建目录..."
mkdir -p nginx/ssl prometheus grafana/{dashboards,datasources} data/backups

# 复制环境变量文件
if [ ! -f .env ]; then
    echo "📄 复制环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，设置强密码和密钥"
    echo "   重要: 生成安全密钥:"
    echo "   python -c \"import secrets; print('FUND_DAILY_SECRET_KEY=' + secrets.token_hex(32))\""
    echo "   python -c \"import secrets; print('FUND_DAILY_JWT_SECRET=' + secrets.token_hex(32))\""
fi

# 生成 SSL 证书（自签名，生产环境需要真实证书）
if [ ! -f nginx/ssl/privkey.pem ]; then
    echo "🔐 生成自签名 SSL 证书..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout nginx/ssl/privkey.pem \
        -out nginx/ssl/fullchain.pem \
        -subj "/C=CN/ST=Beijing/L=Beijing/O=Fund Daily/CN=localhost" 2>/dev/null || \
    echo "⚠️  SSL 证书生成失败，跳过此步骤"
fi

# 设置文件权限
echo "🔒 设置文件权限..."
chmod 600 .env 2>/dev/null || true
chmod 755 scripts/*.sh 2>/dev/null || true

# 构建镜像
echo "🐳 构建 Docker 镜像..."
docker-compose build --pull

echo ""
echo "✅ 环境设置完成！"
echo ""
echo "下一步:"
echo "1. 编辑 .env 文件，设置强密码和密钥"
echo "2. 启动服务: docker-compose up -d"
echo "3. 查看日志: docker-compose logs -f"
echo "4. 访问应用: http://localhost:5007"
echo ""
echo "开发环境:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d"
echo ""
echo "生产环境:"
echo "  1. 复制生产配置: cp docker-compose.prod.yml.example docker-compose.prod.yml"
echo "  2. 设置 Docker 密钥: echo 'your_password' | docker secret create postgres_password -"
echo "  3. 启动: docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml fund-daily"