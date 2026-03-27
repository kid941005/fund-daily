#!/usr/bin/env python3
"""
统一参数命名脚本
将基金代码参数统一为 fund_code
"""

import os
import re
from pathlib import Path
from typing import List, Tuple


def find_functions_with_code_param(project_root: str) -> List[Tuple[str, str, int]]:
    """查找使用code参数的函数"""
    project_path = Path(project_root)
    results = []

    for py_file in project_path.rglob("*.py"):
        if "node_modules" in str(py_file) or "__pycache__" in str(py_file) or "test" in str(py_file):
            continue

        rel_path = py_file.relative_to(project_path)

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找函数定义中的code参数
            func_pattern = r"def\s+(\w+)\s*\((.*?)\)\s*:"
            for match in re.finditer(func_pattern, content, re.DOTALL):
                func_name = match.group(1)
                params_str = match.group(2)

                # 检查参数中是否有code
                if "code" in params_str and "fund_code" not in params_str:
                    # 获取函数开始行
                    lines_before = content[: match.start()].count("\n")
                    results.append((str(rel_path), func_name, lines_before + 1))

        except Exception as e:
            print(f"检查文件 {py_file} 时出错: {e}")

    return results


def update_function_params(file_path: str, func_name: str, line_num: int):
    """更新函数参数命名"""
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 查找函数定义行
    func_line_idx = line_num - 1

    if func_line_idx >= len(lines):
        print(f"错误: 行号 {line_num} 超出文件范围")
        return False

    func_line = lines[func_line_idx]

    # 使用正则表达式匹配函数定义
    pattern = r"(def\s+" + re.escape(func_name) + r"\s*\()(.*?)(\)\s*:)"
    match = re.search(pattern, func_line)

    if not match:
        print(f"未找到函数 {func_name} 的定义")
        return False

    # 获取参数部分
    params_str = match.group(2)

    # 替换code为fund_code（但避免替换status_code等）
    # 只替换作为独立参数的code
    new_params = re.sub(r"\bcode\b(?=\s*(?:,|$|:))", "fund_code", params_str)

    if new_params == params_str:
        print(f"未找到需要替换的code参数: {func_name}")
        return False

    # 替换整行
    new_line = func_line[: match.start(2)] + new_params + func_line[match.end(2) :]
    lines[func_line_idx] = new_line

    # 写回文件
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    print(f"已更新: {file_path}:{line_num} - {func_name}")
    return True


def update_function_calls(file_path: str):
    """更新函数调用中的参数名"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 查找函数调用中的code参数
    # 模式: 函数名(..., code=值, ...) 或 函数名(..., 值, ...) 但需要更复杂的分析
    # 这里先处理关键字参数的情况

    # 替换关键字参数 code= 为 fund_code=
    new_content = re.sub(r"\bcode\s*=", "fund_code=", content)

    if new_content != content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"已更新函数调用: {file_path}")
        return True

    return False


def main():
    project_root = "/home/kid/fund-daily"

    print("🔍 查找使用code参数的函数...")
    functions = find_functions_with_code_param(project_root)

    print(f"\n📊 找到 {len(functions)} 个使用code参数的函数:")
    for file_path, func_name, line_num in functions[:20]:  # 只显示前20个
        print(f"  {file_path}:{line_num} - {func_name}")

    if len(functions) > 20:
        print(f"  等 {len(functions) - 20} 个函数...")

    # 询问用户是否继续
    response = input("\n是否继续更新这些函数？(y/n): ")
    if response.lower() != "y":
        print("操作已取消")
        return

    print("\n🔄 开始更新函数参数...")
    updated_count = 0

    for file_path, func_name, line_num in functions:
        full_path = Path(project_root) / file_path
        if update_function_params(str(full_path), func_name, line_num):
            updated_count += 1

    print(f"\n✅ 更新完成！共更新了 {updated_count} 个函数")

    # 更新函数调用
    print("\n🔄 更新函数调用中的参数名...")
    call_updated = 0

    # 只更新主要的业务文件
    main_dirs = ["src", "web", "db"]
    for main_dir in main_dirs:
        dir_path = Path(project_root) / main_dir
        if not dir_path.exists():
            continue

        for py_file in dir_path.rglob("*.py"):
            if "node_modules" in str(py_file) or "__pycache__" in str(py_file):
                continue

            if update_function_calls(str(py_file)):
                call_updated += 1

    print(f"✅ 更新了 {call_updated} 个文件中的函数调用")

    print("\n📝 总结:")
    print(f"  1. 更新了 {updated_count} 个函数的参数定义")
    print(f"  2. 更新了 {call_updated} 个文件中的函数调用")
    print(f"  3. 基金代码参数已统一为 fund_code")

    # 创建命名规范文档
    print("\n📄 创建命名规范文档...")
    create_naming_standards(project_root)


def create_naming_standards(project_root: str):
    """创建命名规范文档"""
    standards_content = """# Fund Daily 命名规范

