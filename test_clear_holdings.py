#!/usr/bin/env python3
"""
测试清仓功能
"""

import json
import os

import requests

# 设置环境变量
os.environ["FUND_DAILY_DB_PASSWORD"] = "941005"


def test_clear_holdings():
    """测试清仓功能"""
    base_url = "http://localhost:5000"

    print("=== 测试清仓功能 ===")

    # 1. 首先登录（使用测试用户）
    print("\n1. 登录测试用户...")
    login_data = {"username": "kid", "password": "kid123"}

    try:
        # 创建会话
        session = requests.Session()

        # 登录
        response = session.post(f"{base_url}/api/login", json=login_data)
        login_result = response.json()

        if login_result.get("success"):
            print(f"✅ 登录成功: {login_result.get('username')}")
        else:
            print(f"❌ 登录失败: {login_result.get('error')}")
            return False

        # 2. 获取当前持仓
        print("\n2. 获取当前持仓...")
        response = session.get(f"{base_url}/api/holdings")
        holdings_result = response.json()

        if holdings_result.get("success"):
            holdings = holdings_result.get("holdings", [])
            print(f"✅ 获取持仓成功，共 {len(holdings)} 条记录")
            if holdings:
                total_amount = sum(h.get("amount", 0) for h in holdings)
                print(f"   总金额: ¥{total_amount:.2f}")
        else:
            print(f"❌ 获取持仓失败: {holdings_result.get('error')}")
            return False

        # 3. 测试清仓API
        print("\n3. 测试清仓API...")
        response = session.post(f"{base_url}/api/holdings/clear")
        clear_result = response.json()

        if clear_result.get("success"):
            print(f"✅ 清仓成功: {clear_result.get('message')}")
        else:
            print(f"❌ 清仓失败: {clear_result.get('error')}")
            return False

        # 4. 验证持仓已清空
        print("\n4. 验证持仓已清空...")
        response = session.get(f"{base_url}/api/holdings")
        holdings_result = response.json()

        if holdings_result.get("success"):
            holdings = holdings_result.get("holdings", [])
            if len(holdings) == 0:
                print("✅ 持仓已成功清空")
            else:
                print(f"❌ 持仓未清空，仍有 {len(holdings)} 条记录")
                return False
        else:
            print(f"❌ 验证持仓失败: {holdings_result.get('error')}")
            return False

        # 5. 测试未登录情况
        print("\n5. 测试未登录情况...")
        new_session = requests.Session()  # 新会话，未登录
        response = new_session.post(f"{base_url}/api/holdings/clear")
        clear_result = response.json()

        if clear_result.get("success") == False and clear_result.get("need_login") == True:
            print("✅ 未登录时清仓被正确拒绝")
        else:
            print(f"❌ 未登录验证失败: {clear_result}")
            return False

        print("\n🎉 所有清仓功能测试通过！")
        return True

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_clear_holdings()
    exit(0 if success else 1)
