"""
钉钉通知模块
"""
import os
import json
import requests
from datetime import datetime


def send_dingtalk_message(webhook_url: str, message: str, msg_type: str = "text") -> bool:
    """
    发送钉钉消息
    
    Args:
        webhook_url: 钉钉机器人Webhook地址
        message: 消息内容
        msg_type: 消息类型 (text/markdown)
    
    Returns:
        bool: 发送是否成功
    """
    if not webhook_url:
        return False
    
    try:
        if msg_type == "markdown":
            # Markdown格式
            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": "基金提醒",
                    "text": message
                }
            }
        else:
            # 文本格式
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
    """
    发送基金涨跌提醒
    
    Args:
        webhook_url: 钉钉Webhook地址
        fund_code: 基金代码
        fund_name: 基金名称
        change_pct: 涨跌幅百分比
        current_nav: 当前净值
    
    Returns:
        bool: 发送是否成功
    """
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
    """
    发送每日基金报告
    
    Args:
        webhook_url: 钉钉Webhook地址
        report_data: 报告数据字典
    
    Returns:
        bool: 发送是否成功
    """
    advice = report_data.get("advice", {})
    holdings = advice.get("holdings", [])
    avg_change = advice.get("avg_change", 0)
    
    # 构建持仓列表
    holdings_text = ""
    for h in holdings[:10]:  # 最多显示10个
        change = h.get("change", 0)
        emoji = "📈" if change > 0 else "📉"
        holdings_text += f"- {h.get('name', '')}: {emoji} {change:+.2f}%\n"
    
    if not holdings_text:
        holdings_text = "暂无持仓数据"
    
    action = advice.get("action", "观望")
    advice_text = advice.get("advice", "暂无建议")
    
    message = f"""### 📊 每日基金报告

**总体情况**:
- 持仓数量: {len(holdings)}
- 平均涨跌: {avg_change:+.2f}%
- 操作建议: **{action}**

**持仓表现**:
{holdings_text}

**建议**: {advice_text}

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return send_dingtalk_message(webhook_url, message, msg_type="markdown")


def send_market_alert(webhook_url: str, sentiment: int, sectors: list) -> bool:
    """
    发送市场情绪提醒
    
    Args:
        webhook_url: 钉钉Webhook地址
        sentiment: 市场情绪得分 (0-100)
        sectors: 热门板块列表
    
    Returns:
        bool: 发送是否成功
    """
    if sentiment >= 70:
        emoji = "🔥"
        status = "市场过热"
    elif sentiment >= 50:
        emoji = "😊"
        status = "市场平稳"
    elif sentiment >= 30:
        emoji = "😐"
        status = "市场观望"
    else:
        emoji = "❄️"
        status = "市场冷淡"
    
    sectors_text = "\n".join([f"- {s.get('name', '')}: {s.get('change', '')}" 
                              for s in sectors[:5]])
    
    message = f"""### {emoji} 市场情绪播报

**市场状态**: {status}
**情绪得分**: {sentiment}/100

**热门板块**:
{sectors_text}

> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    return send_dingtalk_message(webhook_url, message, msg_type="markdown")


def get_webhook() -> str:
    """获取配置的钉钉Webhook地址"""
    return os.environ.get("DINGTALK_WEBHOOK", "")


def is_configured() -> bool:
    """检查是否已配置钉钉通知"""
    return bool(get_webhook())
