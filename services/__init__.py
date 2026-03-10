"""
Services package
业务逻辑服务层
"""
from .data_service import fetch_fund_data_eastmoney, analyze_fund, generate_summary
from .notification_service import send_dingtalk_message, send_fund_alert, send_daily_report

__all__ = [
    'fetch_fund_data_eastmoney',
    'analyze_fund', 
    'generate_summary',
    'send_dingtalk_message',
    'send_fund_alert',
    'send_daily_report',
]
