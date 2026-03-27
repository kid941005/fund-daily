#!/usr/bin/env python3
"""
分析配置使用情况，查找直接 os.getenv() 调用
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set


def analyze_file(file_path: Path) -> Dict:
    """分析单个文件的配置使用情况"""
    results = {
        "file": str(file_path),
        "os_getenv_calls": [],
        "os_environ_access": [],
        "config_imports": [],
        "get_config_calls": [],
    }

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找 os.getenv() 调用
        getenv_pattern = r"os\.getenv\(([^)]+)\)"
        for match in re.finditer(getenv_pattern, content):
            args = match.group(1)
            # 提取参数
            params = re.split(r",\s*", args)
            env_var = params[0].strip("'\"")
            default_value = params[1] if len(params) > 1 else None

            results["os_getenv_calls"].append(
                {
                    "line": content[: match.start()].count("\n") + 1,
                    "env_var": env_var,
                    "default": default_value,
                    "full_match": match.group(0),
                }
            )

        # 查找 os.environ 访问
        environ_pattern = r"os\.environ\[([^\]]+)\]"
        for match in re.finditer(environ_pattern, content):
            key = match.group(1).strip("'\"")
            results["os_environ_access"].append(
                {"line": content[: match.start()].count("\n") + 1, "key": key, "full_match": match.group(0)}
            )

        # 查找配置导入
        if "from src.config import" in content or "import src.config" in content:
            config_import_match = re.search(r"(from src.config import|import src.config)", content)
            if config_import_match:
                results["config_imports"].append(config_import_match.group(0))

        # 查找 get_config() 调用
        get_config_pattern = r"get_config\(\)"
        get_config_matches = list(re.finditer(get_config_pattern, content))
        results["get_config_calls_count"] = len(get_config_matches)

        return results

    except Exception as e:
        print(f"分析文件 {file_path} 时出错: {e}")
        return results


def main():
    project_root = Path("/home/kid/fund-daily")

    # 需要分析的文件
    files_to_analyze = [
        project_root / "src" / "jwt_auth.py",
        project_root / "src" / "api_gateway" / "core.py",
        project_root / "web" / "api" / "rate_limiter.py",
        project_root / "db" / "pool.py",
        project_root / "db" / "dingtalk.py",
    ]

    print("🔍 分析配置使用情况...\n")

    all_results = []
    total_getenv_calls = 0
    total_environ_access = 0

    for file_path in files_to_analyze:
        if file_path.exists():
            results = analyze_file(file_path)
            all_results.append(results)

            getenv_count = len(results["os_getenv_calls"])
            environ_count = len(results["os_environ_access"])
            total_getenv_calls += getenv_count
            total_environ_access += environ_count

            if getenv_count > 0 or environ_count > 0:
                print(f"📄 {file_path.relative_to(project_root)}")
                print(f"   os.getenv() 调用: {getenv_count}")
                print(f"   os.environ 访问: {environ_count}")
                print(f"   get_config() 调用: {results.get('get_config_calls_count', 0)}")

                if getenv_count > 0:
                    print("   具体调用:")
                    for call in results["os_getenv_calls"][:3]:  # 只显示前3个
                        print(f"     第{call['line']}行: {call['full_match']}")
                    if getenv_count > 3:
                        print(f"     ... 等 {getenv_count - 3} 个更多调用")
                print()

    # 生成报告
    report = f"""# 配置使用分析报告

## 分析概要
- **分析时间**: 2026-03-19
- **分析文件数**: {len(all_results)}
- **总 os.getenv() 调用**: {total_getenv_calls}
- **总 os.environ 访问**: {total_environ_access}

## 详细分析

### 1. 需要迁移的文件

#### 1.1 src/jwt_auth.py
**状态**: 需要迁移
**分析**: JWT认证模块直接读取环境变量，应使用统一配置

#### 1.2 src/api_gateway/core.py  
**状态**: 需要迁移
**分析**: API网关核心配置，应使用统一配置管理

#### 1.3 web/api/rate_limiter.py
**状态**: 需要迁移
**分析**: 速率限制器配置，应使用统一配置

