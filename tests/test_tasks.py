"""
Tests for Background Task System
"""

import pytest
import time
import threading
from unittest.mock import MagicMock, patch
from datetime import datetime

# Add project root to path
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTaskStatus:
    """Test TaskStatus enum"""
    
    def test_task_status_values(self):
        from src.tasks.background import TaskStatus
        
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"
    
    def test_task_status_from_string(self):
        from src.tasks.background import TaskStatus
        
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("running") == TaskStatus.RUNNING
        assert TaskStatus("completed") == TaskStatus.COMPLETED


class TestTaskType:
    """Test TaskType enum"""
    
    def test_task_type_values(self):
        from src.tasks.background import TaskType
        
        assert TaskType.FUND_FETCH == "fund_fetch"
        assert TaskType.NAV_UPDATE == "nav_update"
        assert TaskType.SCORE_CALC == "score_calculation"
        assert TaskType.CACHE_WARM == "cache_warmup"
        assert TaskType.BATCH_IMPORT == "batch_import"


class TestTaskInfo:
    """Test TaskInfo model"""
    
    def test_task_info_creation(self):
        from src.tasks.background import TaskInfo, TaskType, TaskStatus
        
        task = TaskInfo(
            task_type=TaskType.FUND_FETCH,
            params={"codes": ["000001"]}
        )
        
        assert task.task_id is not None
        assert task.task_type == TaskType.FUND_FETCH
        assert task.status == TaskStatus.PENDING
        assert task.progress == 0.0
        assert task.params == {"codes": ["000001"]}
        assert task.created_at is not None
        assert task.started_at is None
        assert task.completed_at is None
    
    def test_task_info_default_values(self):
        from src.tasks.background import TaskInfo, TaskType
        
        task = TaskInfo(task_type=TaskType.NAV_UPDATE)
        
        assert task.task_id is not None
        assert task.status.value == "pending"
        assert task.progress == 0.0
        assert task.message == ""
        assert task.result is None
        assert task.error is None


class TestTaskContext:
    """Test TaskContext"""
    
    def test_task_context_creation(self):
        from src.tasks.background import TaskContext
        
        cancel_event = threading.Event()
        update_func = MagicMock()
        
        context = TaskContext(
            task_id="test-123",
            params={"codes": ["000001"]},
            cancel_event=cancel_event,
            update_progress_func=update_func
        )
        
        assert context.task_id == "test-123"
        assert context.params == {"codes": ["000001"]}
        assert context.check_cancelled() == False
        assert context.is_cancelled == False
    
    def test_task_context_cancelled(self):
        from src.tasks.background import TaskContext
        
        cancel_event = threading.Event()
        cancel_event.set()  # Cancel the task
        
        context = TaskContext(
            task_id="test-123",
            params={},
            cancel_event=cancel_event,
            update_progress_func=MagicMock()
        )
        
        assert context.check_cancelled() == True
        assert context.is_cancelled == True
    
    def test_task_context_update_progress(self):
        from src.tasks.background import TaskContext
        
        update_func = MagicMock()
        
        context = TaskContext(
            task_id="test-123",
            params={},
            cancel_event=threading.Event(),
            update_progress_func=update_func
        )
        
        context.update_progress(0.5, "已完成50%")
        
        update_func.assert_called_once_with(0.5, "已完成50%")


