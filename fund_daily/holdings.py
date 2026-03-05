#!/usr/bin/env python3
"""
Fund Holdings Management - 持仓管理
记录和管理用户的基金持仓
"""

import json
import os
from datetime import datetime
from pathlib import Path


class HoldingsManager:
    """基金持仓管理器"""
    
    def __init__(self, config_path="config/holdings.json"):
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_config()
    
    def _ensure_config(self):
        """确保配置文件存在"""
        if not self.config_path.exists():
            self._save({
                "holdings": [],
                "last_updated": datetime.now().isoformat()
            })
    
    def _load(self):
        """加载配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save(self, data):
        """保存配置"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_holding(self, fund_code, fund_name, shares, cost_price, buy_date=None):
        """添加持仓"""
        data = self._load()
        
        # 检查是否已存在
        for h in data['holdings']:
            if h['fund_code'] == fund_code:
                return {"error": f"基金 {fund_code} 已存在，请使用 update 命令更新"}
        
        # 添加新持仓
        holding = {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "shares": float(shares),
            "cost_price": float(cost_price),
            "buy_date": buy_date or datetime.now().strftime("%Y-%m-%d"),
            "added_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        data['holdings'].append(holding)
        data['last_updated'] = datetime.now().isoformat()
        self._save(data)
        
        return {"success": True, "message": f"已添加 {fund_name} ({fund_code})"}
    
    def update_holding(self, fund_code, shares=None, cost_price=None):
        """更新持仓"""
        data = self._load()
        
        for h in data['holdings']:
            if h['fund_code'] == fund_code:
                if shares is not None:
                    h['shares'] = float(shares)
                if cost_price is not None:
                    h['cost_price'] = float(cost_price)
                
                data['last_updated'] = datetime.now().isoformat()
                self._save(data)
                return {"success": True, "message": f"已更新 {fund_code}"}
        
        return {"error": f"基金 {fund_code} 不存在"}
    
    def remove_holding(self, fund_code):
        """删除持仓"""
        data = self._load()
        
        original_count = len(data['holdings'])
        data['holdings'] = [h for h in data['holdings'] if h['fund_code'] != fund_code]
        
        if len(data['holdings']) < original_count:
            data['last_updated'] = datetime.now().isoformat()
            self._save(data)
            return {"success": True, "message": f"已删除 {fund_code}"}
        
        return {"error": f"基金 {fund_code} 不存在"}
    
    def list_holdings(self):
        """列出所有持仓"""
        data = self._load()
        return {
            "total": len(data['holdings']),
            "holdings": data['holdings'],
            "last_updated": data['last_updated']
        }
    
    def get_holding(self, fund_code):
        """获取单个持仓"""
        data = self._load()
        
        for h in data['holdings']:
            if h['fund_code'] == fund_code:
                return h
        
        return None
    
    def get_total_cost(self):
        """获取总成本"""
        data = self._load()
        total = sum(h['shares'] * h['cost_price'] for h in data['holdings'])
        return total


# 便捷函数
def get_holdings_manager():
    """获取持仓管理器实例"""
    return HoldingsManager()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("""Usage: holdings <command> [options]

Commands:
  add <code> <name> <shares> <cost>     添加持仓
  update <code> [shares] [cost]         更新持仓
  remove <code>                          删除持仓
  list                                    列出所有持仓
  get <code>                              获取单个持仓
  total                                   获取总成本

Examples:
  holdings add 000001 "华夏成长" 1000 1.05
  holdings update 000001 1500 1.10
  holdings remove 000001
  holdings list
  holdings total
""", file=sys.stderr)
        sys.exit(1)
    
    manager = get_holdings_manager()
    command = sys.argv[1]
    
    if command == "add" and len(sys.argv) >= 6:
        result = manager.add_holding(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "update" and len(sys.argv) >= 3:
        shares = sys.argv[3] if len(sys.argv) > 3 else None
        cost = sys.argv[4] if len(sys.argv) > 4 else None
        result = manager.update_holding(sys.argv[2], shares, cost)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "remove" and len(sys.argv) >= 3:
        result = manager.remove_holding(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "list":
        result = manager.list_holdings()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    elif command == "get" and len(sys.argv) >= 3:
        result = manager.get_holding(sys.argv[2])
        print(json.dumps(result, ensure_ascii=False, indent=2) if result else '{"error": "Not found"}')
        
    elif command == "total":
        print(f"总成本: ¥{manager.get_total_cost():,.2f}")
        
    else:
        print("Error: Invalid command", file=sys.stderr)
        sys.exit(1)
