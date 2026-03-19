#!/usr/bin/env python3
"""
正确修复fetcher模块的导入问题
"""

from pathlib import Path

def fix_file_imports(file_path: Path):
    """修复文件的导入"""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 分析文件内容
    content = ''.join(lines)
    
    # 确定需要添加的导入
    imports_needed = []
    
    if "cache_keys." in content and "import cache_keys" not in content:
        imports_needed.append("from src.utils import cache_keys")
    
    if "get_cache(" in content and "from .cache import" not in content:
        imports_needed.append("from .cache import get_cache, set_cache")
    
    if "get_config()" in content and "from src.config import" not in content:
        imports_needed.append("from src.config import get_config")
    
    if "logger." in content and "logger = logging.getLogger" not in content:
        imports_needed.append("logger = logging.getLogger(__name__)")
    
    if not imports_needed:
        return False
    
    # 找到docstring结束的位置
    docstring_end = 0
    in_docstring = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        if stripped.startswith('"""') or stripped.startswith("'''"):
            if in_docstring:
                # 结束docstring
                docstring_end = i + 1
                break
            else:
                # 开始docstring
                in_docstring = True
        elif not in_docstring and stripped and not stripped.startswith('#'):
            # 第一个非注释非空行
            docstring_end = i
            break
    
    # 插入导入
    new_lines = lines[:docstring_end]
    
    # 确保有空白行
    if new_lines and not new_lines[-1].strip() == '':
        new_lines.append('\n')
    
    # 添加导入
    for imp in imports_needed:
        new_lines.append(imp + '\n')
    
    # 添加空白行
    new_lines.append('\n')
    
    # 添加剩余的行
    new_lines.extend(lines[docstring_end:])
    
    # 写入文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    return True

def main():
    project_root = Path("/home/kid/fund-daily")
    fetcher_dir = project_root / "src" / "fetcher"
    
    print("🔧 正确修复fetcher模块导入...")
    
    fixed_count = 0
    modules = ["cache", "network", "fund_basic", "market_data", "fund_advanced"]
    
    for module in modules:
        file_path = fetcher_dir / module / "fetcher.py"
        if file_path.exists():
            if fix_file_imports(file_path):
                print(f"✅ 修复 {module}/fetcher.py")
                fixed_count += 1
            else:
                print(f"✓ {module}/fetcher.py 无需修复")
    
    print(f"\n📊 修复完成: {fixed_count}/{len(modules)} 个文件已修复")

if __name__ == "__main__":
    main()