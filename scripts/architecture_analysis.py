#!/usr/bin/env python3
"""
架构分析：从系统工程和全局视角分析项目架构
"""

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set


class ArchitectureAnalyzer:
    """架构分析器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.architecture = {
            "layers": defaultdict(list),
            "modules": {},
            "dependencies": defaultdict(set),
            "metrics": {},
            "issues": [],
        }

    def analyze_architecture(self):
        """分析整体架构"""
        print("🏗️  分析项目架构...")

        # 识别架构层
        self._identify_architecture_layers()

        # 分析模块依赖
        self._analyze_module_dependencies()

        # 计算架构指标
        self._calculate_architecture_metrics()

        # 识别架构问题
        self._identify_architecture_issues()

        return self.architecture

    def _identify_architecture_layers(self):
        """识别架构层"""
        layer_patterns = {
            "presentation": ["web/", "vue3/", "templates/", "static/"],
            "application": ["api/", "services/", "gateway/"],
            "domain": ["models/", "entities/", "value_objects/"],
            "infrastructure": ["db/", "cache/", "fetcher/", "utils/"],
            "config": ["config", "constants", "settings"],
        }

        for root, dirs, files in os.walk(self.project_root):
            # 排除目录
            dirs[:] = [
                d
                for d in dirs
                if d
                not in ["__pycache__", ".git", "node_modules", ".backup", "dist", "build", ".venv", "venv", "tests"]
            ]

            for file in files:
                if file.endswith(".py"):
                    file_path = Path(root) / file
                    rel_path = str(file_path.relative_to(self.project_root))

                    # 确定所属层
                    assigned = False
                    for layer, patterns in layer_patterns.items():
                        for pattern in patterns:
                            if pattern in rel_path:
                                self.architecture["layers"][layer].append(rel_path)
                                assigned = True
                                break
                        if assigned:
                            break

                    if not assigned:
                        # 根据父目录判断
                        parent = Path(rel_path).parent
                        if "src" in str(parent):
                            self.architecture["layers"]["domain"].append(rel_path)
                        else:
                            self.architecture["layers"]["infrastructure"].append(rel_path)

    def _analyze_module_dependencies(self):
        """分析模块依赖"""
        print("🔗 分析模块依赖关系...")

        for layer, files in self.architecture["layers"].items():
            for file_path in files:
                full_path = self.project_root / file_path
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # 提取导入
                    imports = self._extract_imports(content)
                    self.architecture["modules"][file_path] = {
                        "layer": layer,
                        "imports": imports,
                        "size": len(content.splitlines()),
                    }

                    # 记录依赖
                    for imp in imports:
                        self.architecture["dependencies"][file_path].add(imp)

                except Exception as e:
                    print(f"分析文件 {file_path} 时出错: {e}")

    def _extract_imports(self, content: str) -> List[str]:
        """提取导入语句"""
        imports = []
        lines = content.splitlines()

        for line in lines:
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                # 提取模块名
                if line.startswith("import "):
                    parts = line[7:].split()
                    if parts:
                        imports.append(parts[0].split(".")[0])
                elif line.startswith("from "):
                    parts = line[5:].split(" import ")
                    if len(parts) > 1:
                        imports.append(parts[0].split(".")[0])

        return imports

    def _calculate_architecture_metrics(self):
        """计算架构指标"""
        print("📊 计算架构指标...")

        metrics = {
            "total_files": sum(len(files) for files in self.architecture["layers"].values()),
            "layer_distribution": {},
            "dependency_complexity": 0,
            "circular_dependencies": [],
            "layer_violations": [],
        }

        # 各层文件分布
        for layer, files in self.architecture["layers"].items():
            metrics["layer_distribution"][layer] = len(files)

        # 依赖复杂度
        total_deps = sum(len(deps) for deps in self.architecture["dependencies"].values())
        metrics["dependency_complexity"] = total_deps / metrics["total_files"] if metrics["total_files"] > 0 else 0

        # 检查循环依赖
        metrics["circular_dependencies"] = self._find_circular_dependencies()

        # 检查层违规（高层依赖低层）
        metrics["layer_violations"] = self._find_layer_violations()

        self.architecture["metrics"] = metrics

    def _find_circular_dependencies(self) -> List[List[str]]:
        """查找循环依赖"""
        # 简化版本：检查明显的循环
        circular = []
        visited = set()

        def dfs(node, path):
            if node in path:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if len(cycle) > 2:  # 忽略自引用
                    circular.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            path.append(node)

            for dep in self.architecture["dependencies"].get(node, []):
                # 只检查项目内的模块
                if dep in self.architecture["modules"]:
                    dfs(dep, path.copy())

        for module in self.architecture["modules"]:
            dfs(module, [])

        return circular[:5]  # 只返回前5个

    def _find_layer_violations(self) -> List[Dict]:
        """查找层架构违规"""
        violations = []

        # 定义允许的依赖方向
        allowed_dependencies = {
            "presentation": ["application", "domain", "infrastructure", "config"],
            "application": ["domain", "infrastructure", "config"],
            "domain": ["infrastructure", "config"],
            "infrastructure": ["config"],
            "config": [],
        }

        for source_file, source_info in self.architecture["modules"].items():
            source_layer = source_info["layer"]

            for dep in self.architecture["dependencies"][source_file]:
                if dep in self.architecture["modules"]:
                    dep_info = self.architecture["modules"][dep]
                    dep_layer = dep_info["layer"]

                    # 检查是否允许
                    if dep_layer not in allowed_dependencies.get(source_layer, []):
                        violations.append(
                            {
                                "source": source_file,
                                "source_layer": source_layer,
                                "dependency": dep,
                                "dependency_layer": dep_layer,
                                "issue": f"{source_layer}层不应依赖{dep_layer}层",
                            }
                        )

        return violations[:10]  # 只返回前10个

    def _identify_architecture_issues(self):
        """识别架构问题"""
        print("🔍 识别架构问题...")

        issues = []

        # 1. 检查大文件
        for file_path, info in self.architecture["modules"].items():
            if info["size"] > 500:
                issues.append(
                    {
                        "type": "large_file",
                        "file": file_path,
                        "size": info["size"],
                        "layer": info["layer"],
                        "description": f"文件过大 ({info['size']} 行)，难以维护",
                        "suggestion": "考虑拆分为多个小文件",
                    }
                )

        # 2. 检查层分布
        layer_dist = self.architecture["metrics"]["layer_distribution"]
        if layer_dist.get("presentation", 0) == 0:
            issues.append(
                {
                    "type": "missing_layer",
                    "layer": "presentation",
                    "description": "缺少表示层（前端/API接口）",
                    "suggestion": "检查前端代码是否在正确位置",
                }
            )

        # 3. 检查依赖复杂度
        if self.architecture["metrics"]["dependency_complexity"] > 5:
            issues.append(
                {
                    "type": "high_coupling",
                    "metric": self.architecture["metrics"]["dependency_complexity"],
                    "description": f"依赖复杂度高 ({self.architecture['metrics']['dependency_complexity']:.1f})",
                    "suggestion": "减少模块间依赖，提高内聚性",
                }
            )

        # 4. 检查循环依赖
        if self.architecture["metrics"]["circular_dependencies"]:
            issues.append(
                {
                    "type": "circular_dependency",
                    "count": len(self.architecture["metrics"]["circular_dependencies"]),
                    "description": f"发现 {len(self.architecture['metrics']['circular_dependencies'])} 个循环依赖",
                    "suggestion": "打破循环依赖，引入抽象层",
                }
            )

        # 5. 检查层违规
        if self.architecture["metrics"]["layer_violations"]:
            issues.append(
                {
                    "type": "layer_violation",
                    "count": len(self.architecture["metrics"]["layer_violations"]),
                    "description": f"发现 {len(self.architecture['metrics']['layer_violations'])} 个层架构违规",
                    "suggestion": "遵循依赖倒置原则，高层不应依赖低层实现",
                }
            )

        self.architecture["issues"] = issues

    def generate_architecture_report(self) -> str:
        """生成架构报告"""
        metrics = self.architecture["metrics"]

        report = f"""# 系统架构分析报告

