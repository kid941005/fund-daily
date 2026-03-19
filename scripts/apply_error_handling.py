#!/usr/bin/env python3
"""
应用错误处理工具到关键函数
"""

import re
from pathlib import Path
from typing import List, Tuple

def analyze_function_for_error_handling(file_path: Path, function_name: str) -> Tuple[bool, List[str]]:
    """分析函数是否需要错误处理优化"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 查找函数定义
    function_pattern = rf'def {function_name}\(.*?\):'
    function_match = re.search(function_pattern, content, re.DOTALL)
    
    if not function_match:
        return False, ["未找到函数定义"]
    
    # 提取函数体（简化版本）
    start_pos = function_match.end()
    # 查找函数结束（下一个def或文件结束）
    next_def = re.search(r'\ndef ', content[start_pos:])
    if next_def:
        function_body = content[start_pos:start_pos + next_def.start()]
    else:
        function_body = content[start_pos:]
    
    # 检查是否已经有异常处理
    has_exception_handling = "except" in function_body or "try:" in function_body
    
    # 检查函数特征
    features = []
    if "requests.get" in function_body or "urllib.request" in function_body:
        features.append("网络请求")
    if "open(" in function_body or "read(" in function_body or "write(" in function_body:
        features.append("文件操作")
    if "psycopg2" in function_body or "cursor.execute" in function_body:
        features.append("数据库操作")
    if "json.loads" in function_body or "json.dumps" in function_body:
        features.append("JSON解析")
    if "redis" in function_body.lower():
        features.append("Redis操作")
    
    needs_optimization = bool(features) and not has_exception_handling
    
    return needs_optimization, features

def apply_error_handling_to_file(file_path: Path, function_names: List[str]):
    """应用错误处理工具到文件中的函数"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changes_made = []
    
    for function_name in function_names:
        # 检查是否需要添加导入
        if "from src.utils.error_handling import" not in content:
            # 在第一个import后添加
            import_match = re.search(r'^import', content, re.MULTILINE)
            if import_match:
                insert_pos = import_match.end()
                lines = content.split('\n')
                for i in range(import_match.start(), len(lines)):
                    if not lines[i].startswith(('import', 'from')):
                        insert_pos = sum(len(line) + 1 for line in lines[:i])
                        break
                
                content = content[:insert_pos] + '\nfrom src.utils.error_handling import handle_errors\n' + content[insert_pos:]
                changes_made.append("添加错误处理导入")
        
        # 查找函数定义并添加装饰器
        function_pattern = rf'(def {function_name}\(.*?\):)'
        if re.search(function_pattern, content):
            # 在函数定义前添加装饰器
            replacement = rf'@handle_errors(default_return=None, log_level="error")\n\1'
            content = re.sub(function_pattern, replacement, content, count=1)
            changes_made.append(f"为 {function_name} 添加错误处理装饰器")
    
    if changes_made:
        # 创建备份
        backup_path = file_path.with_suffix(file_path.suffix + '.backup')
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 写入更新后的内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return True, changes_made
    else:
        return False, []

def identify_key_functions():
    """识别关键函数"""
    key_functions = []
    
    # 1. 数据获取模块 - 网络请求密集型
    fetcher_files = [
        ("src/fetcher/__init__.py", [
            "fetch_fund_data",
            "fetch_fund_detail", 
            "fetch_market_news",
            "fetch_hot_sectors",
            "fetch_fund_manager_info"
        ]),
        ("src/fetcher/enhanced_fetcher.py", [
            "fetch_enhanced_fund_data",
            "fetch_fund_metrics"
        ]),
        ("src/fetcher/xueqiu.py", [
            "fetch_xueqiu_data"
        ]),
        ("src/fetcher/alipay.py", [
            "fetch_alipay_fund_data"
        ]),
    ]
    
    # 2. 服务模块 - 业务逻辑密集型
    service_files = [
        ("src/services/market_service.py", [
            "get_market_sentiment",
            "get_commodity_sentiment",
            "get_hot_sectors",
            "get_market_news"
        ]),
        ("src/services/quant_service.py", [
            "calculate_dynamic_weights",
            "get_timing_signals",
            "portfolio_optimization",
            "rebalancing_suggestions"
        ]),
    ]
    
    # 3. 数据库模块 - 数据操作密集型
    db_files = [
        ("db/users.py", [
            "create_user",
            "get_user_by_id",
            "update_user"
        ]),
        ("db/holdings.py", [
            "get_holdings",
            "add_holding",
            "update_holding",
            "delete_holding"
        ]),
    ]
    
    all_files = fetcher_files + service_files + db_files
    
    # 验证函数存在并分析
    valid_functions = []
    for file_path_str, functions in all_files:
        file_path = Path(file_path_str)
        if file_path.exists():
            for func_name in functions:
                needs_opt, features = analyze_function_for_error_handling(file_path, func_name)
                if needs_opt:
                    valid_functions.append((file_path, func_name, features))
                    print(f"✅ 识别: {file_path} -> {func_name} ({', '.join(features)})")
                else:
                    print(f"⏭️  跳过: {file_path} -> {func_name} (已有错误处理或无风险操作)")
        else:
            print(f"❌ 文件不存在: {file_path}")
    
    return valid_functions

