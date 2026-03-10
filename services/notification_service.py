"""
通知服务模块
处理钉钉、企业微信等通知
"""
import os
import json
import requests
from datetime import datetime

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

def send_fund_alert(webhook_url: str, fund_code: str, fund_name: str, 
                    change_pct: float, current_nav: float) -> bool:
    """发送基金涨跌提醒"""
    emoji = "📈" if change_pct > 0 else "📉"
    color = "red" if change_pct > 0 else "green"
    
    message = f"""### {emoji} 基金涨跌提醒

- **基金**: {fund_name}
- **代码**: {fund_code}
- **当前净值**: {current_nav}
- **涨跌幅**: <font color=\"{color}\">{change_pct:+.2f}%</font>

> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return send_dingtalk_message(webhook_url, message, msg_type="markdown")

def send_daily_report(webhook_url: str, report_data: dict) -> bool:
    """发送每日报告"""
    advice = report_data.get("advice", {})
    holdings = advice.get("holdings", [])
    avg_change = advice.get("avg_change", 0)
    
    action = advice.get("action", "观望")
    advice_text = advice.get("advice", "暂无建议")
    
    message = f"""### 📊 每日基金报告

**总体情况**:
- 持仓数量: {len(holdings)}
- 平均涨跌: {avg_change:+.2f}%
- 操作建议: **{action}**

**建议**: {advice_text}

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return send_dingtalk_message(webhook_url, message, msg_type="markdown")

def get_webhook() -> str:
    """获取配置的钉钉Webhook地址"""
    return os.environ.get("DINGTALK_WEBHOOK", "")

def is_configured() -> bool:
    """检查是否已配置钉钉通知"""
    return bool(get_webhook())