## 架构概览
- **项目路径**: {self.project_root}
- **总文件数**: {metrics['total_files']}
- **架构层数**: {len(self.architecture['layers'])}
- **发现问题数**: {len(self.architecture['issues'])}

## 架构层分布
"""

        for layer, count in sorted(metrics["layer_distribution"].items(), key=lambda x: x[1], reverse=True):
            report += f"- **{layer}层**: {count} 个文件\n"

        report += f"""
## 架构指标

### 1. 依赖复杂度
- **平均依赖数**: {metrics['dependency_complexity']:.1f}
- **评估**: {'✅ 良好' if metrics['dependency_complexity'] < 3 else '⚠️ 偏高' if metrics['dependency_complexity'] < 5 else '❌ 过高'}

### 2. 循环依赖
- **发现循环**: {len(metrics['circular_dependencies'])} 个
- **评估**: {'✅ 无循环依赖' if not metrics['circular_dependencies'] else '❌ 存在循环依赖'}

### 3. 层架构合规性
- **违规数量**: {len(metrics['layer_violations'])} 个
- **评估**: {'✅ 层架构合规' if not metrics['layer_violations'] else '❌ 存在层违规'}

## 详细架构分析

### 各层文件列表
"""

        for layer, files in self.architecture["layers"].items():
            report += f"\n#### {layer}层 ({len(files)} 个文件)\n"
            for file in sorted(files)[:10]:  # 只显示前10个
                report += f"- `{file}`\n"
            if len(files) > 10:
                report += f"- ... 等 {len(files) - 10} 个更多文件\n"

        report += """
