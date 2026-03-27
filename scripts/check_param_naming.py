#!/usr/bin/env python3
"""
检查参数命名一致性
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set


def check_parameter_naming(project_root: str) -> Dict[str, Dict]:
    """检查参数命名一致性"""
    project_path = Path(project_root)
    results = {
        "fund_code": {"standard": "fund_code", "variants": set(), "files": {}},
        "user_id": {"standard": "user_id", "variants": set(), "files": {}},
        "timestamp": {"standard": "timestamp", "variants": set(), "files": {}},
        "amount": {"standard": "amount", "variants": set(), "files": {}},
        "date": {"standard": "date", "variants": set(), "files": {}},
    }

    for py_file in project_path.rglob("*.py"):
        if any(exclude in str(py_file) for exclude in ["node_modules", "__pycache__", "test", ".backup"]):
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

                # 检查每个参数概念
                for concept in results.keys():
                    # 查找参数定义
                    param_pattern = rf"\b({concept}|{concept[:-1]})\b"
                    if re.search(param_pattern, params_str):
                        # 获取具体的参数名
                        param_matches = re.findall(rf"\b(\w+)\s*(?:=|:)\s*(?:.*?{concept}.*?)?", params_str)
                        for param_name in param_matches:
                            if concept in param_name.lower():
                                if param_name != results[concept]["standard"]:
                                    results[concept]["variants"].add(param_name)
                                    if str(rel_path) not in results[concept]["files"]:
                                        results[concept]["files"][str(rel_path)] = []
                                    results[concept]["files"][str(rel_path)].append(
                                        {"function": func_name, "parameter": param_name}
                                    )

        except Exception as e:
            print(f"检查文件 {py_file} 时出错: {e}")

    return results


def generate_report(results: Dict[str, Dict]) -> str:
    """生成报告"""
    report = "# 参数命名一致性检查报告\n\n"

    total_issues = 0
    for concept, data in results.items():
        variants = list(data["variants"])
        if variants:
            report += f"## {concept.upper()} 参数\n"
            report += f"- **标准名称**: `{data['standard']}`\n"
            report += f"- **发现变体**: {', '.join(f'`{v}`' for v in variants)}\n"
            report += f"- **影响文件数**: {len(data['files'])}\n"

            if data["files"]:
                report += "- **具体位置**:\n"
                for file_path, functions in list(data["files"].items())[:5]:  # 只显示前5个
                    report += f"  - `{file_path}`:\n"
                    for func_info in functions[:3]:  # 只显示前3个函数
                        report += f"    - `{func_info['function']}()` 使用 `{func_info['parameter']}`\n"

            if len(data["files"]) > 5:
                report += f"  - ... 等 {len(data['files']) - 5} 个文件\n"

            report += "\n"
            total_issues += len(variants)

    if total_issues == 0:
        report += "✅ 所有参数命名一致，符合规范！\n"
    else:
        report += f"\n## 总结\n"
        report += f"- **总问题数**: {total_issues} 个不一致的参数命名\n"
        report += f"- **需要统一的概念**: {len([c for c, d in results.items() if d['variants']])} 个\n"

    return report


def main():
    project_root = "/home/kid/fund-daily"

    print("🔍 检查参数命名一致性...")
    results = check_parameter_naming(project_root)

    report = generate_report(results)
    print(report)

    # 保存报告
    report_file = Path(project_root) / "docs" / "PARAM_NAMING_REPORT.md"
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 报告已保存: {report_file}")


if __name__ == "__main__":
    main()
