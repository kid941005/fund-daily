"""
Background Task Core Module

Provides:
- BackgroundTaskManager: Singleton task manager
- TaskInfo: Pydantic model for task information
- TaskStatus: Task status enum
- TaskType: Task type enum
"""

import json
import uuid
import logging
import threading
import asyncio
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field, asdict
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    """Task type enumeration"""

    FUND_FETCH = "fund_fetch"  # 基金数据抓取
    NAV_UPDATE = "nav_update"  # 净值更新
    SCORE_CALC = "score_calculation"  # 评分计算
    CACHE_WARM = "cache_warmup"  # 缓存预热
    BATCH_IMPORT = "batch_import"  # 批量导入


class TaskStatus(str, Enum):
    """Task status enumeration"""

    PENDING = "pending"  # 等待执行
    RUNNING = "running"  # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


class TaskInfo(BaseModel):
    """Task information model"""

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0  # 0.0 to 1.0
    message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)

    class Config:
        use_enum_values = True


class BackgroundTaskManager:
    """
    Background Task Manager (Singleton)

    Features:
    - Task persistence in Redis
    - Progress tracking
    - Task cancellation
    - Concurrent task limiting
    """

    _instance: Optional["BackgroundTaskManager"] = None
    _lock = threading.Lock()

    # Default settings
    DEFAULT_MAX_CONCURRENT = 5
    DEFAULT_TASK_TTL = 86400  # 24 hours
    TASK_KEY_PREFIX = "task:"
    TASK_LIST_KEY = "tasks:list"

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, max_concurrent: int = None):
        """Initialize the task manager"""
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._initialized = True
        self._max_concurrent = max_concurrent or self.DEFAULT_MAX_CONCURRENT
        self._task_ttl = self.DEFAULT_TASK_TTL
        self._executor = ThreadPoolExecutor(max_workers=self._max_concurrent)
        self._running_tasks: Dict[str, threading.Event] = {}
        self._running_lock = threading.Lock()

        # Import registry
        from .task_registry import TaskRegistry

        self._registry = TaskRegistry.get_instance()

        # Initialize Redis
        self._redis = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection"""
        try:
            import redis
            from src.config import get_config

            config = get_config().redis
            self._redis = redis.Redis(
                host=config.host,
                port=config.port,
                db=config.db,
                password=config.password,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=3,
            )
            self._redis.ping()
            logger.info(f"✅ Task Manager Redis 连接成功: {config.host}:{config.port}")
        except ImportError:
            logger.warning("⚠️ redis-py 未安装，任务状态将存储在内存中")
            self._redis = None
        except Exception as e:
            logger.warning(f"⚠️ Task Manager Redis 连接失败: {e}，使用内存存储")
            self._redis = None

    @classmethod
    def get_instance(cls) -> "BackgroundTaskManager":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _get_redis(self):
        """Get Redis client, reconnect if needed"""
        if self._redis is None:
            self._init_redis()
        return self._redis

    def _task_key(self, task_id: str) -> str:
        """Get Redis key for task"""
        return f"{self.TASK_KEY_PREFIX}{task_id}"

    def _save_task(self, task_info: TaskInfo) -> bool:
        """Save task to Redis or memory"""
        redis = self._get_redis()

        if redis is None:
            # Memory fallback - store in instance dict
            if not hasattr(self, "_memory_tasks"):
                self._memory_tasks: Dict[str, TaskInfo] = {}
            self._memory_tasks[task_info.task_id] = task_info
            return True

        try:
            data = task_info.model_dump(mode="json")
            # Convert datetime to ISO format
            for dt_field in ["created_at", "started_at", "completed_at"]:
                if data.get(dt_field):
                    if isinstance(data[dt_field], datetime):
                        data[dt_field] = data[dt_field].isoformat()

            redis.setex(self._task_key(task_info.task_id), self._task_ttl, json.dumps(data))

            # Add to task list for listing
            redis.sadd(self.TASK_LIST_KEY, task_info.task_id)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to save task {task_info.task_id}: {e}")
            # Fallback to memory
            if not hasattr(self, "_memory_tasks"):
                self._memory_tasks = {}
            self._memory_tasks[task_info.task_id] = task_info
            return False

    def _load_task(self, task_id: str) -> Optional[TaskInfo]:
        """Load task from Redis or memory"""
        redis = self._get_redis()

        # Try memory first
        if hasattr(self, "_memory_tasks") and task_id in self._memory_tasks:
            return self._memory_tasks[task_id]

        if redis is None:
            return None

        try:
            data = redis.get(self._task_key(task_id))
            if data:
                task_dict = json.loads(data)
                # Parse datetime fields
                for dt_field in ["created_at", "started_at", "completed_at"]:
                    if task_dict.get(dt_field):
                        task_dict[dt_field] = datetime.fromisoformat(task_dict[dt_field])
                return TaskInfo(**task_dict)
        except Exception as e:
            logger.error(f"❌ Failed to load task {task_id}: {e}")

        return None

    def _get_all_task_ids(self) -> List[str]:
        """Get all task IDs"""
        redis = self._get_redis()

        if redis is None:
            if hasattr(self, "_memory_tasks"):
                return list(self._memory_tasks.keys())
            return []

        try:
            return list(redis.smembers(self.TASK_LIST_KEY))
        except Exception as e:
            logger.error(f"❌ Failed to get task list: {e}")
            return []

    def submit(self, task_type: str, params: Dict[str, Any] = None, user_id: str = None) -> str:
        """
        Submit a new task

        Args:
            task_type: Type of task (from TaskType enum)
            params: Task parameters
            user_id: Optional user ID for tracking

        Returns:
            task_id: Unique task identifier
        """
        task_id = str(uuid.uuid4())
        params = params or {}

        if user_id:
            params["user_id"] = user_id

        # Create task info
        task_info = TaskInfo(task_id=task_id, task_type=task_type, status=TaskStatus.PENDING, params=params)

        # Save task
        self._save_task(task_info)

        # Get task handler
        handler = self._registry.get_handler(task_type)
        if handler is None:
            task_info.status = TaskStatus.FAILED
            task_info.error = f"Unknown task type: {task_type}"
            task_info.completed_at = datetime.utcnow()
            self._save_task(task_info)
            return task_id

        # Submit to executor
        self._executor.submit(self._run_task, task_id)

        logger.info(f"📝 Task submitted: {task_id} ({task_type})")
        return task_id

    def _run_task(self, task_id: str):
        """Run a task in a separate thread"""
        task_info = self._load_task(task_id)
        if task_info is None:
            logger.error(f"❌ Task not found: {task_id}")
            return

        # Set running status
        cancel_event = threading.Event()
        with self._running_lock:
            self._running_tasks[task_id] = cancel_event

        try:
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.utcnow()
            self._save_task(task_info)

            logger.info(f"🚀 Task started: {task_id}")

            # Get handler
            handler = self._registry.get_handler(task_info.task_type)
            if handler is None:
                raise ValueError(f"Handler not found for task type: {task_info.task_type}")

            # Create task context
            task_context = TaskContext(
                task_id=task_id,
                params=task_info.params,
                cancel_event=cancel_event,
                update_progress_func=lambda p, m: self.update_progress(task_id, p, m),
            )

            # Run handler
            result = handler(task_context)

            # Check if cancelled
            if cancel_event.is_set():
                task_info.status = TaskStatus.CANCELLED
                logger.info(f"⏹️ Task cancelled: {task_id}")
            else:
                task_info.status = TaskStatus.COMPLETED
                task_info.result = result
                logger.info(f"✅ Task completed: {task_id}")

            task_info.completed_at = datetime.utcnow()

        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error = str(e)
            task_info.completed_at = datetime.utcnow()
            logger.error(f"❌ Task failed: {task_id} - {e}")

        finally:
            # Remove from running tasks
            with self._running_lock:
                self._running_tasks.pop(task_id, None)

            self._save_task(task_info)

    def update_progress(self, task_id: str, progress: float, message: str = ""):
        """
        Update task progress

        Args:
            task_id: Task identifier
            progress: Progress value (0.0 to 1.0)
            message: Progress message
        """
        task_info = self._load_task(task_id)
        if task_info:
            task_info.progress = max(0.0, min(1.0, progress))
            if message:
                task_info.message = message
            self._save_task(task_info)

    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information"""
        return self._load_task(task_id)

    def list_tasks(
        self, status: TaskStatus = None, task_type: str = None, limit: int = 100, offset: int = 0
    ) -> List[TaskInfo]:
        """List tasks with optional filters"""
        task_ids = self._get_all_task_ids()
        tasks = []

        for task_id in task_ids:
            task_info = self._load_task(task_id)
            if task_info is None:
                continue

            # Apply filters
            if status and task_info.status != status:
                continue
            if task_type and task_info.task_type != task_type:
                continue

            tasks.append(task_info)

        # Sort by created_at descending
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Apply pagination
        return tasks[offset : offset + limit]

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task

        Args:
            task_id: Task identifier

        Returns:
            True if task was cancelled, False otherwise
        """
        with self._running_lock:
            if task_id in self._running_tasks:
                self._running_tasks[task_id].set()
                logger.info(f"⏹️ Cancel signal sent to task: {task_id}")
                return True

        # Task might not be running yet (still pending)
        task_info = self._load_task(task_id)
        if task_info and task_info.status == TaskStatus.PENDING:
            task_info.status = TaskStatus.CANCELLED
            task_info.completed_at = datetime.utcnow()
            self._save_task(task_info)
            return True

        return False

    def is_cancelled(self, task_id: str) -> bool:
        """Check if task has been cancelled"""
        with self._running_lock:
            if task_id in self._running_tasks:
                return self._running_tasks[task_id].is_set()
        return False

    def get_running_count(self) -> int:
        """Get number of currently running tasks"""
        return len(self._running_tasks)

    def get_stats(self) -> Dict[str, Any]:
        """Get task manager statistics"""
        all_tasks = self.list_tasks(limit=10000)

        stats = {
            "total_tasks": len(all_tasks),
            "running_tasks": len([t for t in all_tasks if t.status == TaskStatus.RUNNING]),
            "pending_tasks": len([t for t in all_tasks if t.status == TaskStatus.PENDING]),
            "completed_tasks": len([t for t in all_tasks if t.status == TaskStatus.COMPLETED]),
            "failed_tasks": len([t for t in all_tasks if t.status == TaskStatus.FAILED]),
            "cancelled_tasks": len([t for t in all_tasks if t.status == TaskStatus.CANCELLED]),
            "max_concurrent": self._max_concurrent,
            "executor_workers": self._executor._max_workers,
        }

        return stats


class TaskContext:
    """
    Task execution context

    Passed to task handlers to provide:
    - Task ID
    - Parameters
    - Cancellation check
    - Progress updates
    """

    def __init__(
        self,
        task_id: str,
        params: Dict[str, Any],
        cancel_event: threading.Event,
        update_progress_func: Callable[[float, str], None],
    ):
        self.task_id = task_id
        self.params = params
        self._cancel_event = cancel_event
        self._update_progress = update_progress_func
        self._current_progress = 0.0

    def update_progress(self, progress: float, message: str = ""):
        """Update task progress"""
        self._current_progress = progress
        self._update_progress(progress, message)

    def check_cancelled(self) -> bool:
        """Check if task has been cancelled"""
        return self._cancel_event.is_set()

    @property
    def is_cancelled(self) -> bool:
        """Check if task has been cancelled (alias)"""
        return self.check_cancelled()


def get_task_manager() -> BackgroundTaskManager:
    """Get the global task manager instance"""
    return BackgroundTaskManager.get_instance()
