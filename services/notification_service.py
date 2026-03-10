"""
通知服务模块
处理钉钉、企业微信、Telegram、邮件等通知
支持：定期推送、涨跌幅提醒
"""
import os
import json
import time
import requests
from datetime import datetime
from typing import List, Dict, Optional

# ============== 发送渠道 ==============

def send_dingtalk_message(webhook_url: str, message: str, msg_type: str = "text") -> bool:
    """发送钉钉消息"""
    if not webhook_url:
        return False
    
    try:
        if msg_type == "markdown":
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "基金提醒",
                    "text": message
                }
            }
        else:
            data = {
                "msgtype": "text",
                "text": {
                    "content": f"[基金提醒] {message}"
                }
            }
        
        response = requests.post(
            webhook_url, 
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        return response.json().get("errcode", 1) == 0
    
    except Exception as e:
        print(f"钉钉通知失败: {e}")
        return False


def send_telegram_message(token: str, chat_id: str, message: str, parse_mode: str = "Markdown") -> bool:
    """发送Telegram消息"""
    if not token or not chat_id:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": parse_mode
        }
        response = requests.post(url, json=data, timeout=10)
        return response.json().get("ok", False)
    except Exception as e:
        print(f"Telegram通知失败: {e}")
        return False


def send_email(smtp_server: str, smtp_port: int, username: str, password: str,
              to_addr: str, subject: str, body: str) -> bool:
    """发送邮件"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg["From"] = username
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html", "utf-8"))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False


# ============== 统一发送接口 ==============

def send_message(message: str, msg_type: str = "text", title: str = "基金提醒") -> bool:
    """统一发送接口，支持多种渠道"""
    success = False
    
    # 1. 钉钉
    dingtalk_webhook = os.environ.get("DINGTALK_WEBHOOK", "")
    if dingtalk_webhook:
        if send_dingtalk_message(dingtalk_webhook, message, msg_type):
            success = True
    
    # 2. Telegram
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    tg_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if tg_token and tg_chat_id:
        if send_telegram_message(tg_token, tg_chat_id, message):
            success = True
    
    # 3. 邮件
    smtp_server = os.environ.get("SMTP_SERVER", "")
    if smtp_server:
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USERNAME", "")
        smtp_pass = os.environ.get("SMTP_PASSWORD", "")
        mail_to = os.environ.get("MAIL_TO", "")
        if smtp_user and smtp_pass and mail_to:
            if send_email(smtp_server, smtp_port, smtp_user, smtp_pass, mail_to, title, message):
                success = True
    
    return success


# ============== 基金提醒功能 ==============

def send_fund_alert(fund_code: str, fund_name: str, 
                    change_pct: float, current_nav: float, threshold: float = 3.0) -> bool:
    """发送基金涨跌提醒"""
    emoji = "📈" if change_pct > 0 else "📉"
    color = "red" if change_pct > 0 else "green"
    direction = "暴涨" if change_pct > threshold else "大跌" if change_pct < -threshold else "波动"
    
    message = f"""### {emoji} 基金{direction}提醒

- **基金**: {fund_name}
- **代码**: {fund_code}
- **当前净值**: {current_nav}
- **涨跌幅**: <font color="{color}">{change_pct:+.2f}%</font>
- **阈值**: ±{threshold}%

> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return send_message(message, msg_type="markdown", title=f"基金提醒 - {direction}")


