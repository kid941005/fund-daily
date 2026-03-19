#!/usr/bin/env python3
"""
修复fetcher模块的导入问题
"""

import re
from pathlib import Path

def fix_imports_in_file(file_path: Path):
    """修复单个文件的导入"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # 检查缺少的导入
    imports_to_add = []
    
    # 检查需要导入的模块
    if "cache_keys." in content and "import cache_keys" not in content:
        imports_to_add.append("from src.utils import cache_keys")
    
    if "get_cache(" in content and "from .cache import get_cache" not in content:
        imports_to_add.append("from .cache import get_cache, set_cache")
    
    if "get_config()" in content and "from src.config import get_config" not in content:
        imports_to_add.append("from src.config import get_config")
    
    if "logger." in content and "logger = logging.getLogger(__name__)" not in content:
        imports_to_add.append("logger = logging.getLogger(__name__)")
    
    # 添加导入
    if imports_to_add:
        # 找到import语句后的位置
        import_section_end = 0
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            if line.strip() and not line.strip().startswith(('import', 'from', '#', '"', "'")):
                import_section_end = i
                break
        
        # 在import部分后添加新的导入
        new_lines = lines[:import_section_end] + [''] + imports_to_add + [''] + lines[import_section_end:]
        content = '\n'.join(new_lines)
        
        print(f"✅ 修复 {file_path.name}: 添加了 {len(imports_to_add)} 个导入")
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    project_root = Path("/home/kid/fund-daily")
    fetcher_dir = project_root / "src" / "fetcher"
    
    print("🔧 修复fetcher模块导入问题...")
    
    # 修复所有fetcher模块
    fixed_files = []
    
    for subdir in ["cache", "network", "fund_basic", "market_data", "fund_advanced"]:
        fetcher_file = fetcher_dir / subdir / "fetcher.py"
        if fetcher_file.exists():
            if fix_imports_in_file(fetcher_file):
                fixed_files.append(fetcher_file.name)
    
    print(f"\n📊 修复完成:")
    print(f"   修复的文件: {len(fixed_files)} 个")
    for file in fixed_files:
        print(f"   - {file}")

if __name__ == "__main__":
    main()