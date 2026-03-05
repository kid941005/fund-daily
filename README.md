# Fund Daily - 每日基金分析工具

🚀 自动获取基金数据，分析趋势，生成每日报告

## ✨ 功能特点

- 📊 **实时数据** - 获取基金净值、涨跌幅
- 📈 **趋势分析** - 自动判断涨跌趋势
- 📋 **每日报告** - 生成多基金对比报告
- 💬 **分享格式** - 一键生成适合分享的文字
- 🌐 **Web UI** - 可视化界面查看基金数据
- 🐳 **Docker 支持** - 一键部署

## 🚀 快速开始

### 方式 1: 直接运行

```bash
# 克隆仓库
git clone https://github.com/kid941005/fund-daily.git
cd fund-daily

# 安装依赖
pip3 install -r requirements.txt

# 运行
python3 scripts/fund-daily.py share 000001,110022
```

### 方式 2: Docker 部署

```bash
# 构建镜像
docker build -t fund-daily .

# 运行
docker run --rm fund-daily share 000001,110022
```

### 方式 3: Web UI

```bash
# 安装依赖
pip3 install -r requirements.txt

# 启动 Web 服务
python3 web/app.py

# 访问 http://localhost:5000
```

## 📖 使用说明

### 命令行工具

```bash
# 获取单只基金数据
python3 scripts/fund-daily.py fetch 000001

# 分析单只基金
python3 scripts/fund-daily.py analyze 000001

# 生成每日报告
python3 scripts/fund-daily.py report 000001,000002,000003

# 生成分享文本
python3 scripts/fund-daily.py share 000001,000002,000003
```

### Web 界面

启动后访问 http://localhost:5000，可以：
- 查看实时基金数据
- 添加/删除关注的基金
- 查看市场概览

## 🐳 Docker Compose

```bash
# 启动所有服务
docker-compose up -d

# 服务列表
- fund-daily-web: http://localhost:5000 (Web UI)
- fund-daily-cron: 定时推送服务
```

## 📋 常用基金代码

| 代码 | 名称 |
|:---|:---|
| 000001 | 华夏成长混合 |
| 110022 | 易方达消费行业 |
| 161725 | 招商白酒 |
| 002190 | 农银新能源 |
| 005911 | 广发双擎升级 |

## 🔧 配置

编辑 `config/config.json`：

```json
{
  "default_funds": ["000001", "110022", "161725"],
  "report_time": "15:00"
}
```

## 📄 项目结构

```
fund-daily/
├── scripts/          # 核心脚本
│   └── fund-daily.py # 主程序
├── web/              # Web UI
│   ├── app.py        # Flask 应用
│   └── templates/    # HTML 模板
├── config/           # 配置文件
├── Dockerfile        # CLI 版本
├── Dockerfile.web    # Web 版本
└── docker-compose.yml
```

## ⚠️ 免责声明

- 数据来源：东方财富公开 API
- 仅供参考，不构成投资建议
- 基金投资有风险，入市需谨慎

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 🙏 致谢

- 数据来源：[东方财富](https://fund.eastmoney.com/)
- 参考项目：[daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis)