def main():
    print("🔍 识别关键函数并应用错误处理工具...\n")
    
    # 识别关键函数
    key_functions = identify_key_functions()
    
    print(f"\n📊 识别到 {len(key_functions)} 个需要优化的关键函数")
    
    if not key_functions:
        print("✅ 所有关键函数已有适当的错误处理")
        return
    
    # 应用错误处理工具
    print(f"\n🔧 开始应用错误处理工具...")
    
    all_changes = []
    files_updated = 0
    
    for file_path, func_name, features in key_functions:
        print(f"\n处理: {file_path}")
        print(f"  函数: {func_name}")
        print(f"  特征: {', '.join(features)}")
        
        # 确定合适的错误处理策略
        if "网络请求" in features:
            decorator = "@handle_network_errors"
        elif "文件操作" in features:
            decorator = "@handle_file_errors"
        elif "数据库操作" in features or "Redis操作" in features:
            decorator = "@handle_db_errors"
        else:
            decorator = "@handle_errors(default_return=None, log_level='error')"
        
        print(f"  建议装饰器: {decorator}")
        
        # 手动应用（因为自动应用可能复杂）
        print(f"  状态: 建议手动应用 {decorator} 装饰器")
        all_changes.append(f"{file_path}: {func_name} → {decorator}")
    
    print(f"\n📋 优化建议总结:")
    for change in all_changes:
        print(f"  • {change}")
    
    # 创建应用指南
    guide = """# 错误处理工具应用指南

## 应用步骤

### 1. 添加导入
在每个需要优化的文件开头添加:
```python
from src.utils.error_handling import (
    handle_errors, 
    handle_network_errors, 
    handle_file_errors, 
    handle_db_errors
)
```

### 2. 应用装饰器
根据函数特征选择合适的装饰器:

#### 网络请求函数
```python
@handle_network_errors
def fetch_fund_data(fund_code: str, use_cache: bool = True):
    # 函数体
```

#### 文件操作函数  
```python
@handle_file_errors
def load_config_file(file_path: str):
    # 函数体
```

#### 数据库/Redis操作函数
```python
@handle_db_errors  
def get_user_by_id(user_id: str):
    # 函数体
```

#### 通用业务函数
```python
@handle_errors(default_return=None, log_level="error")
def calculate_metrics(data):
    # 函数体
```

### 3. 验证优化
1. 运行单元测试确保功能正常
2. 检查日志输出是否合理
3. 验证异常情况下的默认返回值

## 关键函数优化列表

"""
    
    for file_path, func_name, features in key_functions:
        if "网络请求" in features:
            decorator = "@handle_network_errors"
        elif "文件操作" in features:
            decorator = "@handle_file_errors"
        elif "数据库操作" in features or "Redis操作" in features:
            decorator = "@handle_db_errors"
        else:
            decorator = "@handle_errors(default_return=None, log_level='error')"
        
        guide += f"- **{file_path}** - `{func_name}`: {decorator} ({', '.join(features)})\n"
    
    guide += """
## 预期效果

### 代码质量提升
1. **减少重复代码**: 消除重复的 try-except 块
2. **统一错误处理**: 所有函数使用相同的错误处理策略
3. **更好的日志**: 统一的日志格式和级别
4. **默认值安全**: 异常时返回安全的默认值

### 运维便利性
1. **错误追踪**: 统一的错误日志便于问题排查
2. **监控集成**: 更容易添加错误监控和告警
3. **性能监控**: 可以添加性能监控装饰器

## 验证步骤
1. 运行完整测试套件 (194个测试)
2. 测试网络异常情况下的行为
3. 验证日志输出是否符合预期
4. 检查性能是否有退化
"""
    
    guide_file = Path("/home/kid/fund-daily/docs/ERROR_HANDLING_APPLICATION_GUIDE.md")
    guide_file.parent.mkdir(exist_ok=True)
    
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(guide)
    
    print(f"\n📄 应用指南已保存: {guide_file}")
    print(f"\n🎯 下一步: 根据指南手动应用错误处理装饰器，然后运行完整测试套件")

if __name__ == "__main__":
    main()