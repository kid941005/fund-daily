#!/usr/bin/env python3
"""
Fund Data Storage - Persistent storage for fund data
Supports JSON and CSV formats
"""

import json
import csv
import os
from datetime import datetime
from pathlib import Path

class FundStorage:
    """基金数据持久化存储"""
    
    def __init__(self, data_dir="data/db"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 子目录
        self.json_dir = self.data_dir / "json"
        self.csv_dir = self.data_dir / "csv"
        self.json_dir.mkdir(exist_ok=True)
        self.csv_dir.mkdir(exist_ok=True)
    
    def save_fund_data(self, fund_code, fund_data):
        """
        保存基金数据
        
        Args:
            fund_code: 基金代码
            fund_data: 基金数据字典
        """
        # 添加时间戳
        record = {
            "timestamp": datetime.now().isoformat(),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "fund_code": fund_code,
            "data": fund_data
        }
        
        # JSON 格式保存（便于查询）
        self._save_json(fund_code, record)
        
        # CSV 格式保存（便于分析）
        self._save_csv(fund_code, record)
        
        return True
    
    def _save_json(self, fund_code, record):
        """保存为 JSON 格式"""
        filepath = self.json_dir / f"{fund_code}.json"
        
        # 读取现有数据
        history = []
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                history = json.load(f)
        
        # 检查是否已存在今天的数据
        today = datetime.now().strftime("%Y-%m-%d")
        history = [h for h in history if h.get('date') != today]
        
        # 添加新记录
        history.append(record)
        
        # 保存（保留最近 365 天）
        history = history[-365:]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def _save_csv(self, fund_code, record):
        """保存为 CSV 格式"""
        filepath = self.csv_dir / f"{fund_code}.csv"
        
        # 提取关键字段
        data = record.get('data', {})
        row = {
            'date': record['date'],
            'fund_code': fund_code,
            'fund_name': data.get('name', ''),
            'nav': data.get('dwjz', ''),
            'estimate_nav': data.get('gsz', ''),
            'daily_change': data.get('gszzl', ''),
            'estimate_time': data.get('gztime', '')
        }
        
        # 写入 CSV
        file_exists = filepath.exists()
        with open(filepath, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=row.keys())
            if not file_exists:
                writer.writeheader()
            writer.writerow(row)
    
    def get_fund_history(self, fund_code, days=30):
        """
        获取基金历史数据
        
        Args:
            fund_code: 基金代码
            days: 获取最近多少天的数据
            
        Returns:
            list: 历史数据列表
        """
        filepath = self.json_dir / f"{fund_code}.json"
        
        if not filepath.exists():
            return []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            history = json.load(f)
        
        # 返回最近 N 天
        return history[-days:] if len(history) > days else history
    
    def get_all_funds(self):
        """获取所有已记录的基金"""
        funds = []
        for json_file in self.json_dir.glob("*.json"):
            fund_code = json_file.stem
            history = self.get_fund_history(fund_code, days=1)
            if history:
                latest = history[-1]
                funds.append({
                    "fund_code": fund_code,
                    "fund_name": latest.get('data', {}).get('name', 'Unknown'),
                    "last_update": latest.get('date'),
                    "records_count": len(self.get_fund_history(fund_code, days=365))
                })
        return funds
    
    def get_date_range(self, fund_code):
        """获取基金数据的日期范围"""
        history = self.get_fund_history(fund_code, days=365)
        if not history:
            return None, None
        
        dates = [h.get('date') for h in history if h.get('date')]
        return min(dates), max(dates) if dates else (None, None)
    
    def export_to_csv(self, fund_code, output_path=None):
        """导出基金数据到 CSV"""
        history = self.get_fund_history(fund_code, days=365)
        
        if not history:
            return False
        
        if output_path is None:
            output_path = f"{fund_code}_export.csv"
        
        # 准备数据
        rows = []
        for record in history:
            data = record.get('data', {})
            rows.append({
                'date': record.get('date'),
                'fund_code': fund_code,
                'fund_name': data.get('name', ''),
                'nav': data.get('dwjz', ''),
                'estimate_nav': data.get('gsz', ''),
                'daily_change': data.get('gszzl', '')
            })
        
        # 写入文件
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        
        return True
    
    def get_statistics(self, fund_code, days=30):
        """获取基金统计信息"""
        history = self.get_fund_history(fund_code, days)
        
        if not history:
            return None
        
        # 提取涨跌幅
        changes = []
        for h in history:
            try:
                change = float(h.get('data', {}).get('gszzl', 0))
                changes.append(change)
            except:
                continue
        
        if not changes:
            return None
        
        return {
            "fund_code": fund_code,
            "days": len(changes),
            "avg_change": round(sum(changes) / len(changes), 2),
            "max_change": round(max(changes), 2),
            "min_change": round(min(changes), 2),
            "positive_days": sum(1 for c in changes if c > 0),
            "negative_days": sum(1 for c in changes if c < 0),
            "total_change": round(sum(changes), 2)
        }


# 便捷函数
def get_storage():
    """获取存储实例"""
    return FundStorage()


if __name__ == '__main__':
    # 测试
    storage = FundStorage()
    
    # 测试数据
    test_data = {
        "fundcode": "000001",
        "name": "华夏成长混合",
        "dwjz": "1.0920",
        "gsz": "1.1101",
        "gszzl": "1.66"
    }
    
    # 保存
    storage.save_fund_data("000001", test_data)
    
    # 读取
    history = storage.get_fund_history("000001", days=7)
    print(f"历史记录数: {len(history)}")
    
    # 统计
    stats = storage.get_statistics("000001", days=30)
    print(f"统计: {stats}")
