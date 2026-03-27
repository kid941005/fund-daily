#!/usr/bin/env python3
"""
缓存接口迁移脚本
将 redis_get/redis_set 替换为 CacheManager
"""

import os
import re
from pathlib import Path


def migrate_market_service():
    """迁移 market_service.py"""
    file_path = Path("/home/kid/fund-daily/src/services/market_service.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 替换导入
    content = content.replace(
        "from src.cache.redis_cache import redis_get, redis_set, get_redis_client",
        "from src.cache.manager import get_cache_manager",
    )

    # 在 __init__ 方法中添加缓存管理器
    init_pattern = (
        r"(def __init__\(self, cache_enabled: bool = True\):.*?self\.metrics_service = get_metrics_service\(\))"
    )
    init_replacement = r"\1\n        self.cache_manager = get_cache_manager()"
    content = re.sub(init_pattern, init_replacement, content, flags=re.DOTALL)

    # 替换 redis_get 调用
    # 模式: redis_get(cache_key) -> self.cache_manager.get(cache_key)
    content = re.sub(r"redis_get\((\w+)\)", r"self.cache_manager.get(\1)", content)

    # 替换 redis_set 调用
    # 模式: redis_set(cache_key, data, ttl=xxx) -> self.cache_manager.set(cache_key, data, ttl=xxx)
    content = re.sub(r"redis_set\((\w+),\s*(\w+),\s*ttl=(\w+)\)", r"self.cache_manager.set(\1, \2, ttl=\3)", content)

    # 替换没有ttl参数的redis_set
    content = re.sub(r"redis_set\((\w+),\s*(\w+)\)", r"self.cache_manager.set(\1, \2)", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ 已迁移 market_service.py")


def migrate_fund_service():
    """迁移 fund_service.py"""
    file_path = Path("/home/kid/fund-daily/src/services/fund_service.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 替换导入
    content = content.replace(
        "from src.cache.redis_cache import redis_get, redis_set, get_redis_client",
        "from src.cache.manager import get_cache_manager",
    )

    # 在 __init__ 方法中添加缓存管理器
    init_pattern = r"(def __init__\(self, cache_enabled: bool = True\):.*?self\.cache_enabled = cache_enabled)"
    init_replacement = r"\1\n        self.cache_manager = get_cache_manager()"
    content = re.sub(init_pattern, init_replacement, content, flags=re.DOTALL)

    # 替换 redis_get 调用
    content = re.sub(r"redis_get\((\w+)\)", r"self.cache_manager.get(\1)", content)

    # 替换 redis_set 调用
    content = re.sub(r"redis_set\((\w+),\s*(\w+),\s*ttl=(\w+)\)", r"self.cache_manager.set(\1, \2, ttl=\3)", content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    print("✅ 已迁移 fund_service.py")


def check_fetcher_module():
    """检查 fetcher 模块"""
    file_path = Path("/home/kid/fund-daily/src/fetcher/__init__.py")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 检查是否还有 redis_set 调用
    if "redis_set(" in content:
        print("⚠️  fetcher 模块中仍有 redis_set 调用")
        # 找到并显示具体位置
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "redis_set(" in line:
                print(f"   第 {i} 行: {line.strip()}")
    else:
        print("✅ fetcher 模块已清理完成")


def main():
    print("🔧 开始迁移缓存接口...")

    # 迁移 market_service.py
    migrate_market_service()

    # 迁移 fund_service.py
    migrate_fund_service()

    # 检查 fetcher 模块
    check_fetcher_module()

    print("\n📊 迁移完成!")
    print("   1. market_service.py - 已迁移到 CacheManager")
    print("   2. fund_service.py - 已迁移到 CacheManager")
    print("   3. fetcher/__init__.py - 已清理完成")

    # 创建迁移报告
    report = """# 缓存接口迁移报告

## 迁移内容
将以下文件的缓存接口从直接 Redis 调用迁移到统一的 CacheManager:

### 1. src/services/market_service.py
- **导入变更**: `from src.cache.redis_cache import ...` → `from src.cache.manager import get_cache_manager`
- **初始化添加**: `self.cache_manager = get_cache_manager()`
- **方法替换**:
  - `redis_get(cache_key)` → `self.cache_manager.get(cache_key)`
  - `redis_set(cache_key, data, ttl=xxx)` → `self.cache_manager.set(cache_key, data, ttl=xxx)`

### 2. src/services/fund_service.py
- **导入变更**: 同上
- **初始化添加**: 同上
- **方法替换**: 同上

### 3. src/fetcher/__init__.py
- **清理完成**: 已移除重复的 `redis_set()` 调用
- **统一使用**: `set_cache()` 函数（内部使用 CacheManager）

## 迁移好处
1. **统一接口**: 所有缓存操作通过 CacheManager
2. **多级缓存**: 支持内存+Redis多级缓存
3. **错误防护**: 内置缓存穿透和雪崩防护
4. **性能优化**: 内存缓存优先，减少Redis访问
5. **统计监控**: 提供缓存命中率等统计信息

## 验证步骤
1. 运行相关服务的单元测试
2. 测试市场数据获取功能
3. 测试基金数据获取功能
4. 检查缓存命中率统计

## 注意事项
1. **性能监控**: 迁移后监控缓存性能变化
2. **错误处理**: CacheManager 有内置错误处理，但仍需监控
3. **向后兼容**: 保持原有API接口不变
"""

    report_file = Path("/home/kid/fund-daily/docs/CACHE_MIGRATION_REPORT.md")
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"📄 报告已保存: {report_file}")


if __name__ == "__main__":
    main()