## 架构问题分析
"""

        if self.architecture["issues"]:
            for issue in self.architecture["issues"]:
                report += f"""
### {issue['type'].replace('_', ' ').title()}
**描述**: {issue['description']}
**建议**: {issue['suggestion']}
"""
                if "file" in issue:
                    report += f"**文件**: `{issue['file']}`\n"
                if "count" in issue:
                    report += f"**数量**: {issue['count']} 个\n"
        else:
            report += "\n✅ 未发现重大架构问题\n"

        # 添加架构改进建议
        report += """
## 架构改进建议

### 1. 架构优化 (高优先级)
"""

        if metrics["circular_dependencies"]:
            report += "- **打破循环依赖**: 引入接口抽象，使用依赖注入\n"

        if metrics["layer_violations"]:
            report += "- **修复层违规**: 遵循依赖倒置原则，高层定义接口，低层实现\n"

        if any(issue["type"] == "large_file" for issue in self.architecture["issues"]):
            report += "- **拆分大文件**: 将超过500行的文件拆分为专注的模块\n"

        report += """
### 2. 代码结构优化 (中优先级)
- **提高内聚性**: 将相关功能组织到同一模块
- **降低耦合度**: 减少模块间不必要的依赖
- **统一接口**: 定义清晰的模块接口和契约

### 3. 可维护性优化 (低优先级)
- **完善文档**: 为每个模块添加架构文档
- **依赖管理**: 建立清晰的依赖管理策略
- **监控指标**: 监控架构指标变化，及时发现问题

## 架构评估结论
"""

        # 根据问题数量评估
        issue_count = len(self.architecture["issues"])
        circular_count = len(metrics["circular_dependencies"])
        violation_count = len(metrics["layer_violations"])

        if issue_count == 0 and circular_count == 0 and violation_count == 0:
            report += "✅ **架构优秀**: 项目架构清晰，层分离合理，无重大架构问题。"
        elif issue_count < 5 and circular_count == 0:
            report += "✅ **架构良好**: 整体架构合理，存在少量可优化的问题。"
        elif issue_count < 10 or circular_count > 0:
            report += "⚠️ **架构中等**: 存在需要关注的架构问题，建议进行优化。"
        else:
            report += "❌ **架构需要改进**: 存在较多架构问题，建议进行系统性的架构重构。"

        report += f"""

**关键发现**:
- 项目采用 {len(self.architecture['layers'])} 层架构
- 依赖复杂度: {metrics['dependency_complexity']:.1f}
- 循环依赖: {circular_count} 个
- 层违规: {violation_count} 个

**建议行动**: 按照优先级逐步解决架构问题，保持架构的清晰和可维护性。
"""

        return report


def main():
    project_root = Path("/home/kid/fund-daily")

    print("🏗️  开始系统架构分析...")
    print("=" * 60)

    # 创建分析器
    analyzer = ArchitectureAnalyzer(project_root)

    # 分析架构
    architecture = analyzer.analyze_architecture()

    # 生成报告
    report = analyzer.generate_architecture_report()

    # 保存报告
    report_file = project_root / "docs" / "SYSTEM_ARCHITECTURE_ANALYSIS.md"
    report_file.parent.mkdir(exist_ok=True)

    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n📊 架构分析完成!")
    print(f"   分析文件数: {architecture['metrics']['total_files']}")
    print(f"   架构层数: {len(architecture['layers'])}")
    print(f"   发现问题: {len(architecture['issues'])}")
    print(f"   报告已保存: {report_file}")

    # 显示摘要
    print(f"\n📋 架构层分布:")
    for layer, count in sorted(architecture["metrics"]["layer_distribution"].items()):
        print(f"  {layer}: {count} 个文件")

    print(f"\n⚠️  架构问题:")
    for issue in architecture["issues"]:
        print(f"  • {issue['description']}")


if __name__ == "__main__":
    main()
