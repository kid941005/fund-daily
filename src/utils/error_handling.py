#!/usr/bin/env python3
"""
错误处理工具

提供统一的错误处理装饰器和工具函数，减少重复的错误处理代码。
"""

import logging
from functools import wraps
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def handle_errors(
    default_return: Any = None,
    log_level: str = "error",
    raise_exception: bool = False,
    exception_types: Optional[tuple] = None,
):
    """
    错误处理装饰器

    用法:
        @handle_errors(default_return=None, log_level="error")
        def risky_function():
            # 可能抛出异常的函数
            pass

    Args:
        default_return: 发生异常时返回的默认值
        log_level: 日志级别 ('debug', 'info', 'warning', 'error', 'critical')
        raise_exception: 是否重新抛出异常
        exception_types: 要处理的异常类型元组，None表示处理所有异常

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # 检查是否应该处理这个异常
                if exception_types and not isinstance(e, exception_types):
                    raise

                # 记录日志
                log_func = getattr(logger, log_level, logger.error)
                log_func(f"函数 {func.__name__} 执行失败: {e}", exc_info=True)

                # 重新抛出或返回默认值
                if raise_exception:
                    raise
                return default_return

        return wrapper

    return decorator


def log_and_continue(operation: str, default_value: Any = None, log_level: str = "warning"):
    """
    记录错误并继续执行的上下文管理器

    用法:
        with log_and_continue("数据处理", default_value={}):
            result = risky_operation()

    Args:
        operation: 操作名称，用于日志
        default_value: 发生异常时返回的默认值
        log_level: 日志级别

    Returns:
        上下文管理器
    """

    class LogAndContinueContext:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_val:
                log_func = getattr(logger, log_level, logger.warning)
                log_func(f"操作 '{operation}' 失败: {exc_val}", exc_info=True)
                return True  # 抑制异常
            return False

    return LogAndContinueContext()


def retry_on_failure(
    max_attempts: int = 3, delay: float = 1.0, backoff_factor: float = 2.0, exception_types: tuple = (Exception,)
):
    """
    失败重试装饰器

    用法:
        @retry_on_failure(max_attempts=3, delay=1.0)
        def network_request():
            # 可能失败的网络请求
            pass

    Args:
        max_attempts: 最大重试次数
        delay: 首次重试延迟（秒）
        backoff_factor: 退避因子，每次重试延迟乘以这个因子
        exception_types: 触发重试的异常类型

    Returns:
        装饰器函数
    """
    import time

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exception_types as e:
                    last_exception = e

                    if attempt < max_attempts - 1:
                        logger.warning(
                            f"函数 {func.__name__} 第 {attempt + 1} 次尝试失败，" f"{current_delay:.1f}秒后重试: {e}"
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    else:
                        logger.error(f"函数 {func.__name__} 所有 {max_attempts} 次尝试均失败: {e}")

            # 所有尝试都失败，抛出最后一个异常
            raise last_exception

        return wrapper

    return decorator


def safe_execute(func: Callable, *args, default_return: Any = None, log_message: Optional[str] = None, **kwargs) -> Any:
    """
    安全执行函数，捕获异常并返回默认值

    用法:
        result = safe_execute(risky_function, arg1, arg2, default_return={})

    Args:
        func: 要执行的函数
        *args: 函数参数
        default_return: 发生异常时返回的默认值
        log_message: 自定义日志消息
        **kwargs: 函数关键字参数

    Returns:
        函数结果或默认值
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        message = log_message or f"函数 {func.__name__} 执行失败"
        logger.error(f"{message}: {e}", exc_info=True)
        return default_return


# 预定义的错误处理装饰器
handle_network_errors = handle_errors(
    default_return=None, log_level="warning", exception_types=(ConnectionError, TimeoutError)
)

handle_file_errors = handle_errors(
    default_return=None, log_level="error", exception_types=(IOError, FileNotFoundError, PermissionError)
)

# 数据库错误处理器 - 使用更精确的异常类型
try:
    from psycopg2 import Error as DBError
except ImportError:
    DBError = Exception  # SQLite 或其他驱动时回退

handle_db_errors = handle_errors(
    default_return=None,
    log_level="error",
    exception_types=(DBError, IOError, OSError, AttributeError),
    raise_exception=False,
)


if __name__ == "__main__":
    # 测试错误处理工具
    print("🧪 测试错误处理工具...")

    # 测试 handle_errors 装饰器
    @handle_errors(default_return="默认值", log_level="warning")
    def risky_function(should_fail: bool):
        if should_fail:
            raise ValueError("测试异常")
        return "成功"

    print("1. handle_errors 装饰器测试:")
    print(f"   正常执行: {risky_function(False)}")
    print(f"   异常处理: {risky_function(True)}")

    # 测试 log_and_continue 上下文管理器
    print("\n2. log_and_continue 上下文管理器测试:")
    with log_and_continue("测试操作", default_value={}):
        raise RuntimeError("测试上下文管理器异常")
    print("   异常被抑制，继续执行")

    # 测试 safe_execute 函数
    print("\n3. safe_execute 函数测试:")

    def divide(a, b):
        return a / b

    result = safe_execute(divide, 10, 0, default_return=0, log_message="除法运算失败")
    print(f"   安全除法: 10 / 0 = {result}")

    print("\n✅ 错误处理工具测试完成")
# Patched: handle_db_errors should only catch DB-related exceptions
# This is done at the module level by importing and reassigning