def send_daily_report(report_data: dict) -> bool:
    """发送每日报告"""
    advice = report_data.get("advice", {})
    funds = report_data.get("funds", [])
    summary = report_data.get("summary", {})
    
    action = advice.get("action", "观望")
    advice_text = advice.get("advice", "暂无建议")
    market_sentiment = advice.get("market_sentiment", "平稳")
    commodity_desc = advice.get("commodity_desc", "暂无")
    
    # 基金列表
    fund_list = []
    for f in funds[:10]:
        change = f.get("daily_change", 0)
        emoji = "📈" if change > 0 else "📉" if change < 0 else "➖"
        fund_list.append(f"- {emoji} {f.get('fund_name', '')}: {change:+.2f}%")
    
    funds_text = "\n".join(fund_list) if fund_list else "暂无数据"
    
    message = f"""### 📊 每日基金报告

**市场情况**:
- 大盘情绪: {market_sentiment}
- 大宗商品: {commodity_desc}

**基金表现**:
{funds_text}

**操作建议**: **{action}** - {advice_text}

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return send_message(message, msg_type="markdown", title="每日基金报告")


# ============== 涨跌幅监控 ==============

class FundAlertMonitor:
    """基金涨跌幅监控器"""
    
    def __init__(self, threshold: float = 3.0, cooldown: int = 3600):
        """
        Args:
            threshold: 涨跌幅阈值，超过时触发提醒 (default: 3.0%)
            cooldown: 同一基金提醒冷却时间秒数 (default: 1小时)
        """
        self.threshold = threshold
        self.cooldown = cooldown
        self.last_alert: Dict[str, float] = {}  # {fund_code: timestamp}
    
    def check_and_alert(self, fund_code: str, fund_name: str, 
                       change_pct: float, current_nav: float) -> Optional[bool]:
        """检查是否需要提醒，返回True/False/None"""
        abs_change = abs(change_pct)
        
        # 检查是否超过阈值
        if abs_change < self.threshold:
            return None
        
        # 检查冷却时间
        now = time.time()
        last_time = self.last_alert.get(fund_code, 0)
        if now - last_time < self.cooldown:
            return False  # 冷却中
        
        # 发送提醒
        self.last_alert[fund_code] = now
        return send_fund_alert(fund_code, fund_name, change_pct, current_nav, self.threshold)
    
    def clear_old_records(self, max_age: int = 86400):
        """清理超过24小时的记录"""
        now = time.time()
        self.last_alert = {
            k: v for k, v in self.last_alert.items() 
            if now - v < max_age
        }


# ============== 定时推送 ==============

def run_scheduled_monitor(fund_codes: List[str], check_interval: int = 300):
    """
    运行定时监控循环
    
    Args:
        fund_codes: 基金代码列表
        check_interval: 检查间隔秒数 (default: 5分钟)
    """
    monitor = FundAlertMonitor(
        threshold=float(os.environ.get("ALERT_THRESHOLD", "3.0")),
        cooldown=int(os.environ.get("ALERT_COOLDOWN", "3600"))
    )
    
    # 导入fund-daily的数据获取函数
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from fund_daily import fetch_fund_data_eastmoney, analyze_fund
    
    print(f"开始监控 {len(fund_codes)} 个基金，阈值: {monitor.threshold}%")
    
    while True:
        try:
            for code in fund_codes:
                data = fetch_fund_data_eastmoney(code.strip())
                analysis = analyze_fund(data)
                
                if "error" not in analysis:
                    change = analysis.get("daily_change", 0)
                    nav = analysis.get("nav", "N/A")
                    name = analysis.get("fund_name", code)
                    
                    result = monitor.check_and_alert(code, name, change, nav)
                    if result:
                        print(f"已发送 {code} 涨跌幅提醒: {change:+.2f}%")
            
            # 清理旧记录
            monitor.clear_old_records()
            
        except Exception as e:
            print(f"监控出错: {e}")
        
        time.sleep(check_interval)


# ============== 配置检查 ==============

def get_webhook() -> str:
    """获取配置的钉钉Webhook地址"""
    return os.environ.get("DINGTALK_WEBHOOK", "")

def is_configured() -> bool:
    """检查是否已配置任意通知渠道"""
    return bool(
        get_webhook() or 
        os.environ.get("TELEGRAM_BOT_TOKEN") or
        os.environ.get("SMTP_SERVER")
    )
