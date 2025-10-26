"""バッチスケジューラー管理"""

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.logging import get_logger

from .registry import task_registry

logger = get_logger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """
    スケジューラーを作成し、登録されたタスクをセットアップする。

    Returns:
        BackgroundScheduler: タスクが登録されたスケジューラー

    Example:
        >>> scheduler = create_scheduler()
        >>> start_scheduler(scheduler)
    """
    scheduler = BackgroundScheduler()

    for task_id, task_info in task_registry.get_all().items():
        scheduler.add_job(
            task_info["func"],
            trigger=task_info["trigger"],
            id=task_id,
            name=task_info["description"] or task_id,
        )
        logger.info(f"[SCHEDULER] Registered task: {task_id}")

    return scheduler


def start_scheduler(scheduler: BackgroundScheduler) -> None:
    """
    スケジューラーを起動し、次回実行時刻をログに出力する。

    Args:
        scheduler: 起動するスケジューラー

    Example:
        >>> scheduler = create_scheduler()
        >>> start_scheduler(scheduler)
    """
    scheduler.start()
    logger.info("[SCHEDULER] Started")

    # 次回実行時刻をログ出力
    for job in scheduler.get_jobs():
        logger.info(f"[SCHEDULER] {job.id} next run: {job.next_run_time}")


def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    """
    スケジューラーを停止する。

    Args:
        scheduler: 停止するスケジューラー

    Example:
        >>> stop_scheduler(scheduler)
    """
    scheduler.shutdown()
    logger.info("[SCHEDULER] Stopped")
