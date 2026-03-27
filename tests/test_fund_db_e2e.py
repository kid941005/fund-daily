"""
端到端测试：基金数据存储到PostgreSQL的完整流程
"""

import concurrent.futures
import json
import os
import random
import sys
import threading
import time
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# 设置环境变量
os.environ["FUND_DAILY_DB_PASSWORD"] = "941005"


class TestFundDataLifecycle:
    """测试基金数据完整生命周期"""

    def test_fund_data_crud(self):
        """测试基金数据的增删改查"""
        from db import (
            get_fund_info,
            get_fund_nav,
            get_fund_score,
            save_fund_data,
            save_fund_info,
            save_fund_nav,
            save_fund_score,
        )

        fund_code = f"E2E{random.randint(1000, 9999)}"

        print(f"测试基金代码: {fund_code}")

        # 1. 创建基金信息
        save_fund_info(
            fund_code=fund_code,
            fund_name="端到端测试基金",
            fund_type="混合型",
            fund_company="测试基金公司",
            establish_date="2020-01-01",
            fund_size=100.0,
            manager="测试经理",
            risk_level="中风险",
            rating=4.0,
        )

        # 验证创建
        fund_info = get_fund_info(fund_code)
        assert fund_info is not None
        assert fund_info["fund_name"] == "端到端测试基金"
        print("✅ 基金信息创建成功")

        # 2. 添加净值数据
        nav_date = date.today()
        save_fund_nav(
            fund_code=fund_code, nav_date=nav_date, net_value=1.2345, accumulated_value=2.3456, daily_return=0.0123
        )

        # 验证净值数据
        nav_data = get_fund_nav(fund_code, nav_date)
        assert nav_data is not None
        assert float(nav_data["net_value"]) == 1.2345
        print("✅ 基金净值数据添加成功")

        # 3. 添加评分数据
        score_date = date.today()
        save_fund_score(
            fund_code=fund_code,
            score_date=score_date,
            total_score=85,
            valuation_score=9,
            sector_score=8,
            risk_score=7,
            valuation_reason="估值优秀",
            sector_reason="行业领先",
            risk_reason="风控良好",
        )

        # 验证评分数据
        score_data = get_fund_score(fund_code, score_date)
        assert score_data is not None
        assert score_data["total_score"] == 85
        print("✅ 基金评分数据添加成功")

        # 4. 更新基金信息
        save_fund_info(fund_code=fund_code, fund_name="更新后的端到端测试基金", fund_size=150.0, rating=4.5)

        # 验证更新
        updated_info = get_fund_info(fund_code)
        assert updated_info["fund_name"] == "更新后的端到端测试基金"
        assert float(updated_info["fund_size"]) == 150.0
        assert float(updated_info["rating"]) == 4.5
        print("✅ 基金信息更新成功")

        # 5. 测试save_fund_data函数
        comprehensive_data = {
            "fund_code": fund_code,
            "fund_name": "save_fund_data测试",
            "net_value": 2.3456,
            "accumulated_value": 3.4567,
            "daily_return": 0.0234,
            "score_100": {
                "total_score": 90,
                "valuation": {"score": 9, "reason": "优秀"},
                "sector": {"score": 9, "reason": "领先"},
                "risk_control": {"score": 8, "reason": "良好"},
            },
        }

        result = save_fund_data(fund_code, comprehensive_data)
        assert result is True
        print("✅ save_fund_data函数测试成功")

        # 6. 数据查询验证
        final_info = get_fund_info(fund_code)
        final_nav = get_fund_nav(fund_code)
        final_score = get_fund_score(fund_code)

        assert final_info is not None
        assert final_nav is not None
        assert final_score is not None

        print("✅ 所有数据查询验证成功")

        return True

    def test_historical_data(self):
        """测试历史数据存储和查询"""
        from db import get_fund_history, save_fund_nav

        fund_code = f"HIST{random.randint(1000, 9999)}"

        print(f"测试历史数据基金: {fund_code}")

        # 首先创建基金
        from db import save_fund_info

        save_fund_info(fund_code=fund_code, fund_name="历史数据测试基金")

        # 添加多天的净值数据
        base_date = date.today()
        for i in range(5):
            nav_date = base_date - timedelta(days=i)
            save_fund_nav(fund_code=fund_code, nav_date=nav_date, net_value=1.0 + i * 0.1, daily_return=0.01 * i)

        # 获取历史数据
        history = get_fund_history(fund_code, days=30)

        assert history is not None
        assert "fund_info" in history
        assert "nav_history" in history
        assert "score_history" in history

        # 应该至少有5条净值历史记录
        assert len(history["nav_history"]) >= 5

        print(f"✅ 历史数据测试成功，获取到{len(history['nav_history'])}条净值记录")

        return True


