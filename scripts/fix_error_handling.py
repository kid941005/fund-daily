#!/usr/bin/env python3
"""
自动修复错误处理脚本
将 jsonify({"error": str(e)}) 替换为 create_error_response()
"""

import os
import re
from pathlib import Path

def fix_error_handling_in_file(file_path: str):
    """修复单个文件中的错误处理"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 模式1: jsonify({"success": False, "error": str(e)}), 500
    pattern1 = r'jsonify\(\{"success":\s*False,\s*"error":\s*str\(e\)\}\)\s*,\s*500'
    replacement1 = 'create_error_response(ErrorCode.INTERNAL_ERROR, f"内部服务器错误: {str(e)}", http_status=500)'
    
    # 模式2: jsonify({"error": str(e)}), 500
    pattern2 = r'jsonify\(\{"error":\s*str\(e\)\}\)\s*,\s*500'
    replacement2 = 'create_error_response(ErrorCode.INTERNAL_ERROR, f"内部服务器错误: {str(e)}", http_status=500)'
    
    new_content = content
    changes = 0
    
    # 应用替换
    new_content, count1 = re.subn(pattern1, replacement1, new_content)
    changes += count1
    
    new_content, count2 = re.subn(pattern2, replacement2, new_content)
    changes += count2
    
    if changes > 0:
        # 检查是否导入了必要的模块
        if 'from src.error import' not in new_content and 'import src.error' not in new_content:
            # 在第一个from导入后添加
            import_match = re.search(r'^from\s+\S+\s+import', new_content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.end()
                new_content = new_content[:insert_pos] + '\nfrom src.error import ErrorCode, create_error_response' + new_content[insert_pos:]
            else:
                # 在文件开头添加
                new_content = 'from src.error import ErrorCode, create_error_response\n' + new_content
        
        # 写回文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"✅ 修复了 {file_path}: {changes} 处错误处理")
        return changes
    
    return 0

def main():
    project_root = "/home/kid/fund-daily"
    total_fixes = 0
    
    # 需要检查的文件列表
    files_to_check = [
        "web/api/endpoints/system.py",
        "web/api/endpoints/auth.py",
        "web/api/endpoints/external.py",
        "web/api/validation.py"
    ]
    
    print("🔧 开始修复错误处理...")
    
    for file_rel_path in files_to_check:
        file_path = Path(project_root) / file_rel_path
        if file_path.exists():
            fixes = fix_error_handling_in_file(str(file_path))
            total_fixes += fixes
        else:
            print(f"⚠️  文件不存在: {file_rel_path}")
    
    print(f"\n📊 修复完成!")
    print(f"   总共修复了 {total_fixes} 处错误处理")
    print(f"   统一使用了 create_error_response()")
    
    # 创建修复报告
    report = f"""# 错误处理统一修复报告

## 修复统计
- **修复文件数**: {len(files_to_check)}
- **修复错误处理数**: {total_fixes}
- **修复时间**: 2026-03-19

## 修复内容
将以下模式统一为 `create_error_response()`:
1. `jsonify({"success": False, "error": str(e)}), 500`
2. `jsonify({"error": str(e)}), 500`

## 新的错误处理标准
```python
from src.error import ErrorCode, create_error_response

# 使用示例
return create_error_response(
    ErrorCode.INTERNAL_ERROR,
    f"操作失败: {str(e)}",
    details={{"operation": "具体操作"}},
    http_status=500
)
```

## 好处
1. **一致性**: 所有错误响应格式统一
2. **可维护性**: 错误码集中管理
3. **可扩展性**: 易于添加新的错误类型
4. **类型安全**: 完整的类型提示

## 注意事项
1. 需要根据具体错误类型选择合适的 `ErrorCode`
2. 可以提供详细的 `details` 信息便于调试
3. 根据错误性质设置合适的 `http_status`
"""
    
    report_file = Path(project_root) / "docs" / "ERROR_HANDLING_REPORT.md"
    report_file.parent.mkdir(exist_ok=True)
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"📄 报告已保存: {report_file}")

if __name__ == "__main__":
    main()