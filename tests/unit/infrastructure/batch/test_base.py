"""
BatchTaskクラスの単体テスト
"""

from unittest.mock import Mock, patch

import pytest

from app.infrastructure.batch.base import BatchTask


class SuccessfulTask(BatchTask):
    """テスト用の成功するタスク"""

    def __init__(self) -> None:
        super().__init__()
        self.executed = False

    def execute(self) -> None:
        """タスクを実行する"""
        self.executed = True


class FailingTask(BatchTask):
    """テスト用の失敗するタスク"""

    def execute(self) -> None:
        """タスクを実行する（例外を発生させる）"""
        raise ValueError("Task execution failed")


class TaskWithCustomHooks(BatchTask):
    """テスト用のカスタムフック付きタスク"""

    def __init__(self) -> None:
        super().__init__()
        self.success_called = False
        self.failure_called = False

    def execute(self) -> None:
        """タスクを実行する"""
        pass

    def on_success(self) -> None:
        """成功時のカスタムフック"""
        self.success_called = True

    def on_failure(self, error: Exception) -> None:
        """失敗時のカスタムフック"""
        self.failure_called = True


class TestBatchTaskRun:
    """run()メソッドの実行フロー"""

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_run_executes_task_successfully(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """execute()が正常に実行されること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = SuccessfulTask()
        task.run()

        assert task.executed is True
        mock_sentry.capture_exception.assert_not_called()

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_run_calls_on_success_hook(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """on_success()が呼ばれること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = TaskWithCustomHooks()
        task.run()

        assert task.success_called is True


class TestBatchTaskError:
    """run()メソッドのエラーハンドリング"""

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_run_calls_on_failure_when_exception_occurs(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """例外時にon_failure()が呼ばれること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = TaskWithCustomHooks()

        # 失敗させるために execute をパッチ
        with patch.object(task, "execute", side_effect=ValueError("Test error")):
            with pytest.raises(ValueError):
                task.run()

        assert task.failure_called is True

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_run_sends_exception_to_sentry(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """Sentryに例外が送信されること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = FailingTask()

        with pytest.raises(ValueError):
            task.run()

        mock_sentry.capture_exception.assert_called_once()

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_run_reraises_exception(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """例外が再送出されること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = FailingTask()

        with pytest.raises(ValueError) as exc_info:
            task.run()

        assert "Task execution failed" in str(exc_info.value)