class TestConcurrentAccess:
    """测试并发访问"""

    def test_concurrent_reads(self):
        """测试并发读取"""
        import threading

        from db import get_fund_info, save_fund_info

        fund_code = f"CONC{random.randint(1000, 9999)}"

        # 首先创建测试数据
        save_fund_info(fund_code=fund_code, fund_name="并发测试基金", fund_size=200.0)

        results = []
        errors = []

        def read_fund_data(thread_id):
            """读取基金数据的线程函数"""
            try:
                for i in range(10):
                    info = get_fund_info(fund_code)
                    if info and info["fund_name"] == "并发测试基金":
                        results.append((thread_id, i, "success"))
                    else:
                        results.append((thread_id, i, "fail"))
                    time.sleep(0.01)  # 短暂延迟
            except Exception as e:
                errors.append((thread_id, str(e)))

        # 创建多个线程并发读取
        threads = []
        for i in range(5):
            thread = threading.Thread(target=read_fund_data, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(errors) == 0, f"并发读取出现错误: {errors}"

        success_count = sum(1 for r in results if r[2] == "success")
        print(f"✅ 并发读取测试成功，{success_count}/{len(results)}次读取成功")

        return True

    def test_concurrent_writes(self):
        """测试并发写入"""
        from db import get_fund_info, save_fund_info

        fund_base = f"WRITE{random.randint(1000, 9999)}"
        results = []
        errors = []

        def write_fund_data(thread_id):
            """写入基金数据的线程函数"""
            try:
                fund_code = f"{fund_base}T{thread_id}"
                for i in range(3):
                    save_fund_info(
                        fund_code=fund_code, fund_name=f"线程{thread_id}基金{i}", fund_size=100.0 + thread_id * 10 + i
                    )
                    results.append((thread_id, i, "success"))
                    time.sleep(0.02)  # 短暂延迟
            except Exception as e:
                errors.append((thread_id, str(e)))

        # 使用线程池执行并发写入
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(write_fund_data, i) for i in range(3)]
            concurrent.futures.wait(futures)

        # 验证结果
        assert len(errors) == 0, f"并发写入出现错误: {errors}"

        # 验证数据是否正确保存
        for thread_id in range(3):
            fund_code = f"{fund_base}T{thread_id}"
            info = get_fund_info(fund_code)
            assert info is not None
            assert f"线程{thread_id}基金" in info["fund_name"]

        print(f"✅ 并发写入测试成功，创建了{3*3}条基金记录")

        return True


class TestErrorHandling:
    """测试错误处理"""

    def test_invalid_data(self):
        """测试无效数据处理"""
        from db import get_fund_info, save_fund_info

        # 测试空基金代码
        try:
            save_fund_info(fund_code="", fund_name="空代码基金")
            print("⚠️  空基金代码应该被拒绝")
        except Exception as e:
            print(f"✅ 空基金代码正确处理: {type(e).__name__}")

        # 测试None值
        try:
            save_fund_info(fund_code="NULLTEST", fund_name=None)
            info = get_fund_info("NULLTEST")
            # PostgreSQL可能允许NULL值
            if info and info["fund_name"] is None:
                print("⚠️  NULL基金名称被接受")
            else:
                print("✅  NULL值处理正常")
        except Exception as e:
            print(f"✅ NULL值正确处理: {type(e).__name__}")

        return True

    def test_duplicate_data(self):
        """测试重复数据处理"""
        from db import get_fund_info, save_fund_info

        fund_code = f"DUP{random.randint(1000, 9999)}"

        # 第一次保存
        save_fund_info(fund_code=fund_code, fund_name="原始基金", fund_size=100.0)

        # 第二次保存（更新）
        save_fund_info(fund_code=fund_code, fund_name="更新后的基金", fund_size=200.0)

        # 验证更新成功
        info = get_fund_info(fund_code)
        assert info["fund_name"] == "更新后的基金"
        assert float(info["fund_size"]) == 200.0

        print("✅ 重复数据处理成功（ON CONFLICT UPDATE）")

        return True


