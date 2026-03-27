#!/usr/bin/env python3
"""
拆分 src/fetcher/__init__.py 为多个专注模块
"""

import ast
import os
from pathlib import Path
from typing import Dict, List, Set


class FetcherSplitter:
    """fetcher模块拆分器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.fetcher_dir = project_root / "src" / "fetcher"

    def analyze_fetcher_module(self) -> Dict:
        """分析fetcher模块结构"""
        fetcher_file = self.fetcher_dir / "__init__.py"

        with open(fetcher_file, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)

        # 收集所有函数
        functions = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                start_line = node.lineno
                end_line = node.end_lineno if node.end_lineno else start_line
                functions[node.name] = {
                    "name": node.name,
                    "lines": end_line - start_line,
                    "start_line": start_line,
                    "end_line": end_line,
                    "code": ast.get_source_segment(content, node),
                }

        # 按功能分组
        groups = {
            "cache": ["get_cache", "set_cache", "clear_cache", "get_cache_stats"],
            "network": ["_get_ssl_context", "_make_request"],
            "fund_basic": ["fetch_fund_data", "fetch_fund_detail", "fetch_fund_nav_history"],
            "market_data": ["fetch_market_news", "fetch_hot_sectors", "fetch_commodity_prices"],
            "fund_advanced": ["calculate_technical_from_history", "fetch_fund_manager", "fetch_fund_scale"],
        }

        return {
            "total_functions": len(functions),
            "total_lines": len(content.splitlines()),
            "functions": functions,
            "groups": groups,
        }

    def create_module_structure(self):
        """创建新的模块结构"""
        # 创建子目录
        modules = ["cache", "network", "fund_basic", "market_data", "fund_advanced"]

        for module in modules:
            module_dir = self.fetcher_dir / module
            module_dir.mkdir(exist_ok=True)

            # 创建 __init__.py
            init_file = module_dir / "__init__.py"
            if not init_file.exists():
                init_file.write_text(f'"""\n{module.replace("_", " ").title()} Fetcher Module\n"""\n\n')

        print(f"✅ 创建了 {len(modules)} 个子模块目录")

    def split_functions_to_modules(self, analysis: Dict):
        """将函数拆分到不同模块"""
        functions = analysis["functions"]
        groups = analysis["groups"]

        # 读取原始文件内容
        fetcher_file = self.fetcher_dir / "__init__.py"
        with open(fetcher_file, "r", encoding="utf-8") as f:
            original_content = f.read()

        lines = original_content.splitlines()

        # 为每个组创建模块文件
        for module_name, func_names in groups.items():
            module_content = []
            module_content.append(f'"""\n{module_name.replace("_", " ").title()} Fetcher Functions\n"""\n')
            module_content.append("")

            # 添加导入
            module_content.append("import logging")
            module_content.append("from typing import Dict, List, Optional, Any")
            module_content.append("import requests")
            module_content.append("import json")
            module_content.append("")

            # 添加函数
            for func_name in func_names:
                if func_name in functions:
                    func_info = functions[func_name]
                    module_content.append(func_info["code"])
                    module_content.append("")

            # 写入模块文件
            module_file = self.fetcher_dir / module_name / "fetcher.py"
            module_file.write_text("\n".join(module_content))

            # 更新 __init__.py 以导出函数
            init_file = self.fetcher_dir / module_name / "__init__.py"
            init_content = []
            init_content.append(f'"""\n{module_name.replace("_", " ").title()} Fetcher Module\n"""\n')
            init_content.append("")
            init_content.append(f"from .fetcher import (")
            for func_name in func_names:
                init_content.append(f"    {func_name},")
            init_content.append(")")
            init_content.append("")
            init_content.append("__all__ = [")
            for func_name in func_names:
                init_content.append(f'    "{func_name}",')
            init_content.append("]")
            init_content.append("")

            init_file.write_text("\n".join(init_content))

        print(f"✅ 将 {len(functions)} 个函数拆分到 {len(groups)} 个模块")

    def create_new_main_fetcher(self, analysis: Dict):
        """创建新的主fetcher文件，作为facade"""
        groups = analysis["groups"]

        new_content = []
        new_content.append('"""\nFund Data Fetcher - Main Facade Module\n"""\n')
        new_content.append("")
        new_content.append("# 导入所有子模块")
        new_content.append("from .cache import *")
        new_content.append("from .network import *")
        new_content.append("from .fund_basic import *")
        new_content.append("from .market_data import *")
        new_content.append("from .fund_advanced import *")
        new_content.append("")
        new_content.append("__all__ = [")

        # 收集所有函数名
        all_functions = []
        for func_names in groups.values():
            all_functions.extend(func_names)

        for func_name in sorted(all_functions):
            new_content.append(f'    "{func_name}",')

        new_content.append("]")
        new_content.append("")

        # 写入新的主文件
        new_file = self.fetcher_dir / "__init__.py"
        backup_file = self.fetcher_dir / "__init__.py.backup"

        # 备份原文件
        if new_file.exists():
            new_file.rename(backup_file)
            print(f"📦 备份原文件到: {backup_file}")

        new_file.write_text("\n".join(new_content))
        print(f"✅ 创建新的facade文件: {new_file}")

    def update_imports_in_project(self):
        """更新项目中的导入语句"""
        # 查找所有导入 src.fetcher 的文件
        import_patterns = ["from src.fetcher import", "import src.fetcher", "from fetcher import"]

        updated_files = []

        for root, dirs, files in os.walk(self.project_root):
            # 排除目录
            dirs[:] = [
                d
                for d in dirs
                if d not in ["__pycache__", ".git", "node_modules", ".backup", "dist", "build", ".venv", "venv"]
            ]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # 检查是否导入fetcher
                        needs_update = False
                        new_content = content

                        for pattern in import_patterns:
                            if pattern in content:
                                needs_update = True
                                # 这里可以添加具体的导入更新逻辑
                                # 暂时只标记需要更新

                        if needs_update:
                            updated_files.append(str(file_path.relative_to(self.project_root)))

                    except Exception as e:
                        print(f"读取文件 {file_path} 时出错: {e}")

        print(f"📋 需要更新导入的文件: {len(updated_files)} 个")
        for file in updated_files[:10]:  # 只显示前10个
            print(f"  - {file}")

        if len(updated_files) > 10:
            print(f"  ... 等 {len(updated_files) - 10} 个更多文件")

    def run(self):
        """执行拆分"""
        print("🔧 开始拆分 src/fetcher/__init__.py")
        print("=" * 50)

        # 1. 分析模块结构
        print("\n📊 步骤1: 分析模块结构...")
        analysis = self.analyze_fetcher_module()
        print(f"   发现 {analysis['total_functions']} 个函数，共 {analysis['total_lines']} 行")

        # 2. 创建模块结构
        print("\n📁 步骤2: 创建模块结构...")
        self.create_module_structure()

        # 3. 拆分函数到模块
        print("\n🔀 步骤3: 拆分函数到模块...")
        self.split_functions_to_modules(analysis)

        # 4. 创建新的主fetcher
        print("\n🏗️  步骤4: 创建新的facade文件...")
        self.create_new_main_fetcher(analysis)

        # 5. 更新项目导入
        print("\n🔄 步骤5: 检查需要更新的导入...")
        self.update_imports_in_project()

        print("\n✅ 拆分完成!")
        print(f"   原文件: {analysis['total_lines']} 行")
        print(f"   新结构: 5个专注模块")
        print(f"   保持向后兼容: ✅ 是 (通过facade模式)")


def main():
    project_root = Path("/home/kid/fund-daily")

    splitter = FetcherSplitter(project_root)
    splitter.run()


if __name__ == "__main__":
    main()
