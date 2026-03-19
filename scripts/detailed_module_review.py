#!/usr/bin/env python3
"""
详细模块审查：逐文件、逐逻辑、逐模块审查
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

class ModuleReviewer:
    """模块审查器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.review_results = defaultdict(list)
    
    def review_module(self, module_path: str, standards: Dict) -> Dict:
        """审查单个模块"""
        file_path = self.project_root / module_path
        
        if not file_path.exists():
            return {"error": f"文件不存在: {module_path}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content)
            
            review = {
                "module": module_path,
                "lines": len(content.splitlines()),
                "issues": [],
                "metrics": self._calculate_metrics(tree, content),
                "structure": self._analyze_structure(tree)
            }
            
            # 按标准审查
            self._review_by_standards(tree, content, review, standards)
            
            return review
            
        except Exception as e:
            return {
                "module": module_path,
                "error": str(e),
                "issues": [{
                    "category": "system",
                    "severity": "high",
                    "description": f"解析文件失败: {e}",
                    "suggestion": "检查文件语法错误"
                }]
            }
    
    def _calculate_metrics(self, tree: ast.AST, content: str) -> Dict:
        """计算代码指标"""
        # 基本统计
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        
        # 函数复杂度
        func_complexities = []
        for func in functions:
            # 简单复杂度：嵌套深度 + 分支数量
            complexity = self._calculate_function_complexity(func)
            func_complexities.append(complexity)
        
        avg_complexity = sum(func_complexities) / len(func_complexities) if func_complexities else 0
        
        # 注释比例
        comment_lines = len(re.findall(r'^\s*#', content, re.MULTILINE))
        total_lines = len(content.splitlines())
        comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
        
        return {
            "function_count": len(functions),
            "class_count": len(classes),
            "import_count": len(imports),
            "avg_function_complexity": avg_complexity,
            "comment_ratio": comment_ratio,
            "long_functions": len([f for f in functions if (f.end_lineno or f.lineno) - f.lineno > 50]),
            "large_classes": len([c for c in classes if len(c.body) > 10])
        }
    
    def _calculate_function_complexity(self, func: ast.FunctionDef) -> int:
        """计算函数复杂度"""
        complexity = 0
        
        for node in ast.walk(func):
            # 嵌套结构增加复杂度
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                complexity += 1
            # 嵌套的if/for/while再增加复杂度
            if isinstance(node, (ast.If, ast.For, ast.While)):
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.If, ast.For, ast.While, ast.Try)):
                        complexity += 1
        
        return complexity
    
    def _analyze_structure(self, tree: ast.AST) -> Dict:
        """分析代码结构"""
        structure = {
            "functions": [],
            "classes": [],
            "imports": []
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                structure["functions"].append({
                    "name": node.name,
                    "lines": (node.end_lineno or node.lineno) - node.lineno,
                    "args": len(node.args.args),
                    "has_return": any(isinstance(n, ast.Return) for n in ast.walk(node))
                })
            elif isinstance(node, ast.ClassDef):
                structure["classes"].append({
                    "name": node.name,
                    "methods": len([n for n in node.body if isinstance(n, ast.FunctionDef)]),
                    "bases": [ast.unparse(base) for base in node.bases]
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    structure["imports"].append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                names = ", ".join(alias.name for alias in node.names)
                structure["imports"].append(f"from {module} import {names}")
        
        return structure
    
    def _review_by_standards(self, tree: ast.AST, content: str, review: Dict, standards: Dict):
        """按标准审查"""
        issues = []
        
        # 1. 架构标准审查
        issues.extend(self._review_architecture(tree, content, standards["architecture"]))
        
        # 2. 逻辑标准审查
        issues.extend(self._review_logic(tree, content, standards["logic"]))
        
        # 3. 性能标准审查
        issues.extend(self._review_performance(tree, content, standards["performance"]))
        
        # 4. 规范标准审查
        issues.extend(self._review_standardization(tree, content, standards["standardization"]))
        
        # 5. 可维护性标准审查
        issues.extend(self._review_maintainability(tree, content, standards["maintainability"]))
        
        review["issues"].extend(issues)
    
    def _review_architecture(self, tree: ast.AST, content: str, standards: List[str]) -> List[Dict]:
        """架构审查"""
        issues = []
        
        # 检查职责单一性
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        if len(functions) > 20 and "职责单一" in standards:
            issues.append({
                "category": "architecture",
                "severity": "medium",
                "standard": "职责单一",
                "description": f"模块包含 {len(functions)} 个函数，可能职责过多",
                "suggestion": "考虑拆分为多个专注的模块"
            })
        
        # 检查耦合度
        imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        if len(imports) > 15 and "耦合合理" in standards:
            issues.append({
                "category": "architecture",
                "severity": "medium",
                "standard": "耦合合理",
                "description": f"模块依赖 {len(imports)} 个外部模块，耦合度较高",
                "suggestion": "减少外部依赖，提高模块独立性"
            })
        
        return issues
    
    def _review_logic(self, tree: ast.AST, content: str, standards: List[str]) -> List[Dict]:
        """逻辑审查"""
        issues = []
        
        # 检查异常处理
        if "无漏洞" in standards:
            # 查找空的except语句
            if "except:" in content or "except Exception:" in content:
                issues.append({
                    "category": "logic",
                    "severity": "high",
                    "standard": "无漏洞",
                    "description": "使用空的或过于宽泛的except语句，可能隐藏错误",
                    "suggestion": "使用具体的异常类型，记录异常信息"
                })
        
        # 检查边界条件
        if "边界完备" in standards:
            # 检查除法操作
            if "/" in content and "ZeroDivisionError" not in content:
                # 简单检查，可能有误报
                issues.append({
                    "category": "logic",
                    "severity": "medium",
                    "standard": "边界完备",
                    "description": "可能存在除零风险，未处理ZeroDivisionError",
                    "suggestion": "添加除零检查或异常处理"
                })
        
        return issues
    
    def _review_performance(self, tree: ast.AST, content: str, standards: List[str]) -> List[Dict]:
        """性能审查"""
        issues = []
        
        # 检查重复计算
        if "无冗余计算" in standards:
            # 检查循环中的重复函数调用
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if "for " in line or "while " in line:
                    # 简单检查：循环中是否有明显的重复调用
                    for j in range(i+1, min(i+5, len(lines))):
                        next_line = lines[j]
                        if "re.compile(" in next_line:
                            issues.append({
                                "category": "performance",
                                "severity": "medium",
                                "standard": "无冗余计算",
                                "description": f"第{i+1}行循环中编译正则表达式，应缓存结果",
                                "suggestion": "将正则表达式编译移到循环外部"
                            })
                            break
        
        # 检查资源释放
        if "资源占用最优" in standards:
            if "open(" in content and "with open" not in content:
                issues.append({
                    "category": "performance",
                    "severity": "medium",
                    "standard": "资源占用最优",
                    "description": "文件操作未使用with语句，可能未正确释放资源",
                    "suggestion": "使用with语句确保资源正确释放"
                })
        
        return issues
    
    def _review_standardization(self, tree: ast.AST, content: str, standards: List[str]) -> List[Dict]:
        """规范审查"""
        issues = []
        
        # 检查命名规范
        if "命名规范" in standards:
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                        issues.append({
                            "category": "standardization",
                            "severity": "low",
                            "standard": "命名规范",
                            "description": f"函数命名不符合蛇形命名法: {node.name}",
                            "suggestion": "使用蛇形命名法，如: get_user_data"
                        })
                
                elif isinstance(node, ast.ClassDef):
                    if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                        issues.append({
                            "category": "standardization",
                            "severity": "low",
                            "standard": "命名规范",
                            "description": f"类命名不符合帕斯卡命名法: {node.name}",
                            "suggestion": "使用帕斯卡命名法，如: UserService"
                        })
        
        # 检查代码结构
        if "结构整洁" in standards:
            lines = len(content.splitlines())
            if lines > 500:
                issues.append({
                    "category": "standardization",
                    "severity": "medium",
                    "standard": "结构整洁",
                    "description": f"文件过大 ({lines} 行)，结构可能混乱",
                    "suggestion": "拆分为多个小文件，每个文件专注单一职责"
                })
        
        return issues
    
    def _review_maintainability(self, tree: ast.AST, content: str, standards: List[str]) -> List[Dict]:
        """可维护性审查"""
        issues = []
        
        # 检查注释
        if "注释合理" in standards:
            comment_lines = len(re.findall(r'^\s*#', content, re.MULTILINE))
            total_lines = len(content.splitlines())
            comment_ratio = comment_lines / total_lines if total_lines > 0 else 0
            
            if comment_ratio < 0.05 and total_lines > 100:
                issues.append({
                    "category": "maintainability",
                    "severity": "low",
                    "standard": "注释合理",
                    "description": f"注释比例低 ({comment_ratio:.1%})，可读性可能受影响",
                    "suggestion": "为复杂逻辑和公共接口添加注释"
                })
        
        # 检查类型提示
        if "易于迭代" in standards:
            functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            functions_with_hints = 0
            
            for func in functions:
                # 检查是否有返回类型提示
                if func.returns:
                    functions_with_hints += 1
                # 检查参数类型提示
                elif any(arg.annotation for arg in func.args.args):
                    functions_with_hints += 1
            
            if functions and functions_with_hints / len(functions) < 0.3:
                issues.append({
                    "category": "maintainability",
                    "severity": "low",
                    "standard": "易于迭代",
                    "description": f"类型提示使用率低 ({functions_with_hints}/{len(functions)})",
                    "suggestion": "为函数添加类型提示，提高代码可读性和工具支持"
                })
        
        return issues

def main():
    project_root = Path("/home/kid/fund-daily")
    
    # 审查标准
    standards = {
        "architecture": ["分层清晰", "耦合合理", "职责单一", "无设计缺陷"],
        "logic": ["流程闭环", "边界完备", "无漏洞", "无歧义", "无逻辑硬伤"],
        "performance": ["写法高效", "无冗余计算", "无无效逻辑", "资源占用最优"],
        "standardization": ["命名规范", "结构整洁", "无废代码", "无重复实现"],
        "maintainability": ["可读性强", "扩展性好", "注释合理", "易于迭代"]
    }
    
    # 需要审查的关键模块
    key_modules = [
        "src/fetcher/__init__.py",      # 数据获取核心
        "web/app.py",                   # 主应用入口
        "src/config.py",                # 配置管理
        "db/pool.py",                   # 数据库连接池
        "src/services/quant_service.py", # 量化服务
        "web/api/rate_limiter.py",      # 速率限制器
        "src/utils/error_handling.py",  # 错误处理工具
        "src/utils/cache_keys.py",      # 缓存键工具
    ]
    
    print("🔍 开始关键模块详细审查...")
    print("=" * 60)
    
    reviewer = ModuleReviewer(project_root)
    all_results = []
    
    for module_path in key_modules:
        print(f"\n📄 审查: {module_path}")
        
        review = reviewer.review_module(module_path, standards)
        
        if "error" in review:
            print(f"   ❌ 错误: {review['error']}")
            continue
        
        # 显示摘要
        print(f"   文件大小: {review['lines']} 行")
        print(f"   函数数量: {review['metrics']['function_count']}")
        print(f"   类数量: {review['metrics']['class_count']}")
        print(f"   问题数量: {len(review['issues'])}")
        
        # 显示关键问题
        high_issues = [i for i in review['issues'] if i['severity'] == 'high']
        if high_issues:
            print(f"   ⚠️ 高优先级问题: {len(high_issues)} 个")
            for issue in high_issues[:2]:
                print(f"     • {issue['description']}")
        
        all_results.append(review)
    
    # 生成综合报告
    print(f"\n📊 审查完成!")
    print(f"   审查模块数: {len(all_results)}")
    
    total_issues = sum(len(r['issues']) for r in all_results)
    high_issues = sum(1 for r in all_results for i in r['issues'] if i['severity'] == 'high')
    
    print(f"   发现问题总数: {total_issues}")
    print(f"   高优先级问题: {high_issues}")
    
    # 按类别统计
    categories = defaultdict(int)
    for result in all_results:
        for issue in result['issues']:
            categories[issue['category']] += 1
    
    print(f"\n📋 问题分类:")
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count} 个")

if __name__ == "__main__":
    main()