## 参数命名规范

### 核心参数
| 概念 | 标准名称 | 说明 | 示例 |
|------|----------|------|------|
| 基金代码 | `fund_code` | 6位数字加可选后缀 | `"000001"`, `"510300"` |
| 用户ID | `user_id` | 用户唯一标识 | `123`, `"user_abc"` |
| 持仓金额 | `amount` | 持仓数量或金额 | `1000.00` |
| 成本价 | `cost_basis` | 购买成本 | `1.2345` |
| 时间戳 | `timestamp` | Unix时间戳 | `1640995200` |
| 日期 | `date` | YYYY-MM-DD格式 | `"2024-01-01"` |

### 布尔参数
| 模式 | 示例 | 说明 |
|------|------|------|
| `is_` 前缀 | `is_active`, `is_valid` | 状态标志 |
| `has_` 前缀 | `has_permission`, `has_data` | 拥有关系 |
| `should_` 前缀 | `should_update`, `should_cache` | 行为标志 |

### 集合参数
| 类型 | 命名模式 | 示例 |
|------|----------|------|
| 列表 | 复数形式 | `funds`, `users`, `items` |
| 字典 | 单数形式 + 后缀 | `fund_data`, `user_info` |
| 查询结果 | `result` 或具体名称 | `search_result`, `fund_list` |

## 函数命名规范

### 验证函数
- 前缀: `validate_`
- 示例: `validate_fund_code()`, `validate_user_input()`

### 获取函数
- 前缀: `get_`, `fetch_`, `load_`
- 示例: `get_user_by_id()`, `fetch_fund_data()`

### 创建函数
- 前缀: `create_`, `add_`, `insert_`
- 示例: `create_user()`, `add_holding()`

### 更新函数
- 前缀: `update_`, `modify_`, `set_`
- 示例: `update_user_profile()`, `set_user_preferences()`

### 删除函数
- 前缀: `delete_`, `remove_`, `clear_`
- 示例: `delete_holding()`, `clear_cache()`

## 变量命名规范

### 局部变量
- 小写字母，下划线分隔
- 描述性名称
- 示例: `fund_data`, `user_count`, `is_valid`

### 常量
- 大写字母，下划线分隔
- 放在文件顶部
- 示例: `MAX_RETRY_COUNT`, `DEFAULT_CACHE_TTL`

### 类属性
- 小写字母，下划线分隔
- 私有属性以 `_` 开头
- 示例: `self.user_id`, `self._cache`

## 数据库字段命名

### 表名
- 小写字母，下划线分隔
- 复数形式
- 示例: `users`, `fund_holdings`

### 字段名
- 小写字母，下划线分隔
- 与参数命名一致
- 示例: `fund_code`, `user_id`, `created_at`

## 代码示例

### 好的示例
```python
def calculate_fund_score(fund_code: str, date: str = None) -> float:
    \"\"\"计算基金评分\"\"\"
    fund_data = fetch_fund_data(fund_code, date)
    return calculate_score(fund_data)

def update_user_holdings(user_id: int, holdings_data: List[Dict]) -> bool:
    \"\"\"更新用户持仓\"\"\"
    for holding in holdings_data:
        validate_holding_data(holding)
    return db.update_holdings(user_id, holdings_data)
```

### 避免的示例
```python
def calcScore(code: str, d: str = None) -> float:  # 不清晰
def updateHoldings(uid: int, data: List) -> bool:  # 缩写不一致
```

## 实施指南

1. **新代码**: 必须遵循此规范
2. **现有代码**: 逐步重构，优先修改频繁使用的代码
3. **代码审查**: 检查命名规范遵守情况
4. **自动化检查**: 使用工具检查命名一致性

## 例外情况

1. **第三方API**: 遵循第三方命名约定
2. **已有标准**: 遵循行业或技术标准
3. **性能关键代码**: 在必要时使用缩写

---
*最后更新: 2026-03-19*
*版本: 1.0*
"""

    standards_file = Path(project_root) / "docs" / "CODING_STANDARDS.md"
    standards_file.parent.mkdir(exist_ok=True)

    with open(standards_file, "w", encoding="utf-8") as f:
        f.write(standards_content)

    print(f"✅ 命名规范文档已创建: {standards_file}")


if __name__ == "__main__":
    main()