class TestTaskRegistry:
    """Test TaskRegistry"""
    
    def test_registry_singleton(self):
        from src.tasks.task_registry import TaskRegistry
        
        reg1 = TaskRegistry.get_instance()
        reg2 = TaskRegistry.get_instance()
        
        assert reg1 is reg2
    
    def test_register_task_decorator(self):
        from src.tasks.task_registry import TaskRegistry, register_task
        
        # Create a new registry for testing
        registry = TaskRegistry()
        registry._handlers.clear()
        
        @registry.register(
            task_type="test_task",
            name="Test Task",
            description="A test task"
        )
        def test_handler(context):
            return {"result": "success"}
        
        metadata = registry.get_metadata("test_task")
        
        assert metadata is not None
        assert metadata.name == "Test Task"
        assert metadata.description == "A test task"
        assert metadata.handler is test_handler
    
    def test_get_handler(self):
        from src.tasks.task_registry import TaskRegistry
        
        registry = TaskRegistry()
        
        def dummy_handler(ctx):
            pass
        
        registry._handlers["dummy"] = MagicMock(
            name="dummy",
            description="",
            handler=dummy_handler,
            created_at=datetime.utcnow(),
            max_concurrent=1,
            timeout=3600
        )
        
        handler = registry.get_handler("dummy")
        assert handler is dummy_handler
        
        # Non-existent handler
        assert registry.get_handler("nonexistent") is None


class TestBackgroundTaskManager:
    """Test BackgroundTaskManager"""
    
    def test_manager_singleton(self):
        from src.tasks.background import BackgroundTaskManager
        
        # Reset singleton for testing
        BackgroundTaskManager._instance = None
        
        mgr1 = BackgroundTaskManager()
        mgr2 = BackgroundTaskManager.get_instance()
        
        assert mgr1 is mgr2
    
    def test_submit_task_validation(self):
        from src.tasks.background import BackgroundTaskManager
        
        # Reset singleton
        BackgroundTaskManager._instance = None
        
        with patch.object(BackgroundTaskManager, '_init_redis'):
            mgr = BackgroundTaskManager()
            mgr._redis = None  # Use memory storage
            
            # Mock the executor
            mgr._executor = MagicMock()
            
            task_id = mgr.submit(
                task_type="fund_fetch",
                params={"codes": ["000001"]},
                user_id="user123"
            )
            
            assert task_id is not None
            assert len(task_id) == 36  # UUID length
    
    def test_get_task(self):
        from src.tasks.background import BackgroundTaskManager, TaskInfo
        
        # Reset singleton
        BackgroundTaskManager._instance = None
        
        with patch.object(BackgroundTaskManager, '_init_redis'):
            mgr = BackgroundTaskManager()
            mgr._redis = None
            
            # Create a task directly in memory
            mgr._memory_tasks = {}
            task = TaskInfo(
                task_type="fund_fetch",
                params={"codes": ["000001"]}
            )
            mgr._memory_tasks[task.task_id] = task
            
            retrieved = mgr.get_task(task.task_id)
            
            assert retrieved is not None
            assert retrieved.task_id == task.task_id
            assert retrieved.task_type == task.task_type
    
    def test_update_progress(self):
        from src.tasks.background import BackgroundTaskManager, TaskInfo
        
        # Reset singleton
        BackgroundTaskManager._instance = None
        
        with patch.object(BackgroundTaskManager, '_init_redis'):
            mgr = BackgroundTaskManager()
            mgr._redis = None
            
            # Create a task
            mgr._memory_tasks = {}
            task = TaskInfo(task_type="fund_fetch")
            mgr._memory_tasks[task.task_id] = task
            
            mgr.update_progress(task.task_id, 0.5, "已完成50%")
            
            updated = mgr.get_task(task.task_id)
            assert updated.progress == 0.5
            assert updated.message == "已完成50%"
    
    def test_cancel_task(self):
        from src.tasks.background import BackgroundTaskManager, TaskInfo, TaskStatus
        
        # Reset singleton
        BackgroundTaskManager._instance = None
        
        with patch.object(BackgroundTaskManager, '_init_redis'):
            mgr = BackgroundTaskManager()
            mgr._redis = None
            
            # Create a pending task
            mgr._memory_tasks = {}
            task = TaskInfo(task_type="fund_fetch")
            mgr._memory_tasks[task.task_id] = task
            
            # Cancel should work for pending task
            result = mgr.cancel_task(task.task_id)
            
            assert result == True
            
            cancelled = mgr.get_task(task.task_id)
            assert cancelled.status == TaskStatus.CANCELLED
    
    def test_list_tasks(self):
        from src.tasks.background import BackgroundTaskManager, TaskInfo, TaskStatus
        
        # Reset singleton
        BackgroundTaskManager._instance = None
        
        with patch.object(BackgroundTaskManager, '_init_redis'):
            mgr = BackgroundTaskManager()
            mgr._redis = None
            
            # Create multiple tasks
            mgr._memory_tasks = {}
            for i in range(5):
                task = TaskInfo(task_type="fund_fetch")
                if i % 2 == 0:
                    task.status = TaskStatus.COMPLETED
                mgr._memory_tasks[task.task_id] = task
            
            # List all
            all_tasks = mgr.list_tasks()
            assert len(all_tasks) == 5
            
            # Filter by status
            completed = mgr.list_tasks(status=TaskStatus.COMPLETED)
            assert len(completed) == 3  # indices 0, 2, 4


