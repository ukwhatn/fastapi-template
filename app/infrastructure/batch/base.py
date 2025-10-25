"""バッチタスクの基底クラス"""

from abc import ABC, abstractmethod
from datetime import datetime

import sentry_sdk

from app.core.logging import get_logger


class BatchTask(ABC):
    """
    バッチタスクの基底クラス。

    すべてのバッチタスクはこのクラスを継承し、
    execute()メソッドを実装する必要がある。

    Example:
        >>> class MyTask(BatchTask):
        ...     def execute(self) -> None:
        ...         print("Task executed")
        ...
        >>> task = MyTask()
        >>> task.run()
    """

    def __init__(self) -> None:
        """バッチタスクを初期化する。"""
        self.logger = get_logger(__name__)

    @abstractmethod
    def execute(self) -> None:
        """
        タスクの実行処理。

        サブクラスで実装必須。
        ビジネスロジックをここに記述する。

        Raises:
            NotImplementedError: サブクラスで実装されていない場合
        """
        pass

    def on_success(self) -> None:
        """
        タスク成功時のフック。

        オプション。成功時に追加処理が必要な場合にオーバーライドする。
        """
        pass

    def on_failure(self, error: Exception) -> None:
        """
        タスク失敗時のフック。

        オプション。失敗時に追加処理が必要な場合にオーバーライドする。
        デフォルトではエラーログを出力する。

        Args:
            error: 発生した例外
        """
        self.logger.error(f"Task failed: {error}", exc_info=True)

    def run(self) -> None:
        """
        タスク実行のラッパー。

        execute()メソッドを実行し、以下の処理を自動で行う:
        - 実行開始/終了のログ出力
        - 実行時間の計測
        - エラーハンドリング
        - Sentryへのエラー送信
        - 成功/失敗フックの呼び出し

        Raises:
            Exception: execute()で発生した例外を再送出
        """
        start_time = datetime.now()
        task_name = self.__class__.__name__

        try:
            self.logger.info(f"[BATCH] {task_name} start")
            self.execute()
            self.on_success()
            elapsed = datetime.now() - start_time
            self.logger.info(f"[BATCH] {task_name} completed ({elapsed})")
        except Exception as e:
            self.on_failure(e)
            sentry_sdk.capture_exception(e)
            raise
