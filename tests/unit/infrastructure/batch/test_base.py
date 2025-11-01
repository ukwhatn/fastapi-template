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
    def test_run_logs_start_message(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """開始ログが出力されること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = SuccessfulTask()
        task.run()

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("[BATCH] SuccessfulTask start" in call for call in calls)

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_run_logs_completion_message(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """完了ログが出力されること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = SuccessfulTask()
        task.run()

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("[BATCH] SuccessfulTask completed" in call for call in calls), (
            f"Actual calls: {calls}"
        )

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

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_run_includes_elapsed_time_in_log(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """経過時間がログに含まれること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = SuccessfulTask()
        task.run()

        # 完了ログに経過時間が含まれることを確認
        completion_logs = [
            str(call)
            for call in mock_logger.info.call_args_list
            if "completed" in str(call)
        ]
        assert len(completion_logs) > 0
        # 経過時間は (0:00:00.xxxxx) のような形式で含まれる
        assert any("(" in log and ")" in log for log in completion_logs)


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


class TestBatchTaskHooks:
    """on_success/on_failureフック"""

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_on_success_can_be_overridden(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """on_success()をオーバーライドできること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = TaskWithCustomHooks()
        task.run()

        assert task.success_called is True

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_on_failure_logs_error_by_default(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """on_failure()がデフォルトでログを出力すること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = FailingTask()

        with pytest.raises(ValueError):
            task.run()

        # logger.error() が呼ばれたことを確認
        mock_logger.error.assert_called_once()
        call_args = str(mock_logger.error.call_args)
        assert "Task failed" in call_args

    @patch("app.infrastructure.batch.base.sentry_sdk")
    @patch("app.infrastructure.batch.base.get_logger")
    def test_on_failure_can_be_overridden(
        self, mock_get_logger: Mock, mock_sentry: Mock
    ) -> None:
        """on_failure()をオーバーライドできること"""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        task = TaskWithCustomHooks()

        # 失敗させるために execute をパッチ
        with patch.object(task, "execute", side_effect=ValueError("Test error")):
            with pytest.raises(ValueError):
                task.run()

        assert task.failure_called is True
