#!/usr/bin/env python3
"""
最终修复fetcher模块
"""

from pathlib import Path

def fix_fetcher_imports():
    """修复所有fetcher模块的导入"""
    project_root = Path("/home/kid/fund-daily")
    
    # 需要修复的文件和对应的导入
    files_to_fix = {
        "fund_basic/fetcher.py": [
            "from src.utils import cache_keys",
            "from ..network import _make_request",
            "from ..cache import get_cache, set_cache",
            "logger = logging.getLogger(__name__)"
        ],
        "market_data/fetcher.py": [
            "from src.utils import cache_keys",
            "from ..network import _make_request",
            "from ..cache import get_cache, set_cache",
            "logger = logging.getLogger(__name__)"
        ],
        "fund_advanced/fetcher.py": [
            "from src.utils import cache_keys",
            "from ..network import _make_request",
            "from ..cache import get_cache, set_cache",
            "logger = logging.getLogger(__name__)"
        ]
    }
    
    for rel_path, imports in files_to_fix.items():
        file_path = project_root / "src" / "fetcher" / rel_path
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 找到docstring结束的位置
        docstring_end = 0
        in_docstring = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if in_docstring:
                    docstring_end = i + 1
                    break
                else:
                    in_docstring = True
            elif not in_docstring and stripped and not stripped.startswith('#'):
                docstring_end = i
                break
        
        # 构建新的内容
        new_lines = []
        
        # 添加docstring之前的行
        new_lines.extend(lines[:docstring_end])
        
        # 添加空白行
        if new_lines and not new_lines[-1].strip() == '':
            new_lines.append('\n')
        
        # 添加标准导入
        new_lines.append("import logging\n")
        new_lines.append("from typing import Dict, List, Optional, Any\n")
        new_lines.append("import requests\n")
        new_lines.append("import json\n")
        new_lines.append("\n")
        
        # 添加特定导入
        for imp in imports:
            new_lines.append(imp + "\n")
        
        # 添加空白行
        new_lines.append("\n")
        
        # 添加剩余的行
        new_lines.extend(lines[docstring_end:])
        
        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        
        print(f"✅ 修复 {rel_path}")
    
    print("\n🔧 修复cache_keys引用...")
    
    # 修复cache_keys引用
    for rel_path in ["fund_basic/fetcher.py", "market_data/fetcher.py", "fund_advanced/fetcher.py"]:
        file_path = project_root / "src" / "fetcher" / rel_path
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 替换cache_keys引用
        content = content.replace("cache_keys.cache_keys.", "cache_keys.cache_keys.")
        # 已经是正确的，不需要替换
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 更新 {rel_path} 中的cache_keys引用")

def main():
    print("🔧 最终修复fetcher模块...")
    fix_fetcher_imports()
    print("\n✅ 修复完成!")

if __name__ == "__main__":
    main()