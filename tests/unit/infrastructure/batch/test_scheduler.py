"""
スケジューラー管理の単体テスト
"""

from datetime import datetime
from unittest.mock import Mock, patch

from apscheduler.triggers.cron import CronTrigger


class TestCreateScheduler:
    """create_scheduler()のテスト"""

    @patch("app.infrastructure.batch.scheduler.task_registry")
    @patch("app.infrastructure.batch.scheduler.BackgroundScheduler")
    @patch("app.infrastructure.batch.scheduler.logger")
    def test_create_scheduler_returns_scheduler_instance(
        self,
        mock_logger: Mock,
        mock_scheduler_class: Mock,
        mock_task_registry: Mock,
    ) -> None:
        """BackgroundSchedulerインスタンスを返すこと"""
        from app.infrastructure.batch.scheduler import create_scheduler

        mock_task_registry.get_all.return_value = {}

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        result = create_scheduler()

        assert result == mock_scheduler
        mock_scheduler_class.assert_called_once()

    @patch("app.infrastructure.batch.scheduler.task_registry")
    @patch("app.infrastructure.batch.scheduler.BackgroundScheduler")
    @patch("app.infrastructure.batch.scheduler.logger")
    def test_create_scheduler_registers_tasks(
        self,
        mock_logger: Mock,
        mock_scheduler_class: Mock,
        mock_task_registry: Mock,
    ) -> None:
        """タスクが登録されること"""
        from app.infrastructure.batch.scheduler import create_scheduler

        # テスト用のタスク情報
        def test_func() -> None:
            pass

        test_trigger = CronTrigger.from_crontab("0 3 * * *")
        mock_task_registry.get_all.return_value = {
            "test_task": {
                "func": test_func,
                "trigger": test_trigger,
                "description": "Test task",
            }
        }

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        create_scheduler()

        # add_jobが呼ばれたことを確認
        mock_scheduler.add_job.assert_called_once()
        call_args = mock_scheduler.add_job.call_args
        # funcは位置引数、その他はキーワード引数
        assert call_args[0][0] == test_func  # 第1位置引数
        assert call_args[1]["trigger"] == test_trigger
        assert call_args[1]["id"] == "test_task"
        assert call_args[1]["name"] == "Test task"

    @patch("app.infrastructure.batch.scheduler.task_registry")
    @patch("app.infrastructure.batch.scheduler.BackgroundScheduler")
    @patch("app.infrastructure.batch.scheduler.logger")
    def test_create_scheduler_logs_task_registration(
        self,
        mock_logger: Mock,
        mock_scheduler_class: Mock,
        mock_task_registry: Mock,
    ) -> None:
        """タスク登録ログが出力されること"""
        from app.infrastructure.batch.scheduler import create_scheduler

        # テスト用のタスク情報
        def test_func() -> None:
            pass

        test_trigger = CronTrigger.from_crontab("0 3 * * *")
        mock_task_registry.get_all.return_value = {
            "test_task": {
                "func": test_func,
                "trigger": test_trigger,
                "description": "Test task",
            }
        }

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        create_scheduler()

        # ログが出力されたことを確認
        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Registered task: test_task" in call for call in calls)

    @patch("app.infrastructure.batch.scheduler.task_registry")
    @patch("app.infrastructure.batch.scheduler.BackgroundScheduler")
    @patch("app.infrastructure.batch.scheduler.logger")
    def test_create_scheduler_with_no_tasks(
        self,
        mock_logger: Mock,
        mock_scheduler_class: Mock,
        mock_task_registry: Mock,
    ) -> None:
        """タスクが0個の場合でもスケジューラーを返すこと"""
        from app.infrastructure.batch.scheduler import create_scheduler

        mock_task_registry.get_all.return_value = {}

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        result = create_scheduler()

        assert result == mock_scheduler
        mock_scheduler.add_job.assert_not_called()


class TestStartScheduler:
    """start_scheduler()のテスト"""

    @patch("app.infrastructure.batch.scheduler.logger")
    def test_start_scheduler_starts_scheduler(self, mock_logger: Mock) -> None:
        """scheduler.start()が呼ばれること"""
        from app.infrastructure.batch.scheduler import start_scheduler

        mock_scheduler = Mock()
        mock_scheduler.get_jobs.return_value = []

        start_scheduler(mock_scheduler)

        mock_scheduler.start.assert_called_once()

    @patch("app.infrastructure.batch.scheduler.logger")
    def test_start_scheduler_logs_startup(self, mock_logger: Mock) -> None:
        """起動ログが出力されること"""
        from app.infrastructure.batch.scheduler import start_scheduler

        mock_scheduler = Mock()
        mock_scheduler.get_jobs.return_value = []

        start_scheduler(mock_scheduler)

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("[SCHEDULER] Started" in call for call in calls)

    @patch("app.infrastructure.batch.scheduler.logger")
    def test_start_scheduler_logs_next_run_times(self, mock_logger: Mock) -> None:
        """各ジョブの次回実行時刻がログに出力されること"""
        from app.infrastructure.batch.scheduler import start_scheduler

        # モックジョブを作成
        mock_job = Mock()
        mock_job.id = "test_job"
        mock_job.next_run_time = datetime(2025, 1, 1, 3, 0, 0)

        mock_scheduler = Mock()
        mock_scheduler.get_jobs.return_value = [mock_job]

        start_scheduler(mock_scheduler)

        # 次回実行時刻のログが出力されたことを確認
        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("test_job next run:" in call for call in calls)


class TestStopScheduler:
    """stop_scheduler()のテスト"""

    @patch("app.infrastructure.batch.scheduler.logger")
    def test_stop_scheduler_shuts_down_scheduler(self, mock_logger: Mock) -> None:
        """scheduler.shutdown()が呼ばれること"""
        from app.infrastructure.batch.scheduler import stop_scheduler

        mock_scheduler = Mock()

        stop_scheduler(mock_scheduler)

        mock_scheduler.shutdown.assert_called_once()

    @patch("app.infrastructure.batch.scheduler.logger")
    def test_stop_scheduler_logs_shutdown(self, mock_logger: Mock) -> None:
        """停止ログが出力されること"""
        from app.infrastructure.batch.scheduler import stop_scheduler

        mock_scheduler = Mock()

        stop_scheduler(mock_scheduler)

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("[SCHEDULER] Stopped" in call for call in calls)
