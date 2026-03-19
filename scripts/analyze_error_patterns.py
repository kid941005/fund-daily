#!/usr/bin/env python3
"""
分析错误处理模式，识别重复的异常处理代码
"""

import re
from pathlib import Path
from typing import Dict, List, Set
from collections import Counter

def analyze_error_patterns(file_path: Path) -> List[Dict]:
    """分析单个文件的错误处理模式"""
    patterns = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找异常处理块
        # 模式: except Exception as e: ... return/raise ...
        except_pattern = r'except\s+(?:Exception|\w+Error)\s+as\s+e:\s*\n(.*?)(?=\n\S|\Z)'
        
        for match in re.finditer(except_pattern, content, re.DOTALL):
            exception_block = match.group(1)
            lines = [line.strip() for line in exception_block.split('\n') if line.strip()]
            
            if lines:
                pattern = {
                    "file": str(file_path),
                    "line": content[:match.start()].count('\n') + 1,
                    "code": '\n'.join(lines[:3]),  # 只取前3行作为模式
                    "full_block": exception_block[:200]  # 截断长块
                }
                patterns.append(pattern)
        
        return patterns
        
    except Exception as e:
        print(f"分析文件 {file_path} 时出错: {e}")
        return []

def categorize_pattern(pattern_code: str) -> str:
    """对错误处理模式进行分类"""
    pattern_code_lower = pattern_code.lower()
    
    # 分类规则
    if "logger.error" in pattern_code_lower and "jsonify" in pattern_code_lower:
        return "API错误响应"
    elif "logger.error" in pattern_code_lower and "return" in pattern_code_lower:
        return "日志+返回错误"
    elif "logger.error" in pattern_code_lower:
        return "仅记录日志"
    elif "raise" in pattern_code_lower:
        return "重新抛出异常"
    elif "return" in pattern_code_lower and "error" in pattern_code_lower:
        return "返回错误对象"
    elif "print" in pattern_code_lower:
        return "打印错误"
    else:
        return "其他"

