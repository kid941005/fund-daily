#!/bin/bash

# Fund Daily CI/CD 本地脚本
# P2优化：持续集成配置

set -e  # 遇到错误立即退出

echo "🚀 Fund Daily CI/CD 本地脚本启动"
echo "=================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查依赖
echo -e "${BLUE}📦 检查依赖...${NC}"
check_dependency() {
    if command -v $1 >/dev/null 2>&1; then
        echo -e "  ✅ $1: $(which $1)"
    else
        echo -e "  ❌ $1: 未安装"
        return 1
    fi
}

check_dependency python3 || exit 1
check_dependency pip3 || exit 1
check_dependency redis-cli || echo -e "  ⚠️ redis-cli: 未安装（可选）"
check_dependency psql || echo -e "  ⚠️ psql: 未安装（可选）"

# 检查Python版本
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo -e "  📊 Python版本: $PYTHON_VERSION"

# 安装依赖
echo -e "\n${BLUE}📦 安装依赖...${NC}"
pip3 install -r requirements.txt > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "  ✅ 依赖安装成功"
else
    echo -e "  ❌ 依赖安装失败"
    exit 1
fi

# 安装测试依赖
echo -e "\n${BLUE}🧪 安装测试依赖...${NC}"
pip3 install pytest pytest-cov pytest-mock flake8 black isort > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "  ✅ 测试依赖安装成功"
else
    echo -e "  ❌ 测试依赖安装失败"
    exit 1
fi

# 运行测试
echo -e "\n${BLUE}🧪 运行测试...${NC}"
export FUND_DAILY_DB_TYPE=sqlite
export FUND_DAILY_SECRET_KEY=test-secret-key-for-ci

pytest tests/ -v --cov=src --cov-report=term-missing
TEST_EXIT_CODE=$?

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}✅ 所有测试通过${NC}"
else
    echo -e "\n${RED}❌ 测试失败${NC}"
    exit 1
fi

# 代码质量检查
echo -e "\n${BLUE}🔍 代码质量检查...${NC}"

# Flake8检查
echo -e "  📋 Flake8检查..."
flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
FLAKE8_CRITICAL=$?

flake8 src/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
FLAKE8_ALL=$?

if [ $FLAKE8_CRITICAL -eq 0 ]; then
    echo -e "  ✅ Flake8关键检查通过"
else
    echo -e "  ⚠️ Flake8发现关键问题"
fi

# Black检查
echo -e "  🎨 Black代码格式化检查..."
black --check src/
BLACK_EXIT=$?

if [ $BLACK_EXIT -eq 0 ]; then
    echo -e "  ✅ Black检查通过"
else
    echo -e "  ⚠️ Black检查失败，运行 'black src/' 修复格式"
fi

# isort检查
echo -e "  📚 isort导入排序检查..."
isort --check-only src/
ISORT_EXIT=$?

if [ $ISORT_EXIT -eq 0 ]; then
    echo -e "  ✅ isort检查通过"
else
    echo -e "  ⚠️ isort检查失败，运行 'isort src/' 修复导入排序"
fi

# 生成API文档
echo -e "\n${BLUE}📚 生成API文档...${NC}"
python3 -c "
from src.openapi import OpenAPIGenerator
generator = OpenAPIGenerator()
generator.save_to_file('docs/openapi.json')
print('✅ OpenAPI文档已生成')
"

# 构建前端
echo -e "\n${BLUE}🌐 构建前端...${NC}"
if [ -d "web/vue3" ]; then
    cd web/vue3
    if [ -f "package.json" ]; then
        echo -e "  📦 安装前端依赖..."
        npm ci > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "  ✅ 前端依赖安装成功"
        else
            echo -e "  ⚠️ 前端依赖安装失败，尝试npm install..."
            npm install > /dev/null 2>&1
        fi
        
        echo -e "  🔨 构建前端..."
        npm run build > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo -e "  ✅ 前端构建成功"
        else
            echo -e "  ❌ 前端构建失败"
        fi
    else
        echo -e "  ⚠️ 未找到package.json，跳过前端构建"
    fi
    cd ../..
else
    echo -e "  ⚠️ 未找到web/vue3目录，跳过前端构建"
fi

# 检查服务健康
echo -e "\n${BLUE}🏥 检查服务健康...${NC}"
# 检查Flask服务是否在运行
if pgrep -f "python.*app.py" > /dev/null; then
    echo -e "  ✅ Flask服务正在运行"
    
    # 测试健康端点
    if command -v curl >/dev/null 2>&1; then
        HEALTH_RESPONSE=$(curl -s http://localhost:5007/api/health 2>/dev/null || echo "{}")
        if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
            echo -e "  ✅ 健康检查通过"
        else
            echo -e "  ⚠️ 健康检查失败"
        fi
    fi
else
    echo -e "  ⚠️ Flask服务未运行"
    echo -e "    启动命令: cd /home/kid/fund-daily && python3 web/app.py"
fi

# 生成报告
echo -e "\n${BLUE}📊 CI/CD报告${NC}"
echo -e "  =================================="
echo -e "  ✅ 测试: $(find tests/ -name '*.py' | wc -l)个测试文件"
echo -e "  ✅ 代码覆盖率: 运行 'pytest --cov=src --cov-report=html' 查看详细报告"
echo -e "  ✅ API文档: docs/openapi.json"
echo -e "  ✅ 前端构建: web/dist/"
echo -e "  =================================="

echo -e "\n${GREEN}🎉 CI/CD流程完成！${NC}"
echo -e "运行以下命令启动服务:"
echo -e "  cd /home/kid/fund-daily"
echo -e "  python3 web/app.py"
echo -e "\n访问以下地址:"
echo -e "  🌐 Web界面: http://localhost:5007"
echo -e "  📚 API文档: http://localhost:5007/api/docs"
echo -e "  📊 性能监控: http://localhost:5007/api/metrics/enhanced"