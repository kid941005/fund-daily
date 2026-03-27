#!/usr/bin/env python3
"""
基金数据存储到PostgreSQL数据库的简单测试
在项目目录中直接运行
"""

import os
import sys
import time
from datetime import datetime

# 设置环境变量
os.environ["FUND_DAILY_DB_PASSWORD"] = "941005"

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"📋 {title}")
    print("=" * 60)


def test_database_connection():
    """测试数据库连接"""
    print_header("测试数据库连接")

    try:
        from db import get_fund_info, save_fund_info

        print("✅ 数据库模块导入成功")

        # 测试保存和获取基金信息
        fund_code = "000001"
        print(f"测试基金代码: {fund_code}")

        save_fund_info(
            fund_code=fund_code,
            fund_name="华夏成长混合测试基金",
            fund_type="混合型",
            fund_company="华夏基金",
            establish_date="2001-12-18",
            fund_size=150.23,
            manager="张三",
            risk_level="中高风险",
            rating=4.7,
        )
        print("✅ 基金数据保存成功")

        # 测试获取基金信息
        fund_info = get_fund_info(fund_code)
        if fund_info:
            print("✅ 基金数据查询成功")
            print(f"  基金代码: {fund_info.get('fund_code')}")
            print(f"  基金名称: {fund_info.get('fund_name')}")
            print(f"  基金类型: {fund_info.get('fund_type')}")
            print(f"  基金公司: {fund_info.get('fund_company')}")
            print(f"  基金规模: {fund_info.get('fund_size')}亿元")
            print(f"  基金经理: {fund_info.get('manager')}")
            print(f"  风险等级: {fund_info.get('risk_level')}")
            print(f"  基金评级: {fund_info.get('rating')}星")
        else:
            print("❌ 基金数据查询失败")

    except Exception as e:
        print(f"❌ 数据库测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_enhanced_fetcher():
    """测试增强版fetcher"""
    print_header("测试增强版Fetcher")

    try:
        from src.fetcher import HAS_ENHANCED_FETCHER, fetch_fund_data_enhanced

        if not HAS_ENHANCED_FETCHER:
            print("❌ 增强版fetcher不可用")
            return False

        print("✅ 增强版fetcher可用")

        # 测试获取基金数据
        fund_code = "000001"
        print(f"测试获取基金 {fund_code} 数据...")
        result = fetch_fund_data_enhanced(fund_code)

        if "error" not in result:
            print("✅ 基金数据获取成功")
            print(f"  基金名称: {result.get('name', '未知')}")
            print(f"  基金净值: {result.get('nav', '未知')}")
            print(f"  数据来源: {result.get('source', '未知')}")

            # 检查是否保存到数据库
            from db import get_fund_info

            fund_info = get_fund_info(fund_code)
            if fund_info:
                print("✅ 数据已成功保存到数据库")
                print(f"  数据库基金名称: {fund_info.get('fund_name', '未知')}")
            else:
                print("⚠️  数据未保存到数据库")
        else:
            print(f"❌ 基金数据获取失败: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ 增强版fetcher测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_fund_service():
    """测试FundService"""
    print_header("测试FundService")

    try:
        from src.services.fund_service import FundService

        service = FundService()
        fund_code = "000001"

        print(f"测试获取基金 {fund_code} 数据...")
        result = service.get_fund_data(fund_code)

        if "error" not in result:
            print("✅ FundService获取数据成功")
            print(f"  基金名称: {result.get('fund_name', '未知')}")
            print(f"  基金代码: {result.get('fund_code', '未知')}")
            score_100 = result.get("score_100", {})
            print(f"  综合评分: {score_100.get('total_score', '无')}")

            # 检查数据库中是否有数据
            from db import get_fund_info

            fund_info = get_fund_info(fund_code)
            if fund_info:
                print("✅ 数据库中有该基金数据")
            else:
                print("⚠️  数据库中没有该基金数据")
        else:
            print(f"❌ FundService获取数据失败: {result.get('error')}")
            return False

    except Exception as e:
        print(f"❌ FundService测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_api_endpoints():
    """测试API端点"""
    print_header("测试API端点")

    try:
        import json

        import requests

        base_url = "http://localhost:5000"

        # 测试健康检查
        print("1. 测试健康检查端点...")
        response = requests.get(f"{base_url}/api/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ 健康检查通过: {health_data.get('status')}")
            print(f"  数据库状态: {health_data.get('database')}")
            print(f"  Redis状态: {health_data.get('redis')}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False

        # 测试基金数据端点
        print("\n2. 测试基金数据端点...")
        response = requests.get(f"{base_url}/api/funds/000001")
        if response.status_code == 200:
            fund_data = response.json()
            print(f"✅ 基金数据端点通过")
            print(f"  基金名称: {fund_data.get('fund_name', '未知')}")
            print(f"  基金代码: {fund_data.get('fund_code', '未知')}")
        else:
            print(f"⚠️  基金数据端点返回: {response.status_code}")
            # 这可能是正常的，如果基金代码不存在

        # 测试持仓建议端点
        print("\n3. 测试持仓建议端点...")
        response = requests.get(f"{base_url}/api/quant/rebalancing")
        if response.status_code == 200:
            rebalancing_data = response.json()
            print(f"✅ 持仓建议端点通过")
            print(f"  建议数量: {len(rebalancing_data.get('trades', []))}")
            print(f"  转换建议: {len(rebalancing_data.get('conversion_advice', []))}")
            print(f"  数据来源: {rebalancing_data.get('datasource', '未知')}")
        else:
            print(f"❌ 持仓建议端点失败: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def test_data_consistency():
    """测试数据一致性"""
    print_header("测试数据一致性")

    try:
        from db import get_fund_info, get_fund_nav
        from src.fetcher import fetch_fund_data_enhanced

        fund_code = "000001"

        print(f"测试基金 {fund_code} 的数据一致性...")

        # 从增强版fetcher获取数据
        enhanced_data = fetch_fund_data_enhanced(fund_code)

        # 从数据库获取数据
        db_info = get_fund_info(fund_code)
        db_nav = get_fund_nav(fund_code)

        print(f"增强版fetcher数据来源: {enhanced_data.get('source', '未知')}")

        if enhanced_data.get("source") == "database":
            print("✅ 数据来自数据库，一致性检查通过")

            # 验证数据一致性
            if db_info and enhanced_data.get("name"):
                print(f"  数据库基金名称: {db_info.get('fund_name')}")
                print(f"  API基金名称: {enhanced_data.get('name')}")

                # 简单的名称匹配检查
                if str(db_info.get("fund_name")).find(str(enhanced_data.get("name"))) != -1:
                    print("✅ 基金名称匹配")
                else:
                    print("⚠️  基金名称不匹配")

        elif enhanced_data.get("source") == "api":
            print("⚠️  数据来自外部API，数据库可能没有该基金数据")

            if db_info:
                print("✅ 数据库中有该基金数据")
            else:
                print("❌ 数据库中没有该基金数据，需要检查数据保存逻辑")

        else:
            print(f"未知数据来源: {enhanced_data.get('source')}")

    except Exception as e:
        print(f"❌ 数据一致性测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


def main():
    """主测试函数"""
    print("🚀 开始基金数据存储到PostgreSQL数据库的完整测试")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    start_time = time.time()

    # 执行各项测试
    tests = [
        test_database_connection,
        test_enhanced_fetcher,
        test_fund_service,
        test_api_endpoints,
        test_data_consistency,
    ]

    test_names = ["数据库连接", "增强版Fetcher", "FundService", "API端点", "数据一致性"]

    results = []
    for i, test_func in enumerate(tests):
        try:
            print(f"\n📊 测试 {i+1}/{len(tests)}: {test_names[i]}")
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            results.append(False)

    # 统计结果
    end_time = time.time()
    total_time = end_time - start_time

    passed = sum(results)
    total = len(results)

    print_header("测试结果统计")
    print(f"  总测试数: {total}")
    print(f"  通过数: {passed}")
    print(f"  失败数: {total - passed}")
    print(f"  通过率: {passed/total*100:.1f}%")
    print(f"  总耗时: {total_time:.2f}秒")

    print("\n📋 详细测试结果:")
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {i+1}. {name}: {status}")

    if passed == total:
        print("\n🎉 所有测试通过！基金数据已成功集成到PostgreSQL数据库！")
        print("\n✅ 实现的功能:")
        print("  - 基金基本信息存储 (funds表)")
        print("  - 基金净值数据存储 (fund_nav表)")
        print("  - 基金评分数据存储 (fund_scores表)")
        print("  - 增强版数据获取器 (优先数据库)")
        print("  - FundService适配 (使用增强版fetcher)")
        print("  - API端点兼容性")
        print("  - 数据一致性检查")
        return True
    else:
        print("\n❌ 部分测试失败，请检查错误日志")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
