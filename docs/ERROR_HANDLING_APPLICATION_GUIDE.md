# 错误处理工具应用指南

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

- **db/users.py** - `create_user`: @handle_db_errors (数据库操作)
- **db/users.py** - `get_user_by_id`: @handle_db_errors (数据库操作)
- **db/holdings.py** - `get_holdings`: @handle_db_errors (数据库操作)
- **db/holdings.py** - `delete_holding`: @handle_db_errors (数据库操作)

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
