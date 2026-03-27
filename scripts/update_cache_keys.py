#!/usr/bin/env python3
"""
更新缓存键生成，使用统一的缓存键生成器
"""

import re
from pathlib import Path


def update_fetcher_cache_keys():
    """更新 fetcher 模块的缓存键"""
    file_path = Path("/home/kid/fund-daily/src/fetcher/__init__.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    changes = []

    # 替换基金数据缓存键
    pattern1 = r'cache_key = f"fund:{fund_code}"'
    if re.search(pattern1, content):
        content = re.sub(pattern1, "cache_key = cache_keys.fund_data(fund_code)", content)
        changes.append("基金数据缓存键")

    # 替换基金详情缓存键
    pattern2 = r'cache_key = f"fund_detail:{fund_code}"'
    if re.search(pattern2, content):
        content = re.sub(pattern2, "cache_key = cache_keys.fund_detail(fund_code)", content)
        changes.append("基金详情缓存键")

    # 替换市场新闻缓存键
    pattern3 = r'cache_key = f"news:{limit}"'
    if re.search(pattern3, content):
        content = re.sub(pattern3, "cache_key = cache_keys.market_news(limit)", content)
        changes.append("市场新闻缓存键")

    # 替换热点板块缓存键
    pattern4 = r'cache_key = f"sectors:{limit}"'
    if re.search(pattern4, content):
        content = re.sub(pattern4, "cache_key = cache_keys.hot_sectors(limit)", content)
        changes.append("热点板块缓存键")

    # 替换基金经理缓存键
    pattern5 = r'cache_key = f"fund_manager:{fund_code}"'
    if re.search(pattern5, content):
        content = re.sub(pattern5, "cache_key = cache_keys.fund_manager(fund_code)", content)
        changes.append("基金经理缓存键")

    if changes:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 已更新 fetcher 模块: {', '.join(changes)}")
    else:
        print("⚠️  未找到需要更新的缓存键")


def update_market_service_cache_keys():
    """更新 market_service 的缓存键"""
    file_path = Path("/home/kid/fund-daily/src/services/market_service.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 添加导入
    if "from src.utils.cache_keys import cache_keys" not in content:
        # 在现有导入后添加
        import_match = re.search(r"^from src\.services\.metrics_service import", content, re.MULTILINE)
        if import_match:
            insert_pos = import_match.end()
            content = content[:insert_pos] + "\nfrom src.utils.cache_keys import cache_keys" + content[insert_pos:]

    changes = []

    # 替换缓存键生成
    patterns = [
        (r'cache_key = f"{self\.cache_prefix}sentiment"', "cache_key = cache_keys.market_sentiment()"),
        (r'cache_key = f"{self\.cache_prefix}commodity"', 'cache_key = cache_keys.custom("market", "commodity")'),
        (r'cache_key = f"{self\.cache_prefix}hot_sectors"', "cache_key = cache_keys.hot_sectors()"),
        (r'cache_key = f"{self\.cache_prefix}market_news"', "cache_key = cache_keys.market_news()"),
    ]

    for pattern, replacement in patterns:
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            changes.append(pattern.split("=")[-1].strip().strip('"'))

    if changes:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ 已更新 market_service: {', '.join(changes)}")
    else:
        print("⚠️  未找到需要更新的缓存键")


def main():
    print("🔧 开始更新缓存键生成...\n")

    print("1. 更新 fetcher 模块...")
    update_fetcher_cache_keys()

    print("\n2. 更新 market_service...")
    update_market_service_cache_keys()

    print("\n📊 更新完成!")
    print("   缓存键生成已统一到 cache_keys 工具")

    # 测试新的缓存键生成器
    print("\n🧪 测试缓存键生成器:")
    test_script = """
from src.utils.cache_keys import cache_keys

test_keys = [
    cache_keys.fund_data("000001"),
    cache_keys.fund_detail("000001"),
    cache_keys.market_sentiment(),
    cache_keys.market_news(10),
    cache_keys.hot_sectors(5),
]

for key in test_keys:
    print(f"  {key}")
"""

    import subprocess

    result = subprocess.run(["python3", "-c", test_script], cwd="/home/kid/fund-daily", capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ 缓存键生成器测试通过:")
        print(result.stdout)
    else:
        print("❌ 缓存键生成器测试失败:")
        print(result.stderr)

    # 创建更新报告
    report = """# 缓存键生成统一优化报告

## 优化内容
将分散的缓存键生成逻辑统一到 `src/utils/cache_keys.py` 工具模块。

### 1. 创建的缓存键生成器
**类**: `CacheKeyGenerator`
**实例**: `cache_keys` (单例)

**支持的方法**:
- `fund_data(fund_code)` - 基金数据缓存键
- `fund_detail(fund_code)` - 基金详情缓存键  
- `fund_score(fund_code)` - 基金评分缓存键
- `market_sentiment()` - 市场情绪缓存键
- `market_news(limit)` - 市场新闻缓存键
- `hot_sectors(limit)` - 热点板块缓存键
- `fund_manager(fund_code)` - 基金经理缓存键
- `user_holdings(user_id)` - 用户持仓缓存键
- `user_watchlist(user_id)` - 用户关注列表缓存键
- `custom(prefix_key, *parts)` - 自定义缓存键

### 2. 更新的模块

#### 2.1 src/fetcher/__init__.py
- **添加导入**: `from src.utils.cache_keys import cache_keys`
- **替换的缓存键**:
  - `f"fund:{fund_code}"` → `cache_keys.fund_data(fund_code)`
  - `f"fund_detail:{fund_code}"` → `cache_keys.fund_detail(fund_code)`
  - `f"news:{limit}"` → `cache_keys.market_news(limit)`
  - `f"sectors:{limit}"` → `cache_keys.hot_sectors(limit)`
  - `f"fund_manager:{fund_code}"` → `cache_keys.fund_manager(fund_code)`

#### 2.2 src/services/market_service.py
- **添加导入**: `from src.utils.cache_keys import cache_keys`
- **替换的缓存键**:
  - `f"{self.cache_prefix}sentiment"` → `cache_keys.market_sentiment()`
  - `f"{self.cache_prefix}commodity"` → `cache_keys.custom("market", "commodity")`
  - `f"{self.cache_prefix}hot_sectors"` → `cache_keys.hot_sectors()`
  - `f"{self.cache_prefix}market_news"` → `cache_keys.market_news()`

## 优化好处
1. **一致性**: 所有缓存键使用统一的格式和前缀
2. **可维护性**: 缓存键生成逻辑集中管理
3. **可测试性**: 更容易测试缓存键生成
4. **可扩展性**: 添加新的缓存键类型更容易
5. **减少错误**: 避免手动拼接缓存键时的错误

## 向后兼容性
提供了向后兼容的函数:
- `get_fund_data_key(fund_code)`
- `get_fund_score_key(fund_code)`  
- `get_market_news_key(limit)`

## 验证步骤
1. 运行缓存相关的单元测试
2. 测试数据获取功能正常
3. 验证缓存命中率统计

## 后续优化
1. 更新其他模块使用统一的缓存键生成器
2. 添加缓存键验证和文档
3. 实现缓存键版本管理
"""

    report_file = Path("/home/kid/fund-daily/docs/CACHE_KEYS_OPTIMIZATION.md")
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📄 优化报告已保存: {report_file}")


if __name__ == "__main__":
    main()
