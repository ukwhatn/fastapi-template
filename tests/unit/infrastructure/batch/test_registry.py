"""
タスクレジストリの単体テスト
"""

import pytest
from apscheduler.triggers.cron import CronTrigger

from app.infrastructure.batch.registry import TaskRegistry


class TestRegisterTask:
    """register()メソッドのテスト"""

    def test_register_task_successfully(self) -> None:
        """正常にタスク登録できること"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        registry.register(
            task_id="test_task",
            func=test_func,
            cron="0 3 * * *",
            description="Test task",
        )

        assert "test_task" in registry.tasks

    def test_register_task_stores_func(self) -> None:
        """funcが正しく保存されること"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        registry.register(
            task_id="test_task",
            func=test_func,
            cron="0 3 * * *",
        )

        assert registry.tasks["test_task"]["func"] == test_func

    def test_register_task_stores_trigger(self) -> None:
        """triggerが正しく生成・保存されること"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        registry.register(
            task_id="test_task",
            func=test_func,
            cron="0 3 * * *",
        )

        trigger = registry.tasks["test_task"]["trigger"]
        assert isinstance(trigger, CronTrigger)

    def test_register_task_stores_description(self) -> None:
        """descriptionが正しく保存されること"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        registry.register(
            task_id="test_task",
            func=test_func,
            cron="0 3 * * *",
            description="Test description",
        )

        assert registry.tasks["test_task"]["description"] == "Test description"

    def test_register_multiple_tasks(self) -> None:
        """複数タスクを登録できること"""
        registry = TaskRegistry()

        def func1() -> None:
            pass

        def func2() -> None:
            pass

        registry.register(task_id="task1", func=func1, cron="0 3 * * *")
        registry.register(task_id="task2", func=func2, cron="0 4 * * *")

        assert len(registry.tasks) == 2
        assert "task1" in registry.tasks
        assert "task2" in registry.tasks

    def test_register_task_without_description(self) -> None:
        """descriptionなしで登録できること"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        registry.register(
            task_id="test_task",
            func=test_func,
            cron="0 3 * * *",
        )

        assert registry.tasks["test_task"]["description"] == ""

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


class TestGetAllTasks:
    """get_all()メソッドのテスト"""

    def test_get_all_returns_empty_dict_initially(self) -> None:
        """初期状態で空辞書を返すこと"""
        registry = TaskRegistry()

        result = registry.get_all()

        assert result == {}

    def test_get_all_returns_registered_tasks(self) -> None:
        """登録したタスクを返すこと"""
        registry = TaskRegistry()

        def test_func() -> None:
            pass

        registry.register(
            task_id="test_task",
            func=test_func,
            cron="0 3 * * *",
            description="Test task",
        )

        result = registry.get_all()

        assert "test_task" in result
        assert result["test_task"]["func"] == test_func
        assert isinstance(result["test_task"]["trigger"], CronTrigger)
        assert result["test_task"]["description"] == "Test task"

    def test_get_all_returns_all_tasks(self) -> None:
        """複数のタスクをすべて返すこと"""
        registry = TaskRegistry()

        def func1() -> None:
            pass

        def func2() -> None:
            pass

        def func3() -> None:
            pass

        registry.register(task_id="task1", func=func1, cron="0 3 * * *")
        registry.register(task_id="task2", func=func2, cron="0 4 * * *")
        registry.register(task_id="task3", func=func3, cron="0 5 * * *")

        result = registry.get_all()

        assert len(result) == 3
        assert "task1" in result
        assert "task2" in result
        assert "task3" in result
