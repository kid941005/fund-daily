"""
Task Registry Module

Provides:
- TaskRegistry: Singleton registry for task handlers
- @register_task: Decorator to register task handlers
"""

import logging
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TaskMetadata:
    """Task handler metadata"""
    name: str
    description: str
    handler: Callable
    created_at: datetime
    max_concurrent: int = 1  # Max instances of this task type that can run concurrently
    timeout: int = 3600  # Default 1 hour timeout


class TaskRegistry:
    """
    Task Registry (Singleton)
    
    Manages task handler registration and lookup.
    """
    
    _instance: Optional["TaskRegistry"] = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._handlers: Dict[str, TaskMetadata] = {}
        self._task_types: Dict[str, str] = {}  # type_name -> type_value
    
    @classmethod
    def get_instance(cls) -> "TaskRegistry":
        """Get singleton instance"""
        return cls()
    
    def register(
        self,
        task_type: str,
        name: str,
        description: str = "",
        max_concurrent: int = 1,
        timeout: int = 3600
    ) -> Callable:
        """
        Register a task handler
        
        Can be used as a decorator.
        
        Args:
            task_type: Task type identifier (must match TaskType enum value)
            name: Human-readable task name
            description: Task description
            max_concurrent: Max concurrent instances allowed
            timeout: Task timeout in seconds
            
        Returns:
            Decorator function
        """
        def decorator(handler: Callable) -> Callable:
            metadata = TaskMetadata(
                name=name,
                description=description,
                handler=handler,
                created_at=datetime.utcnow(),
                max_concurrent=max_concurrent,
                timeout=timeout
            )
            self._handlers[task_type] = metadata
            self._task_types[handler.__name__] = task_type
            logger.info(f"✅ Task registered: {task_type} -> {handler.__name__}")
            return handler
        return decorator
    
    def get_handler(self, task_type: str) -> Optional[Callable]:
        """Get handler function for task type"""
        metadata = self._handlers.get(task_type)
        if metadata:
            return metadata.handler
        return None
    
    def get_metadata(self, task_type: str) -> Optional[TaskMetadata]:
        """Get metadata for task type"""
        return self._handlers.get(task_type)
    
    def get_all_types(self) -> Dict[str, TaskMetadata]:
        """Get all registered task types"""
        return dict(self._handlers)
    
    def is_registered(self, task_type: str) -> bool:
        """Check if task type is registered"""
        return task_type in self._handlers


def register_task(
    task_type: str,
    name: str = None,
    description: str = "",
    max_concurrent: int = 1,
    timeout: int = 3600
) -> Callable:
    """
    Decorator to register a task handler
    
    Usage:
        @register_task("fund_fetch", name="Fund Data Fetch", description="Fetch fund data from sources")
        def fund_fetch_handler(context: TaskContext):
            # ... task logic
            context.update_progress(0.5, "已完成50%")
            if context.check_cancelled():
                return None
            # ... more logic
            return result
    
    Args:
        task_type: Task type identifier
        name: Human-readable name (defaults to function name)
        description: Task description
        max_concurrent: Max concurrent instances
        timeout: Task timeout in seconds
    """
    def decorator(handler: Callable) -> Callable:
        registry = TaskRegistry.get_instance()
        registry.register(
            task_type=task_type,
            name=name or handler.__name__,
            description=description,
            max_concurrent=max_concurrent,
            timeout=timeout
        )(handler)
        return handler
    return decorator
