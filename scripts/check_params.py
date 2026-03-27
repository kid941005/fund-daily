#!/usr/bin/env python3
"""
参数与需求对应关系检查脚本
检查项目中的参数是否与需求一一对应，查找冗余代码
"""

import ast
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


class CodeAnalyzer:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.function_params: Dict[str, List[Dict]] = {}
        self.api_endpoints: Dict[str, Dict] = {}
        self.duplicate_code: List[Tuple[str, str]] = []

    def analyze_python_files(self):
        """分析所有Python文件"""
        python_files = list(self.project_root.rglob("*.py"))

        for py_file in python_files:
            if "node_modules" in str(py_file) or "__pycache__" in str(py_file):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # 解析AST
                tree = ast.parse(content)

                # 分析函数定义
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        self._analyze_function(node, py_file)

            except Exception as e:
                print(f"解析文件 {py_file} 时出错: {e}")

    def _analyze_function(self, func_node: ast.FunctionDef, file_path: Path):
        """分析单个函数"""
        func_name = func_node.name
        params = []

        # 获取参数
        for arg in func_node.args.args:
            param_name = arg.arg
            params.append({"name": param_name, "type": "positional", "required": True})

        # 获取默认参数
        num_defaults = len(func_node.args.defaults)
        if num_defaults > 0:
            for i in range(num_defaults):
                idx = -num_defaults + i
                if idx < len(params):
                    params[idx]["required"] = False

        # 获取关键字参数
        if func_node.args.kwonlyargs:
            for arg in func_node.args.kwonlyargs:
                params.append({"name": arg.arg, "type": "keyword", "required": False})

        # 检查装饰器（API端点）
        is_api_endpoint = False
        endpoint_info = {}

        for decorator in func_node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    if decorator.func.attr == "route":
                        is_api_endpoint = True
                        # 提取路由信息
                        if decorator.args:
                            endpoint_info["route"] = ast.unparse(decorator.args[0])
                        # 提取方法
                        for keyword in decorator.keywords:
                            if keyword.arg == "methods":
                                if isinstance(keyword.value, ast.List):
                                    endpoint_info["methods"] = [ast.unparse(el) for el in keyword.value.elts]

        # 存储函数信息
        rel_path = str(file_path.relative_to(self.project_root))
        func_key = f"{rel_path}::{func_name}"

        self.function_params[func_key] = {
            "file": rel_path,
            "function": func_name,
            "params": params,
            "is_api_endpoint": is_api_endpoint,
            "endpoint_info": endpoint_info,
        }

        if is_api_endpoint:
            self.api_endpoints[func_key] = self.function_params[func_key]

    def find_duplicate_functions(self):
        """查找重复的函数定义"""
        func_signatures = {}

        for func_key, func_info in self.function_params.items():
            # 创建函数签名（参数名和类型）
            sig = tuple(sorted([p["name"] for p in func_info["params"]]))

            if sig in func_signatures:
                self.duplicate_code.append((func_signatures[sig], func_key))
            else:
                func_signatures[sig] = func_key

    def check_parameter_usage(self):
        """检查参数使用情况"""
        unused_params = []
        required_params_missing = []

        for func_key, func_info in self.function_params.items():
            file_path = self.project_root / func_info["file"]

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                # 查找函数定义行
                func_start = None
                for i, line in enumerate(lines):
                    if f"def {func_info['function']}" in line:
                        func_start = i
                        break

                if func_start is not None:
                    # 分析函数体中的参数使用
                    func_body = "".join(lines[func_start : func_start + 50])

                    for param in func_info["params"]:
                        param_name = param["name"]
                        # 检查参数是否在函数体中使用
                        if param_name not in func_body:
                            unused_params.append({"function": func_key, "parameter": param_name, "type": param["type"]})

            except Exception as e:
                print(f"检查参数使用时出错 {func_key}: {e}")

        return unused_params, required_params_missing

    def generate_report(self):
        """生成检查报告"""
        report = {
            "project": str(self.project_root),
            "total_functions": len(self.function_params),
            "api_endpoints": len(self.api_endpoints),
            "duplicate_functions": [],
            "unused_parameters": [],
            "parameter_analysis": {},
        }

        # 分析重复函数
        self.find_duplicate_functions()
        for func1, func2 in self.duplicate_code:
            report["duplicate_functions"].append({"function1": func1, "function2": func2})

        # 分析未使用参数
        unused_params, missing_params = self.check_parameter_usage()
        report["unused_parameters"] = unused_params

        # 分析API端点参数
        api_params_analysis = {}
        for func_key, func_info in self.api_endpoints.items():
            endpoint_params = []
            for param in func_info["params"]:
                endpoint_params.append({"name": param["name"], "required": param["required"], "type": param["type"]})

            api_params_analysis[func_key] = {
                "endpoint": func_info.get("endpoint_info", {}).get("route", "N/A"),
                "methods": func_info.get("endpoint_info", {}).get("methods", []),
                "parameters": endpoint_params,
            }

        report["api_endpoints_analysis"] = api_params_analysis

        return report


def main():
    project_root = "/home/kid/fund-daily"
    analyzer = CodeAnalyzer(project_root)

    print("🔍 开始分析项目代码...")
    analyzer.analyze_python_files()

    print("📊 生成分析报告...")
    report = analyzer.generate_report()

    # 保存报告
    report_file = Path(project_root) / "参数分析报告.json"
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"✅ 分析完成！报告已保存到: {report_file}")

    # 打印摘要
    print(f"\n📈 分析摘要:")
    print(f"   总函数数: {report['total_functions']}")
    print(f"   API端点: {report['api_endpoints']}")
    print(f"   重复函数: {len(report['duplicate_functions'])}")
    print(f"   未使用参数: {len(report['unused_parameters'])}")

    if report["duplicate_functions"]:
        print(f"\n⚠️  发现重复函数:")
        for dup in report["duplicate_functions"][:5]:  # 只显示前5个
            print(f"   - {dup['function1']}")
            print(f"     {dup['function2']}")

    if report["unused_parameters"]:
        print(f"\n⚠️  发现未使用参数:")
        for param in report["unused_parameters"][:10]:  # 只显示前10个
            print(f"   - {param['function']}: {param['parameter']} ({param['type']})")


if __name__ == "__main__":
    main()