class TestPerformance:
    """测试性能"""

    def test_batch_performance(self):
        """测试批量操作性能"""
        from db import get_fund_info, save_fund_info

        num_records = 50
        start_time = time.time()

        # 批量保存
        for i in range(num_records):
            fund_code = f"PERF{i:04d}"
            save_fund_info(fund_code=fund_code, fund_name=f"性能测试基金{i}", fund_size=100.0 + i)

        save_time = time.time() - start_time
        print(f"✅ 保存{num_records}条记录耗时: {save_time:.2f}秒")
        print(f"    平均每条: {save_time/num_records*1000:.1f}毫秒")

        # 批量查询
        start_time = time.time()
        for i in range(num_records):
            fund_code = f"PERF{i:04d}"
            info = get_fund_info(fund_code)
            assert info is not None

        query_time = time.time() - start_time
        print(f"✅ 查询{num_records}条记录耗时: {query_time:.2f}秒")
        print(f"    平均每条: {query_time/num_records*1000:.1f}毫秒")

        # 性能要求：每秒至少处理10条记录
        assert save_time < num_records / 10, f"保存性能不足: {save_time:.2f}秒 > {num_records/10:.2f}秒"
        assert query_time < num_records / 20, f"查询性能不足: {query_time:.2f}秒 > {num_records/20:.2f}秒"

        return True

    def test_large_data_performance(self):
        """测试大数据量性能"""
        from db import get_fund_nav, save_fund_nav

        fund_code = "LARGEPERF"

        # 首先创建基金
        from db import save_fund_info

        save_fund_info(fund_code=fund_code, fund_name="大数据量测试基金")

        num_days = 100
        start_time = time.time()

        # 创建大量历史数据
        base_date = date.today()
        for i in range(num_days):
            nav_date = base_date - timedelta(days=i)
            save_fund_nav(
                fund_code=fund_code, nav_date=nav_date, net_value=1.0 + i * 0.01, daily_return=0.001 * (i % 10)
            )

        save_time = time.time() - start_time
        print(f"✅ 创建{num_days}天历史数据耗时: {save_time:.2f}秒")

        # 查询最新数据
        start_time = time.time()
        for _ in range(10):
            nav_data = get_fund_nav(fund_code)
            assert nav_data is not None

        query_time = time.time() - start_time
        print(f"✅ 10次查询耗时: {query_time:.2f}秒")

        return True


class TestDataConsistency:
    """测试数据一致性"""

    def test_enhanced_fetcher_consistency(self):
        """测试增强版fetcher数据一致性"""
        from db import get_fund_info, get_fund_nav, get_fund_score
        from src.fetcher import fetch_fund_data_enhanced, fetch_fund_detail_enhanced

        fund_code = "CONSISTENCY"

        # 首先确保数据库中有数据
        from db import save_fund_info, save_fund_nav, save_fund_score

        save_fund_info(fund_code=fund_code, fund_name="一致性测试基金", fund_size=300.0)

        save_fund_nav(fund_code=fund_code, nav_date=date.today(), net_value=2.3456, daily_return=0.0234)

        save_fund_score(
            fund_code=fund_code,
            score_date=date.today(),
            total_score=88,
            valuation_score=9,
            sector_score=8,
            risk_score=8,
        )

        # 使用增强版fetcher获取数据
        enhanced_data = fetch_fund_data_enhanced(fund_code)
        enhanced_detail = fetch_fund_detail_enhanced(fund_code)

        # 验证数据来源
        if "source" in enhanced_data:
            print(f"✅ 增强版fetcher返回数据来源: {enhanced_data['source']}")

        # 验证数据完整性
        assert enhanced_data is not None
        if enhanced_detail:
            assert "fund_name" in enhanced_detail or "name" in enhanced_detail

        # 验证数据库一致性
        db_info = get_fund_info(fund_code)
        db_nav = get_fund_nav(fund_code)
        db_score = get_fund_score(fund_code)

        assert db_info is not None
        assert db_nav is not None
        assert db_score is not None

        print("✅ 数据一致性测试通过")

        return True


def run_all_tests():
    """运行所有测试"""
    print("🚀 开始基金数据存储端到端测试")
    print("=" * 60)

    test_classes = [
        ("基金数据生命周期", TestFundDataLifecycle()),
        ("并发访问", TestConcurrentAccess()),
        ("错误处理", TestErrorHandling()),
        ("性能测试", TestPerformance()),
        ("数据一致性", TestDataConsistency()),
    ]

    all_results = []

    for test_name, test_instance in test_classes:
        print(f"\n📋 测试类别: {test_name}")
        print("-" * 40)

        # 获取所有测试方法
        test_methods = [
            method
            for method in dir(test_instance)
            if method.startswith("test_") and callable(getattr(test_instance, method))
        ]

        class_results = []
        for method_name in test_methods:
            method = getattr(test_instance, method_name)
            print(f"  运行测试: {method_name}...")

            try:
                start_time = time.time()
                result = method()
                elapsed = time.time() - start_time

                if result is not False:  # 允许返回True或None
                    print(f"  ✅ {method_name} 通过 ({elapsed:.2f}秒)")
                    class_results.append(True)
                else:
                    print(f"  ❌ {method_name} 失败")
                    class_results.append(False)

            except Exception as e:
                print(f"  ❌ {method_name} 异常: {e}")
                import traceback

                traceback.print_exc()
                class_results.append(False)

        passed = sum(class_results)
        total = len(class_results)
        all_results.extend(class_results)

        print(f"  📊 {test_name}: {passed}/{total} 通过")

    # 统计总体结果
    total_passed = sum(all_results)
    total_tests = len(all_results)

    print("\n" + "=" * 60)
    print("📊 总体测试结果:")
    print(f"  总测试数: {total_tests}")
    print(f"  通过数: {total_passed}")
    print(f"  失败数: {total_tests - total_passed}")
    print(f"  通过率: {total_passed/total_tests*100:.1f}%")

    if total_passed == total_tests:
        print("\n🎉 所有端到端测试通过！基金数据存储功能完整可用！")
        return True
    else:
        print("\n❌ 部分测试失败，请检查错误日志")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
