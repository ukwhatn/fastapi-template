"""バッチタスクの登録レジストリ"""

from collections.abc import Callable
from typing import TypedDict

from apscheduler.triggers.cron import CronTrigger


class TaskInfo(TypedDict):
    """タスク情報の型定義"""

    func: Callable[[], None]
    trigger: CronTrigger
    description: str


class TaskRegistry:
    """
    バッチタスクの登録レジストリ。

    タスクをスケジュール情報とともに登録し、
    スケジューラーが参照できるように管理する。

    Example:
        >>> from app.infrastructure.batch.registry import task_registry
        >>>
        >>> def my_task():
        ...     print("Task executed")
        >>>
        >>> task_registry.register(
        ...     task_id="my_task",
        ...     func=my_task,
        ...     cron="0 3 * * *",
        ...     description="My daily task"
        ... )
    """

    def __init__(self) -> None:
        """タスクレジストリを初期化する。"""
        self.tasks: dict[str, TaskInfo] = {}

    def register(
        self, task_id: str, func: Callable[[], None], cron: str, description: str = ""
    ) -> None:
        """
        タスクを登録する。

        Args:
            task_id: タスクの一意な識別子
            func: 実行する関数
            cron: cron形式のスケジュール (例: "0 3 * * *" = 毎日3時)
            description: タスクの説明（ログ出力用）

        Raises:
            ValueError: 無効なcron形式の場合

        Example:
            >>> def backup_db():
            ...     print("Backing up database")
            >>>
            >>> task_registry.register(
            ...     task_id="db_backup",
            ...     func=backup_db,
            ...     cron="0 3 * * *",
            ...     description="Daily database backup"
            ... )
        """
        self.tasks[task_id] = {
            "func": func,
            "trigger": CronTrigger.from_crontab(cron),
            "description": description,
        }

    def get_all(self) -> dict[str, TaskInfo]:
        """
        登録された全タスクを取得する。

        Returns:
            dict: タスクID をキーとした辞書。
                各値は func, trigger, description を含む辞書。
        """
        return self.tasks


# グローバルレジストリインスタンス
task_registry = TaskRegistry()