class TestTaskAPI:
    """Test Task API models"""
    
    def test_task_response_from_task_info(self):
        from src.tasks.background import TaskInfo, TaskType
        from src.tasks.api import TaskResponse
        
        task = TaskInfo(
            task_type=TaskType.FUND_FETCH,
            params={"codes": ["000001"]}
        )
        
        response = TaskResponse.from_task_info(task)
        
        assert response.task_id == task.task_id
        assert response.task_type == TaskType.FUND_FETCH
        assert response.status == "pending"
        assert response.progress == 0.0
    
    def test_task_submit_request(self):
        from src.tasks.api import TaskSubmitRequest
        
        request = TaskSubmitRequest(
            task_type="fund_fetch",
            params={"codes": ["000001"]},
            user_id="user123"
        )
        
        assert request.task_type == "fund_fetch"
        assert request.params == {"codes": ["000001"]}
        assert request.user_id == "user123"
    
    def test_task_list_response(self):
        from src.tasks.background import TaskInfo, TaskType
        from src.tasks.api import tasks_to_list_response
        
        tasks = [
            TaskInfo(task_type=TaskType.FUND_FETCH),
            TaskInfo(task_type=TaskType.NAV_UPDATE)
        ]
        
        stats = {
            "total_tasks": 2,
            "running_tasks": 0,
            "pending_tasks": 2,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "cancelled_tasks": 0,
            "max_concurrent": 5
        }
        
        response = tasks_to_list_response(tasks, stats)
        
        assert len(response.tasks) == 2
        assert response.total == 2
        assert response.stats == stats


class TestTaskHandlers:
    """Test task handlers are registered"""
    
    def test_handlers_registered(self):
        from src.tasks.background import TaskType
        from src.tasks.task_registry import TaskRegistry
        
        # Import handlers to register them
        from src.tasks import handlers  # noqa: F401
        
        registry = TaskRegistry()
        
        # All task types should be registered
        assert registry.is_registered(TaskType.FUND_FETCH)
        assert registry.is_registered(TaskType.NAV_UPDATE)
        assert registry.is_registered(TaskType.SCORE_CALC)
        assert registry.is_registered(TaskType.CACHE_WARM)
        assert registry.is_registered(TaskType.BATCH_IMPORT)
    
    def test_handler_execution(self):
        from src.tasks.background import TaskContext
        from src.tasks.handlers import fund_fetch_handler  # noqa: F401
        
        # Create a mock context
        cancel_event = threading.Event()
        progress_updates = []
        
        def mock_update(progress, message):
            progress_updates.append((progress, message))
        
        context = TaskContext(
            task_id="test-123",
            params={"codes": []},  # Empty to test "no funds" path
            cancel_event=cancel_event,
            update_progress_func=mock_update
        )
        
        result = fund_fetch_handler(context)
        
        # Should return empty result when no codes
        assert result["fetched"] == 0
        assert "No funds to fetch" in result["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