#### 1.4 db/pool.py
**状态**: 需要迁移
**分析**: 数据库连接池配置，部分已迁移，但仍有直接访问

#### 1.5 db/dingtalk.py
**状态**: 需要迁移
**分析**: 钉钉集成配置，应使用统一配置

### 2. 配置使用模式分类

#### 2.1 数据库配置
- `FUND_DAILY_DB_HOST`, `FUND_DAILY_DB_PORT`, `FUND_DAILY_DB_NAME`
- `FUND_DAILY_DB_USER`, `FUND_DAILY_DB_PASSWORD`

#### 2.2 JWT配置  
- `FUND_DAILY_SECRET_KEY`, `FUND_DAILY_JWT_SECRET`
- `FUND_DAILY_JWT_ALGORITHM`, `FUND_DAILY_JWT_EXPIRE_MINUTES`

#### 2.3 服务器配置
- `FUND_DAILY_SERVER_PORT`, `FUND_DAILY_ENV`
- `FUND_DAILY_LOG_LEVEL`

#### 2.4 第三方服务配置
- `DINGTALK_WEBHOOK_URL`, `DINGTALK_SECRET`
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD`

### 3. 迁移策略建议

#### 3.1 优先级排序
1. **高优先级**: `db/pool.py` (数据库连接，核心功能)
2. **高优先级**: `src/jwt_auth.py` (安全认证，关键功能)  
3. **中优先级**: `src/api_gateway/core.py` (API网关，重要功能)
4. **中优先级**: `web/api/rate_limiter.py` (速率限制，重要功能)
5. **低优先级**: `db/dingtalk.py` (钉钉集成，辅助功能)

#### 3.2 迁移方法
1. **添加导入**: `from src.config import get_config`
2. **获取配置**: `config = get_config()`
3. **替换调用**: `os.getenv("KEY")` → `config.key.value`
4. **类型转换**: 确保类型一致性
5. **默认值处理**: 使用配置类的默认值

#### 3.3 验证步骤
1. 单元测试验证配置读取
2. 功能测试验证业务逻辑
3. 集成测试验证端到端功能
4. 性能测试验证无性能回归

### 4. 预期收益

#### 4.1 代码质量提升
- **统一性**: 所有配置通过单一接口获取
- **类型安全**: 配置值有明确的类型
- **可维护性**: 配置变更只需修改一处
- **可测试性**: 更容易模拟配置进行测试

#### 4.2 运维便利性
- **配置验证**: 启动时验证所有必需配置
- **环境管理**: 更容易管理不同环境的配置
- **监控集成**: 配置变更可触发监控告警
- **文档生成**: 自动生成配置文档

### 5. 风险与缓解

#### 5.1 主要风险
1. **配置读取失败**: 迁移可能导致配置读取失败
2. **类型转换错误**: 字符串到其他类型的转换可能出错
3. **默认值不一致**: 迁移前后默认值可能不同

#### 5.2 缓解措施
1. **渐进式迁移**: 逐个文件迁移，充分测试
2. **类型检查**: 添加类型验证和转换逻辑
3. **默认值对齐**: 确保迁移前后默认值一致
4. **全面测试**: 迁移后运行完整测试套件

### 6. 实施计划

#### 阶段1: 准备 (今天)
1. 完成配置使用分析
2. 制定详细迁移计划
3. 准备测试环境

#### 阶段2: 实施 (今晚)
1. 迁移高优先级文件
2. 运行单元测试验证
3. 修复发现的问题

#### 阶段3: 验证 (明天)
1. 运行完整测试套件
2. 验证API功能正常
3. 性能基准测试

#### 阶段4: 优化 (后续)
1. 配置验证增强
2. 配置热重载支持
3. 配置监控集成
"""

    report_file = project_root / "docs" / "CONFIG_ANALYSIS_REPORT.md"
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📊 分析完成!")
    print(f"   发现 {total_getenv_calls} 个 os.getenv() 调用")
    print(f"   发现 {total_environ_access} 个 os.environ 访问")
    print(f"   报告已保存: {report_file}")

    return all_results


if __name__ == "__main__":
    main()
