"""
タスクレジストリの単体テスト
"""

import pytest
from apscheduler.triggers.cron import CronTrigger

from app.infrastructure.batch.registry import TaskRegistry


class TestTaskRegistry:
    """TaskRegistryのテスト"""

    def test_register_and_get_task(self) -> None:
        """タスクを登録して取得できること"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        registry.register(
            task_id="test_task",
            func=test_func,
            cron="0 3 * * *",
            description="Test task",
        )

        tasks = registry.get_all()
        assert "test_task" in tasks
        assert tasks["test_task"]["func"] == test_func
        assert isinstance(tasks["test_task"]["trigger"], CronTrigger)
        assert tasks["test_task"]["description"] == "Test task"

    def test_register_multiple_tasks(self) -> None:
        """複数タスクを登録できること"""
        registry = TaskRegistry()

        def func1() -> None:
            pass

        def func2() -> None:
            pass

        registry.register(task_id="task1", func=func1, cron="0 3 * * *")
        registry.register(task_id="task2", func=func2, cron="0 4 * * *")

        tasks = registry.get_all()
        assert len(tasks) == 2
        assert "task1" in tasks
        assert "task2" in tasks

    def test_register_task_with_invalid_cron(self) -> None:
        """無効なcron形式でValueErrorが発生すること"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        with pytest.raises(ValueError):
            registry.register(
                task_id="test_task",
                func=test_func,
                cron="invalid",
            )
