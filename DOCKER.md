# Fund Daily - Docker 部署指南

## 快速开始

### 1. 构建镜像

```bash
cd ~/.openclaw/workspace/skills/fund-daily
docker build -t fund-daily:latest .
```

### 2. 运行单次报告

```bash
docker run --rm fund-daily:latest share 000001,110022
```

### 3. 使用 Docker Compose

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑 .env 文件，配置你的基金代码和 Telegram
nano .env

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

## 配置说明

### 环境变量 (.env)

```bash
# Telegram 推送（可选）
TELEGRAM_BOT_TOKEN=你的机器人Token
TELEGRAM_CHAT_ID=你的聊天ID

# 默认基金代码
FUND_CODES=000001,110022,161725

# 报告时间
REPORT_TIME=15:00
```

### 获取 Telegram Chat ID

1. 创建 Bot: @BotFather
2. 发送消息给 Bot
3. 访问: `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. 找到 `chat.id`

## 使用方式

### 方式 1: 单次运行

```bash
docker run --rm fund-daily:latest share 000001,110022,161725
```

### 方式 2: 定时任务

```bash
# 启动定时服务
docker-compose up -d fund-daily-cron

# 查看定时任务日志
docker-compose logs -f fund-daily-cron
```

### 方式 3: 系统 Cron + Docker

编辑系统 crontab:
```bash
crontab -e
```

添加:
```
0 15 * * * docker run --rm fund-daily:latest share 000001,110022,161725 >> /var/log/fund-daily.log 2>&1
```

## 数据持久化

数据保存在 `./data` 目录:
- 每日报告: `fund_report_YYYYMMDD.txt`
- 历史数据: `fund_history.json`

## 常用命令

```bash
# 构建
docker build -t fund-daily:latest .

# 运行
docker run --rm fund-daily:latest fetch 000001
docker run --rm fund-daily:latest analyze 000001
docker run --rm fund-daily:latest share 000001,110022

# 查看帮助
docker run --rm fund-daily:latest --help

# 停止服务
docker-compose down

# 重启服务
docker-compose restart
```

## 自动化推送示例

### 推送到 Telegram

```bash
# 在 .env 中配置后启动
docker-compose up -d fund-daily-cron
```

### 推送到微信（通过企业微信 Bot）

创建 `wechat-push.sh`:
```bash
#!/bin/bash
KEY="你的企业微信KEY"
REPORT=$(docker run --rm fund-daily:latest share 000001,110022)

curl "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=$KEY" \
  -H "Content-Type: application/json" \
  -d "{\"msgtype\": \"text\", \"text\": {\"content\": \"$REPORT\"}}"
```

添加到 crontab:
```
0 15 * * * /path/to/wechat-push.sh
```

## 故障排查

```bash
# 查看容器日志
docker logs fund-daily

# 进入容器调试
docker run -it --rm fund-daily:latest bash

# 测试 API
docker run --rm fund-daily:latest fetch 000001
```