def main():
    project_root = Path("/home/kid/fund-daily")
    
    # 分析生产代码文件
    python_files = []
    for py_file in project_root.rglob("*.py"):
        if any(exclude in str(py_file) for exclude in ["node_modules", "__pycache__", "test", ".backup", "scripts"]):
            continue
        python_files.append(py_file)
    
    print(f"🔍 分析 {len(python_files)} 个Python文件的错误处理模式...\n")
    
    all_patterns = []
    for file_path in python_files[:50]:  # 限制分析前50个文件
        patterns = analyze_error_patterns(file_path)
        all_patterns.extend(patterns)
    
    # 分类统计
    categories = Counter()
    pattern_counter = Counter()
    
    for pattern in all_patterns:
        category = categorize_pattern(pattern["code"])
        categories[category] += 1
        pattern_counter[pattern["code"][:100]] += 1  # 使用前100字符作为模式标识
    
    print("📊 错误处理模式分类统计:")
    for category, count in categories.most_common():
        print(f"  {category}: {count} 处")
    
    print(f"\n📈 总共发现 {len(all_patterns)} 个异常处理块")
    
    # 找出最常见的重复模式
    print(f"\n🔍 最常见的错误处理模式 (前5):")
    for pattern_text, count in pattern_counter.most_common(5):
        if count > 1:  # 只显示重复的模式
            print(f"\n出现 {count} 次:")
            print(f"  模式: {pattern_text[:80]}...")
            # 找出使用这个模式的文件
            files = []
            for pattern in all_patterns:
                if pattern["code"][:100] == pattern_text[:100]:
                    rel_path = Path(pattern["file"]).relative_to(project_root)
                    files.append(f"{rel_path}:{pattern['line']}")
            
            if files:
                print(f"  位置: {', '.join(files[:3])}")
                if len(files) > 3:
                    print(f"    等 {len(files) - 3} 个更多位置")
    
    # 生成优化建议
    print(f"\n💡 优化建议:")
    
    if categories["API错误响应"] > 10:
        print("1. ✅ 已实施: 统一API错误响应 (create_error_response)")
    
    if categories["日志+返回错误"] > 20:
        print("2. 🔄 建议: 创建通用错误处理装饰器")
        print("   例如: @handle_errors(default_return=None)")
    
    if categories["仅记录日志"] > 30:
        print("3. 🔄 建议: 创建日志记录工具函数")
        print("   例如: log_and_continue(operation, exception)")
    
    # 找出具体的重复代码示例
    print(f"\n📝 重复代码示例分析:")
    
    # 查找相似的错误处理块
    similar_patterns = {}
    for pattern in all_patterns:
        key = pattern["code"].replace('"', "'").replace(' ', '')[:50]
        if key not in similar_patterns:
            similar_patterns[key] = []
        similar_patterns[key].append(pattern)
    
    # 显示重复最多的模式
    duplicate_count = 0
    for key, patterns in similar_patterns.items():
        if len(patterns) > 2:  # 至少重复3次
            duplicate_count += 1
            if duplicate_count <= 3:  # 只显示前3个
                print(f"\n模式重复 {len(patterns)} 次:")
                sample = patterns[0]
                print(f"  示例代码: {sample['code'][:100]}...")
                print(f"  示例位置: {Path(sample['file']).relative_to(project_root)}:{sample['line']}")
    
    if duplicate_count > 0:
        print(f"\n🎯 发现 {duplicate_count} 个重复的错误处理模式，建议提取为工具函数")
    else:
        print("✅ 未发现明显的重复错误处理模式")
    
    # 生成报告
    report = f"""# 错误处理模式分析报告

## 分析概要
- **分析时间**: 2026-03-19
- **分析文件数**: {len(python_files[:50])}
- **发现异常处理块**: {len(all_patterns)}
- **重复模式数**: {duplicate_count}

## 模式分类统计
{chr(10).join(f"- **{category}**: {count} 处" for category, count in categories.most_common())}

## 最常见的重复模式

### 1. API错误响应模式
**出现次数**: {categories.get('API错误响应', 0)}
**典型代码**:
```python
except Exception as e:
    logger.error(f"操作失败: {{e}}")
    return jsonify({{"success": False, "error": str(e)}}), 500
```

**优化状态**: ✅ 已通过 `create_error_response()` 统一

### 2. 日志+返回错误模式
**出现次数**: {categories.get('日志+返回错误', 0)}
**典型代码**:
```python
except Exception as e:
    logger.error(f"数据处理失败: {{e}}")
    return None  # 或返回默认值
```

**优化建议**: 创建 `@handle_errors` 装饰器

### 3. 仅记录日志模式
**出现次数**: {categories.get('仅记录日志', 0)}
**典型代码**:
```python
except Exception as e:
    logger.error(f"网络请求失败: {{e}}")
    # 继续执行或使用默认值
```

**优化建议**: 创建 `log_and_continue()` 工具函数

## 具体重复模式示例

### 重复最多的模式
"""

    # 添加具体的重复模式
    duplicate_examples = []
    for key, patterns in similar_patterns.items():
        if len(patterns) > 2:
            sample = patterns[0]
            example = f"""
**模式**: 出现 {len(patterns)} 次
```python
{sample['code'][:150]}...
```
**位置示例**: {Path(sample['file']).relative_to(project_root)}:{sample['line']}
"""
            duplicate_examples.append(example)
    
    if duplicate_examples:
        report += '\n'.join(duplicate_examples[:3])
    else:
        report += "\n未发现明显的重复模式。"
    
    report += """

## 优化路线图

### 阶段1: 创建通用错误处理工具 (高优先级)
1. **错误处理装饰器**: `@handle_errors(default_return=None, log_level='error')`
2. **日志记录工具**: `log_and_continue(operation, exception, default_value)`
3. **API响应工具**: 扩展 `create_error_response()` 支持更多场景

### 阶段2: 迁移重复模式 (中优先级)
1. 识别并替换最常见的重复模式
2. 保持向后兼容性
3. 更新相关测试

### 阶段3: 监控和优化 (低优先级)
1. 监控错误处理性能
2. 收集错误处理统计
3. 持续优化错误处理策略

## 预期收益
1. **代码简洁性**: 减少重复的错误处理代码
2. **一致性**: 统一的错误处理策略
3. **可维护性**: 错误处理逻辑集中管理
4. **可测试性**: 更容易测试错误处理逻辑
5. **监控能力**: 更好的错误统计和监控
"""
    
    report_file = project_root / "docs" / "ERROR_PATTERN_ANALYSIS.md"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📄 分析报告已保存: {report_file}")

if __name__ == "__main__":
    main()