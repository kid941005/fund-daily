#!/usr/bin/env python3
"""
检查参数命名一致性和冗余代码
"""

import os
import re
from collections import defaultdict
from pathlib import Path


def check_parameter_naming(project_root):
    """检查参数命名一致性"""
    project_path = Path(project_root)

    # 参数命名模式
    param_patterns = defaultdict(set)

    # 检查Python文件
    for py_file in project_path.rglob("*.py"):
        if "node_modules" in str(py_file) or "__pycache__" in str(py_file):
            continue

        rel_path = py_file.relative_to(project_path)

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 查找函数定义
            func_pattern = r"def\s+(\w+)\s*\((.*?)\)\s*:"
            for match in re.finditer(func_pattern, content, re.DOTALL):
                func_name = match.group(1)
                params_str = match.group(2)

                # 解析参数
                params = []
                for param in params_str.split(","):
                    param = param.strip()
                    if "=" in param:
                        param = param.split("=")[0].strip()
                    if param and not param.startswith("*"):
                        params.append(param)

                # 记录参数
                for param in params:
                    param_patterns[param].add(f"{rel_path}::{func_name}")

        except Exception as e:
            print(f"检查文件 {py_file} 时出错: {e}")

    return param_patterns


def check_redundant_validation():
    """检查冗余的验证代码"""
    project_root = "/home/kid/fund-daily"

    # 检查验证文件
    validation_files = ["src/validation.py", "web/api/validation.py"]

    validation_functions = defaultdict(list)

    for vfile in validation_files:
        file_path = Path(project_root) / vfile
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 查找验证函数
        func_pattern = r"def\s+(validate_\w+)\s*\([^)]*\)"
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            validation_functions[func_name].append(vfile)

    return validation_functions


def check_duplicate_error_handling():
    """检查重复的错误处理代码"""
    project_root = "/home/kid/fund-daily"

    error_patterns = [r'return jsonify\({.*?"error".*?}\)', r"except.*?Exception.*?:", r"try:", r"if.*?error.*?:"]

    duplicate_snippets = defaultdict(list)

    for py_file in Path(project_root).rglob("*.py"):
        if "node_modules" in str(py_file) or "__pycache__" in str(py_file) or "test" in str(py_file):
            continue

        rel_path = py_file.relative_to(project_root)

        try:
            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # 检查常见的错误处理模式
            for i, line in enumerate(lines):
                line = line.strip()

                # 检查错误响应
                if '"error"' in line or "'error'" in line:
                    context = "".join(lines[max(0, i - 2) : min(len(lines), i + 3)])
                    duplicate_snippets[line].append(f"{rel_path}:{i+1}")

        except Exception as e:
            continue

    return duplicate_snippets


def main():
    print("🔍 检查参数命名一致性...")
    param_patterns = check_parameter_naming("/home/kid/fund-daily")

    print("\n📊 参数使用统计:")
    for param, usages in sorted(param_patterns.items(), key=lambda x: len(x[1]), reverse=True)[:20]:
        print(f"  {param}: {len(usages)} 处使用")

    print("\n🔍 检查冗余验证代码...")
    validation_funcs = check_redundant_validation()

    duplicate_validations = {k: v for k, v in validation_funcs.items() if len(v) > 1}
    if duplicate_validations:
        print("\n⚠️  发现重复的验证函数:")
        for func, files in duplicate_validations.items():
            print(f"  {func}: {', '.join(files)}")
    else:
        print("✅ 未发现重复的验证函数")

    print("\n🔍 检查重复的错误处理代码...")
    error_snippets = check_duplicate_error_handling()

    duplicate_errors = {k: v for k, v in error_snippets.items() if len(v) > 3}
    if duplicate_errors:
        print(f"\n⚠️  发现 {len(duplicate_errors)} 个重复的错误处理模式:")
        for snippet, locations in list(duplicate_errors.items())[:10]:
            print(f"  模式: {snippet[:50]}...")
            print(f"  位置: {', '.join(locations[:3])}")
            if len(locations) > 3:
                print(f"    等 {len(locations)-3} 个位置")
            print()
    else:
        print("✅ 未发现大量重复的错误处理代码")

    # 检查缓存接口重复
    print("\n🔍 检查缓存接口...")
    cache_files = ["src/cache/redis_cache.py", "src/cache/manager.py", "src/cache_impl.py"]

    cache_functions = defaultdict(list)
    for cfile in cache_files:
        file_path = Path("/home/kid/fund-daily") / cfile
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        func_pattern = r"def\s+(\w+)\s*\([^)]*\)"
        for match in re.finditer(func_pattern, content):
            func_name = match.group(1)
            if func_name.startswith(("get_", "set_", "delete_", "clear_")):
                cache_functions[func_name].append(cfile)

    duplicate_cache = {k: v for k, v in cache_functions.items() if len(v) > 1}
    if duplicate_cache:
        print("\n⚠️  发现重复的缓存函数:")
        for func, files in duplicate_cache.items():
            print(f"  {func}: {', '.join(files)}")
    else:
        print("✅ 缓存接口无重复")


if __name__ == "__main__":
    main()
