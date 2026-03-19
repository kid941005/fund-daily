# 错误处理工具使用指南

## 概述

`src/utils/error_handling.py` 提供了统一的错误处理工具，旨在减少代码中重复的错误处理逻辑。目前项目中已有 140+ 处重复的错误处理代码，使用这些工具可以显著提高代码的可维护性和一致性。

## 可用工具

### 1. `@handle_errors` 装饰器

最常用的错误处理装饰器，可以应用到任何函数上。

```python
from src.utils.error_handling import handle_errors

@handle_errors(default_return=None, log_level="error")
def risky_function():
    # 可能抛出异常的函数
    return do_something()
```

**参数**:
- `default_return`: 发生异常时返回的默认值
- `log_level`: 日志级别 ('debug', 'info', 'warning', 'error', 'critical')
- `raise_exception`: 是否重新抛出异常（默认 False）
- `exception_types`: 要处理的异常类型元组，None 表示处理所有异常

### 2. 预定义装饰器

针对特定场景的预定义装饰器：

```python
from src.utils.error_handling import handle_network_errors, handle_file_errors, handle_db_errors

@handle_network_errors
def fetch_data_from_api():
    # 网络请求函数
    pass

@handle_file_errors  
def read_config_file():
    # 文件操作函数
    pass

@handle_db_errors
def query_database():
    # 数据库操作函数
    pass
```

### 3. `log_and_continue` 上下文管理器

用于抑制异常并记录日志的上下文管理器：

```python
from src.utils.error_handling import log_and_continue

with log_and_continue("数据处理", default_value={}):
    result = risky_operation()
```

### 4. `safe_execute` 函数

安全执行函数，捕获异常并返回默认值：

```python
from src.utils.error_handling import safe_execute

result = safe_execute(risky_function, arg1, arg2, default_return={})
```

### 5. `retry_on_failure` 装饰器

失败重试装饰器，适用于网络请求等可能临时失败的操作：

```python
from src.utils.error_handling import retry_on_failure

@retry_on_failure(max_attempts=3, delay=1.0)
def network_request():
    # 可能失败的网络请求
    pass
```

## 应用示例

### 网络请求函数

```python
from src.utils.error_handling import handle_network_errors

@handle_network_errors
def fetch_fund_data(fund_code: str) -> Dict:
    """获取基金数据"""
    # 网络请求逻辑
    return data
```

### 服务层函数

```python
from src.utils.error_handling import handle_errors

@handle_errors(default_return={"error": "服务暂时不可用"}, log_level="error")
def get_fund_data(self, fund_code: str) -> Dict:
    """获取基金数据（服务层）"""
    # 业务逻辑
    return result
```

### 分析函数

```python
from src.utils.error_handling import handle_errors

@handle_errors(default_return={"sentiment": "平稳", "score": 3, "error": True}, log_level="warning")
def get_market_sentiment() -> Dict:
    """获取市场情绪"""
    # 分析逻辑
    return sentiment_data
```

## 最佳实践

1. **选择合适的默认返回值**: 确保默认返回值与函数签名兼容
2. **适当的日志级别**: 
   - 网络错误: `warning`
   - 业务逻辑错误: `error`
   - 可恢复的错误: `info`
3. **保持向后兼容**: 确保添加错误处理后不影响现有调用方
4. **组合使用**: 可以在已有 try/except 的函数上添加装饰器，提供额外的保护层

## 已应用的关键函数

### 数据获取层
- `fetch_fund_nav_history` - 使用 `@handle_network_errors`

### 分析层
- `get_market_sentiment` - 使用 `@handle_errors`
- `get_commodity_sentiment` - 使用 `@handle_errors`
- `calculate_expected_return` - 使用 `@handle_errors`

### 评分层
- `format_score_report` - 使用 `@handle_errors`
- `apply_ranking_bonus` - 使用 `@handle_errors`

### 服务层
- `FundService.get_fund_data` - 使用 `@handle_errors`
- `FundService.get_market_data` - 使用 `@handle_errors`
- `FundService.calculate_holdings_advice` - 使用 `@handle_errors`
- `ScoreService.calculate_score` - 使用 `@handle_errors`

## 效益

1. **减少代码重复**: 减少 140+ 处重复的错误处理代码
2. **统一错误处理**: 所有函数使用相同的错误处理模式
3. **更好的可维护性**: 错误处理逻辑集中管理
4. **更清晰的业务逻辑**: 错误处理与业务逻辑分离
5. **一致的日志记录**: 所有错误以统一格式记录

## 后续工作

1. 继续将错误处理工具应用到更多函数
2. 创建错误处理配置，支持不同环境的差异化配置
3. 添加错误监控和告警集成
4. 完善错误恢复策略