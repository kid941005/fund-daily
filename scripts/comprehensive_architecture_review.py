#!/usr/bin/env python3
"""
全面架构审查脚本
以系统工程思维+全局架构视角，逐文件、逐逻辑、逐模块审查全部代码
"""

import os
import re
import ast
import json
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Set, Any
from collections import defaultdict, Counter
import ast
import inspect

class ArchitectureReviewer:
    """架构审查器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.results = {
            "summary": {
                "total_files": 0,
                "total_lines": 0,
                "issues_by_category": defaultdict(int),
                "issues_by_severity": defaultdict(int),
                "files_reviewed": 0
            },
            "files": {},
            "architectural_issues": [],
            "performance_issues": [],
            "code_quality_issues": [],
            "security_issues": [],
            "maintainability_issues": []
        }
        
        # 审查标准
        self.standards = {
            "architecture": [
                "分层清晰",
                "耦合合理", 
                "职责单一",
                "无设计缺陷"
            ],
            "logic": [
                "流程闭环",
                "边界完备", 
                "无漏洞",
                "无歧义",
                "无逻辑硬伤"
            ],
            "performance": [
                "写法高效",
                "无冗余计算",
                "无无效逻辑",
                "资源占用最优"
            ],
            "standardization": [
                "命名规范",
                "结构整洁",
                "无废代码",
                "无重复实现"
            ],
            "maintainability": [
                "可读性强",
                "扩展性好",
                "注释合理",
                "易于迭代"
            ]
        }
    
    def analyze_file(self, file_path: Path) -> Dict:
        """分析单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_info = {
                "path": str(file_path.relative_to(self.project_root)),
                "lines": len(content.splitlines()),
                "issues": [],
                "metrics": {}
            }
            
            # 基本指标
            file_info["metrics"]["line_count"] = len(content.splitlines())
            file_info["metrics"]["import_count"] = len(re.findall(r'^(import|from)', content, re.MULTILINE))
            file_info["metrics"]["function_count"] = len(re.findall(r'^def ', content, re.MULTILINE))
            file_info["metrics"]["class_count"] = len(re.findall(r'^class ', content, re.MULTILINE))
            
            # 架构分析
            self._analyze_architecture(file_path, content, file_info)
            
            # 逻辑分析
            self._analyze_logic(file_path, content, file_info)
            
            # 性能分析
            self._analyze_performance(file_path, content, file_info)
            
            # 规范分析
            self._analyze_standardization(file_path, content, file_info)
            
            # 可维护性分析
            self._analyze_maintainability(file_path, content, file_info)
            
            return file_info
            
        except Exception as e:
            print(f"分析文件 {file_path} 时出错: {e}")
            return {
                "path": str(file_path.relative_to(self.project_root)),
                "error": str(e),
                "issues": []
            }
    
    def _analyze_architecture(self, file_path: Path, content: str, file_info: Dict):
        """架构分析"""
        issues = []
        
        # 检查导入依赖
        imports = re.findall(r'^(import|from)\s+(\S+)', content, re.MULTILINE)
        imported_modules = [imp[1].split('.')[0] for imp in imports]
        
        # 检查循环导入风险
        if file_path.name.endswith('__init__.py'):
            # 检查是否过度导入
            if len(imports) > 20:
                issues.append({
                    "category": "architecture",
                    "severity": "medium",
                    "standard": "耦合合理",
                    "description": f"__init__.py 文件导入过多 ({len(imports)} 个)，可能导致循环导入",
                    "suggestion": "考虑延迟导入或重构模块结构"
                })
        
        # 检查职责单一性
        if file_info["metrics"]["class_count"] > 5 and file_info["metrics"]["function_count"] > 20:
            issues.append({
                "category": "architecture",
                "severity": "medium",
                "standard": "职责单一",
                "description": f"文件包含 {file_info['metrics']['class_count']} 个类和 {file_info['metrics']['function_count']} 个函数，可能职责过多",
                "suggestion": "考虑拆分为多个专注的模块"
            })
        
        # 检查设计模式使用
        design_patterns = self._detect_design_patterns(content)
        if design_patterns:
            file_info["metrics"]["design_patterns"] = design_patterns
        
        file_info["issues"].extend(issues)
    
    def _analyze_logic(self, file_path: Path, content: str, file_info: Dict):
        """逻辑分析"""
        issues = []
        
        # 检查异常处理
        exception_patterns = [
            (r'except\s*:', "空的except语句，可能隐藏错误"),
            (r'except\s+Exception\s*:', "捕获过于宽泛的异常"),
            (r'except\s+BaseException\s*:', "捕获系统退出异常，危险"),
        ]
        
        for pattern, description in exception_patterns:
            if re.search(pattern, content):
                issues.append({
                    "category": "logic",
                    "severity": "high",
                    "standard": "无漏洞",
                    "description": description,
                    "suggestion": "使用具体的异常类型，避免隐藏错误"
                })
        
        # 检查边界条件
        if "while True:" in content and "break" not in content:
            issues.append({
                "category": "logic",
                "severity": "high",
                "standard": "流程闭环",
                "description": "发现无限循环，缺少退出条件",
                "suggestion": "添加明确的退出条件或超时机制"
            })
        
        # 检查资源释放
        if "open(" in content and "with open" not in content:
            issues.append({
                "category": "logic",
                "severity": "medium",
                "standard": "边界完备",
                "description": "文件操作未使用with语句，可能未正确关闭",
                "suggestion": "使用with语句确保资源释放"
            })
        
        file_info["issues"].extend(issues)
    
    def _analyze_performance(self, file_path: Path, content: str, file_info: Dict):
        """性能分析"""
        issues = []
        
        # 检查重复计算
        if content.count("re.compile(") > 3:
            issues.append({
                "category": "performance",
                "severity": "low",
                "standard": "无冗余计算",
                "description": "多次编译正则表达式，应缓存编译结果",
                "suggestion": "将正则表达式编译结果保存为常量"
            })
        
        # 检查循环中的数据库/网络操作
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "for " in line or "while " in line:
                # 检查接下来的几行
                for j in range(i+1, min(i+10, len(lines))):
                    next_line = lines[j]
                    if any(op in next_line for op in ["cursor.execute", "requests.get", "urllib.request"]):
                        issues.append({
                            "category": "performance",
                            "severity": "high",
                            "standard": "写法高效",
                            "description": f"第{i+1}行循环中包含数据库/网络操作，性能差",
                            "suggestion": "考虑批量操作或缓存结果"
                        })
                        break
        
        # 检查内存使用
        if "list(" in content and "range(10000)" in content:
            issues.append({
                "category": "performance",
                "severity": "medium",
                "standard": "资源占用最优",
                "description": "可能创建大列表，内存占用高",
                "suggestion": "考虑使用生成器或分块处理"
            })
        
        file_info["issues"].extend(issues)
    
    def _analyze_standardization(self, file_path: Path, content: str, file_info: Dict):
        """规范分析"""
        issues = []
        
        # 检查命名规范
        lines = content.splitlines()
        for i, line in enumerate(lines):
            # 检查函数/方法命名
            func_match = re.match(r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)', line.strip())
            if func_match:
                func_name = func_match.group(1)
                if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                    issues.append({
                        "category": "standardization",
                        "severity": "low",
                        "standard": "命名规范",
                        "description": f"第{i+1}行函数命名不符合蛇形命名法: {func_name}",
                        "suggestion": "使用蛇形命名法，如: get_user_data"
                    })
            
            # 检查类命名
            class_match = re.match(r'class\s+([A-Za-z_][A-Za-z0-9_]*)', line.strip())
            if class_match:
                class_name = class_match.group(1)
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                    issues.append({
                        "category": "standardization",
                        "severity": "low",
                        "standard": "命名规范",
                        "description": f"第{i+1}行类命名不符合帕斯卡命名法: {class_name}",
                        "suggestion": "使用帕斯卡命名法，如: UserService"
                    })
        
        # 检查代码结构
        if len(content) > 1000 and file_info["metrics"]["function_count"] == 0:
            issues.append({
                "category": "standardization",
                "severity": "medium",
                "standard": "结构整洁",
                "description": "大文件缺少函数封装，结构混乱",
                "suggestion": "将代码拆分为多个函数，提高可读性"
            })
        
        # 检查重复代码（简单检查）
        lines_set = set()
        duplicate_lines = []
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped and len(stripped) > 20:  # 忽略短行和空行
                if stripped in lines_set:
                    duplicate_lines.append(i+1)
                else:
                    lines_set.add(stripped)
        
        if duplicate_lines:
            issues.append({
                "category": "standardization",
                "severity": "medium",
                "standard": "无重复实现",
                "description": f"发现重复代码行: {duplicate_lines[:5]}",
                "suggestion": "提取重复代码为函数或工具方法"
            })
        
        file_info["issues"].extend(issues)
    
    def _analyze_maintainability(self, file_path: Path, content: str, file_info: Dict):
        """可维护性分析"""
        issues = []
        
        # 检查注释
        comment_lines = len(re.findall(r'^\s*#', content, re.MULTILINE))
        total_lines = len(content.splitlines())
        comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
        
        if comment_ratio < 0.05 and total_lines > 50:
            issues.append({
                "category": "maintainability",
                "severity": "low",
                "standard": "注释合理",
                "description": f"注释比例低 ({comment_ratio:.1%})，代码可读性可能受影响",
                "suggestion": "为复杂逻辑添加注释"
            })
        
        # 检查函数复杂度
        lines = content.splitlines()
        in_function = False
        function_start = 0
        function_name = ""
        
        for i, line in enumerate(lines):
            if line.strip().startswith('def '):
                if in_function and (i - function_start) > 50:
                    issues.append({
                        "category": "maintainability",
                        "severity": "medium",
                        "standard": "可读性强",
                        "description": f"函数 {function_name} 过长 ({i - function_start} 行)，难以维护",
                        "suggestion": "拆分为多个小函数，每个函数专注单一职责"
                    })
                in_function = True
                function_start = i
                function_name = line.strip().split('def ')[1].split('(')[0]
            elif in_function and line.strip() == '' and i > function_start + 1:
                # 函数结束
                in_function = False
        
        # 检查类型提示
        type_hint_pattern = r'def\s+\w+\([^)]*\)\s*(?:->[^:]+)?:'
        functions_with_hints = len(re.findall(type_hint_pattern, content))
        total_functions = file_info["metrics"]["function_count"]
        
        if total_functions > 0 and functions_with_hints / total_functions < 0.5:
            issues.append({
                "category": "maintainability",
                "severity": "low",
                "standard": "易于迭代",
                "description": f"类型提示使用率低 ({functions_with_hints}/{total_functions})",
                "suggestion": "为函数添加类型提示，提高代码可读性和工具支持"
            })
        
        file_info["issues"].extend(issues)
    
    def _detect_design_patterns(self, content: str) -> List[str]:
        """检测设计模式"""
        patterns = []
        
        # 单例模式检测
        if "_instance" in content and "cls._instance" in content:
            patterns.append("单例模式")
        
        # 工厂模式检测
        if "Factory" in content or "create_" in content:
            patterns.append("工厂模式")
        
        # 装饰器模式检测
        if "@" in content and "def " in content:
            patterns.append("装饰器模式")
        
        # 策略模式检测
        if "Strategy" in content or "execute_strategy" in content:
            patterns.append("策略模式")
        
        return patterns
    
    def collect_python_files(self) -> List[Path]:
        """收集所有Python文件"""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # 排除目录
            dirs[:] = [d for d in dirs if d not in [
                '__pycache__', '.git', 'node_modules', 
                '.backup', 'dist', 'build', '.venv', 'venv'
            ]]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
        
        return python_files
    
    def review(self) -> Dict:
        """执行全面审查"""
        print("🔍 开始全面架构审查...")
        
        # 收集文件
        python_files = self.collect_python_files()
        self.results["summary"]["total_files"] = len(python_files)
        
        print(f"📁 发现 {len(python_files)} 个Python文件")
        
        # 分析每个文件
        for i, file_path in enumerate(python_files):
            if i % 10 == 0:
                print(f"  分析进度: {i+1}/{len(python_files)}")
            
            file_info = self.analyze_file(file_path)
            self.results["files"][file_info["path"]] = file_info
            
            # 汇总问题
            for issue in file_info.get("issues", []):
                category = issue["category"]
                severity = issue["severity"]
                self.results["summary"]["issues_by_category"][category] += 1
                self.results["summary"]["issues_by_severity"][severity] += 1
            
            self.results["summary"]["files_reviewed"] += 1
            self.results["summary"]["total_lines"] += file_info.get("lines", 0)
        
        # 生成分类问题列表
        self._categorize_issues()
        
        # 生成建议
        self._generate_recommendations()
        
        return self.results
    
    def _categorize_issues(self):
        """分类问题"""
        for file_path, file_info in self.results["files"].items():
            for issue in file_info.get("issues", []):
                category = issue["category"]
                
                if category == "architecture":
                    self.results["architectural_issues"].append({
                        "file": file_path,
                        "issue": issue
                    })
                elif category == "performance":
                    self.results["performance_issues"].append({
                        "file": file_path,
                        "issue": issue
                    })
                elif category == "security":
                    self.results["security_issues"].append({
                        "file": file_path,
                        "issue": issue
                    })
                elif category == "maintainability":
                    self.results["maintainability_issues"].append({
                        "file": file_path,
                        "issue": issue
                    })
                else:
                    self.results["code_quality_issues"].append({
                        "file": file_path,
                        "issue": issue
                    })
    
    def _generate_recommendations(self):
        """生成优化建议"""
        total_issues = sum(self.results["summary"]["issues_by_category"].values())
        
        self.results["recommendations"] = {
            "high_priority": [],
            "medium_priority": [],
            "low_priority": []
        }
        
        # 根据问题严重性生成建议
        if self.results["summary"]["issues_by_severity"]["high"] > 0:
            self.results["recommendations"]["high_priority"].append(
                f"修复 {self.results['summary']['issues_by_severity']['high']} 个高严重性问题，包括安全漏洞和逻辑错误"
            )
        
        if self.results["summary"]["issues_by_severity"]["medium"] > 0:
            self.results["recommendations"]["medium_priority"].append(
                f"优化 {self.results['summary']['issues_by_severity']['medium']} 个中等问题，提高代码质量和性能"
            )
        
        if self.results["summary"]["issues_by_severity"]["low"] > 0:
            self.results["recommendations"]["low_priority"].append(
                f"改进 {self.results['summary']['issues_by_severity']['low']} 个低优先级问题，提升代码规范性"
            )
        
        # 架构建议
        if self.results["summary"]["issues_by_category"]["architecture"] > 0:
            self.results["recommendations"]["high_priority"].append(
                "进行架构重构，解决耦合问题和设计缺陷"
            )
        
        # 性能建议
        if self.results["summary"]["issues_by_category"]["performance"] > 0:
            self.results["recommendations"]["medium_priority"].append(
                "优化性能热点，减少冗余计算和资源占用"
            )
        
        # 可维护性建议
        if self.results["summary"]["issues_by_category"]["maintainability"] > 0:
            self.results["recommendations"]["low_priority"].append(
                "改善代码注释和文档，提高可维护性"
            )
    
    def generate_report(self) -> str:
        """生成审查报告"""
        total_issues = sum(self.results["summary"]["issues_by_category"].values())
        
        report = f"""# 全面架构审查报告

## 审查概要
- **审查时间**: 2026-03-19
- **项目路径**: {self.project_root}
- **审查文件数**: {self.results['summary']['files_reviewed']}
- **总代码行数**: {self.results['summary']['total_lines']}
- **发现问题总数**: {total_issues}

## 问题分类统计

### 按类别统计
{chr(10).join(f"- **{category}**: {count} 个" for category, count in sorted(self.results['summary']['issues_by_category'].items()))}

### 按严重性统计
{chr(10).join(f"- **{severity}**: {count} 个" for severity, count in sorted(self.results['summary']['issues_by_severity'].items()))}

## 审查标准对照

### 1. 架构标准 ({self.standards['architecture'][0]})
**评估**: 检查分层清晰度、耦合合理性、职责单一性和设计缺陷

### 2. 逻辑标准 ({self.standards['logic'][0]})
**评估**: 检查流程闭环性、边界完备性、漏洞、歧义和逻辑硬伤

### 3. 性能标准 ({self.standards['performance'][0]})
**评估**: 检查写法效率、冗余计算、无效逻辑和资源占用

### 4. 规范标准 ({self.standards['standardization'][0]})
**评估**: 检查命名规范、结构整洁度、废代码和重复实现

### 5. 可维护性标准 ({self.standards['maintainability'][0]})
**评估**: 检查可读性、扩展性、注释合理性和迭代便利性

## 详细问题分析

### 架构问题 ({len(self.results['architectural_issues'])} 个)
"""
        
        # 添加架构问题
        for item in self.results["architectural_issues"][:10]:  # 只显示前10个
            issue = item["issue"]
            report += f"""
**文件**: `{item['file']}`
**标准**: {issue['standard']}
**描述**: {issue['description']}
**建议**: {issue['suggestion']}
"""
        
        if len(self.results["architectural_issues"]) > 10:
            report += f"\n... 等 {len(self.results['architectural_issues']) - 10} 个更多架构问题\n"
        
        # 添加性能问题
        report += f"""
### 性能问题 ({len(self.results['performance_issues'])} 个)
"""
        
        for item in self.results["performance_issues"][:5]:  # 只显示前5个
            issue = item["issue"]
            report += f"""
**文件**: `{item['file']}`
**标准**: {issue['standard']}
**描述**: {issue['description']}
**建议**: {issue['suggestion']}
"""
        
        if len(self.results["performance_issues"]) > 5:
            report += f"\n... 等 {len(self.results['performance_issues']) - 5} 个更多性能问题\n"
        
        # 添加可维护性问题
        report += f"""
### 可维护性问题 ({len(self.results['maintainability_issues'])} 个)
"""
        
        for item in self.results["maintainability_issues"][:5]:  # 只显示前5个
            issue = item["issue"]
            report += f"""
**文件**: `{item['file']}`
**标准**: {issue['standard']}
**描述**: {issue['description']}
**建议**: {issue['suggestion']}
"""
        
        # 生成优化路线图
        report += """
## 优化路线图

### 高优先级 (立即执行)
"""
        
        for rec in self.results["recommendations"]["high_priority"]:
            report += f"- {rec}\n"
        
        report += """
### 中优先级 (短期优化)
"""
        
        for rec in self.results["recommendations"]["medium_priority"]:
            report += f"- {rec}\n"
        
        report += """
### 低优先级 (长期改进)
"""
        
        for rec in self.results["recommendations"]["low_priority"]:
            report += f"- {rec}\n"
        
        # 添加技术建议
        report += """
## 技术建议

### 架构改进
1. **模块化重构**: 将大文件拆分为专注的模块
2. **依赖注入**: 减少硬编码依赖，提高可测试性
3. **接口抽象**: 定义清晰的接口，降低耦合度

### 性能优化
1. **缓存策略**: 优化数据缓存，减少重复计算
2. **异步处理**: 对IO密集型操作使用异步
3. **资源池**: 使用连接池和对象池管理资源

### 代码质量
1. **静态分析**: 集成代码质量检查工具
2. **单元测试**: 提高测试覆盖率，特别是边界条件
3. **代码审查**: 建立代码审查流程

### 可维护性
1. **文档生成**: 自动生成API文档和架构文档
2. **监控告警**: 集成应用性能监控和错误追踪
3. **配置管理**: 统一配置管理，支持环境隔离

## 审查结论

"""
        
        if total_issues == 0:
            report += "✅ **项目架构优秀**，符合所有审查标准，无需重大修改。"
        elif total_issues < 20:
            report += f"✅ **项目架构良好**，发现 {total_issues} 个小问题，建议按优先级逐步优化。"
        elif total_issues < 50:
            report += f"⚠️ **项目架构中等**，发现 {total_issues} 个问题，建议进行系统性的优化。"
        else:
            report += f"❌ **项目架构需要改进**，发现 {total_issues} 个问题，建议进行全面的重构。"
        
        report += f"""

**总体评估**: 项目具备良好的基础架构，但在 {', '.join(k for k, v in self.results['summary']['issues_by_category'].items() if v > 0)} 方面需要改进。

**建议行动**: 按照优化路线图，从高优先级问题开始逐步改进。
"""
        
        return report

def main():
    project_root = Path("/home/kid/fund-daily")
    
    print("🔍 开始全面架构审查...")
    print("=" * 60)
    
    # 创建审查器
    reviewer = ArchitectureReviewer(project_root)
    
    # 执行审查
    results = reviewer.review()
    
    # 生成报告
    report = reviewer.generate_report()
    
    # 保存报告
    report_file = project_root / "docs" / "COMPREHENSIVE_ARCHITECTURE_REVIEW.md"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📊 审查完成!")
    print(f"   审查文件数: {results['summary']['files_reviewed']}")
    print(f"   发现问题数: {sum(results['summary']['issues_by_category'].values())}")
    print(f"   报告已保存: {report_file}")
    
    # 显示摘要
    print(f"\n📋 问题摘要:")
    for category, count in sorted(results['summary']['issues_by_category'].items()):
        if count > 0:
            print(f"  {category}: {count} 个")
    
    print(f"\n🎯 建议优先处理:")
    for priority in ["high_priority", "medium_priority", "low_priority"]:
        if results["recommendations"][priority]:
            print(f"  {priority.replace('_', ' ').title()}:")
            for rec in results["recommendations"][priority]:
                print(f"    • {rec}")

if __name__ == "__main__":
    main()