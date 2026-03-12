# Fund Daily

每日基金分析工具 - 重构版本

## ✨ 新特性

- 模块化架构 - 代码更易维护
- 完整的单元测试 - 38+ 测试用例
- GitHub Actions CI/CD - 自动化测试

## 📁 项目结构

```
fund-daily/
├── src/                      # 核心业务模块
│   ├── fetcher/             # 数据获取 (API + 缓存)
│   ├── analyzer/            # 风险/情绪分析
│   ├── advice/              # 投资建议生成
│   └── models/              # 数据模型
├── web/
│   ├── app.py              # Flask 主应用
│   ├── api/routes.py       # HTTP 接口
│   └── services/            # 业务逻辑层
├── tests/                   # 单元测试
│   ├── test_fetcher.py
│   ├── test_analyzer.py
│   ├── test_advice.py
│   └── test_services.py
└── scripts/
    └── fund-daily-cli.py   # CLI 工具
```

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

### 运行测试

```bash
pytest tests/ -v
```

### 运行 Web 服务

```bash
python web/app.py
```

### 使用 CLI

```bash
# 获取基金数据
python scripts/fund-daily-cli.py fetch 000001

# 分析基金
python scripts/fund-daily-cli.py analyze 000001

# 生成报告
python scripts/fund-daily-cli.py report 000001,110022
```

## 🧪 测试覆盖

| 模块 | 测试数 |
|------|--------|
| fetcher | 9 |
| analyzer | 13 |
| advice | 16 |
| services | 14 |
| **总计** | **52** |

## 🛠️ 技术栈

- **后端**: Flask + SQLite
- **测试**: pytest + pytest-cov
- **CI/CD**: GitHub Actions

## 📄 许可证

MIT License
