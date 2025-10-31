# Batch System

本テンプレートのバッチ処理システム。APSchedulerベース、タスク自動登録、アプリケーションライフサイクル統合を提供。

## アーキテクチャ

### コンポーネント構成

```
┌────────────────────────────────────────────────────┐
│ app/main.py (lifespan)                             │
│  - スケジューラー作成・起動                        │
│  - タスク自動登録                                  │
│  - シャットダウン時に停止                          │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ app/infrastructure/batch/scheduler.py              │
│  - create_scheduler()                              │
│  - start_scheduler()                               │
│  - stop_scheduler()                                │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ app/infrastructure/batch/registry.py               │
│  - TaskRegistry (シングルトン)                     │
│  - register() / get_all_tasks()                    │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ app/infrastructure/batch/base.py                   │
│  - BaseTask (抽象基底クラス)                       │
│    - name, description, schedule                   │
│    - run() (抽象メソッド)                          │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ app/infrastructure/batch/tasks/                    │
│  - backup.py (BackupTask)                          │
│  - cleanup_sessions.py (CleanupSessionsTask)       │
│  - ... (カスタムタスク)                            │
└────────────────────────────────────────────────────┘
```

## 基底クラス

### BaseTask

**場所**: `app/infrastructure/batch/base.py`

```python
from abc import ABC, abstractmethod

class BaseTask(ABC):
    """
    バッチタスクの抽象基底クラス

    Attributes:
        name: タスク名
        description: タスクの説明
        schedule: Cronスケジュール式
    """
    name: str
    description: str
    schedule: str

    @abstractmethod
    def run(self) -> None:
        """
        タスクを実行

        このメソッドを実装してタスクのロジックを記述
        """
        pass
```

**実装例**:
```python
from app.infrastructure.batch.base import BaseTask
from app.core.logging import get_logger

logger = get_logger(__name__)

class MyCustomTask(BaseTask):
    name = "my_custom_task"
    description = "カスタムタスクの説明"
    schedule = "0 * * * *"  # 毎時0分に実行

    def run(self) -> None:
        logger.info(f"Running {self.name}")
        # タスクのロジック
        logger.info(f"Completed {self.name}")
```

## タスクレジストリ

### TaskRegistry

**場所**: `app/infrastructure/batch/registry.py`

```python
class TaskRegistry:
    """
    タスクレジストリ（シングルトン）

    全てのバッチタスクを管理
    """
    _instance: Optional["TaskRegistry"] = None
    _tasks: list[type[BaseTask]] = []

    @classmethod
    def register(cls, task_class: type[BaseTask]) -> None:
        """タスクを登録"""
        cls._tasks.append(task_class)
        logger.info(f"Registered task: {task_class.name}")

    @classmethod
    def get_all_tasks(cls) -> list[type[BaseTask]]:
        """全タスクを取得"""
        return cls._tasks
```

**自動登録メカニズム**:

タスククラスを定義するだけで自動的に登録される。

```python
# app/infrastructure/batch/tasks/my_task.py
from app.infrastructure.batch.base import BaseTask
from app.infrastructure.batch.registry import TaskRegistry

class MyTask(BaseTask):
    name = "my_task"
    description = "My custom task"
    schedule = "0 2 * * *"

    def run(self) -> None:
        # タスクのロジック
        pass

# 自動登録
TaskRegistry.register(MyTask)
```

**タスク自動登録の仕組み** (`app/main.py`):
```python
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # ...
    from .infrastructure.batch import tasks  # タスク自動登録  # noqa: F401
    # tasksパッケージをインポートすることで、
    # tasks/配下の全モジュールが実行され、TaskRegistry.register()が呼ばれる
```

## スケジューラー

### Scheduler Functions

**場所**: `app/infrastructure/batch/scheduler.py`

#### create_scheduler

```python
def create_scheduler() -> BackgroundScheduler:
    """
    スケジューラーを作成

    Returns:
        BackgroundScheduler: 作成されたスケジューラー
    """
    scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={
            "coalesce": False,  # 遅延実行されたジョブをまとめない
            "max_instances": 1,  # 同時実行数1
        }
    )

    # 全タスクをスケジューラーに登録
    for task_class in TaskRegistry.get_all_tasks():
        task = task_class()
        scheduler.add_job(
            func=task.run,
            trigger=CronTrigger.from_crontab(task.schedule),
            id=task.name,
            name=task.description,
            replace_existing=True,
        )
        logger.info(f"Scheduled task: {task.name} ({task.schedule})")

    return scheduler
```

#### start_scheduler

```python
def start_scheduler(scheduler: BackgroundScheduler) -> None:
    """
    スケジューラーを起動

    Args:
        scheduler: 起動するスケジューラー
    """
    scheduler.start()
    logger.info("Scheduler started")
```

#### stop_scheduler

```python
def stop_scheduler(scheduler: BackgroundScheduler) -> None:
    """
    スケジューラーを停止

    Args:
        scheduler: 停止するスケジューラー
    """
    scheduler.shutdown(wait=True)
    logger.info("Scheduler stopped")
```

## ライフサイクル統合

**場所**: `app/main.py`

```python
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時
    from .infrastructure.batch.scheduler import (
        create_scheduler,
        start_scheduler,
        stop_scheduler,
    )
    from .infrastructure.batch import tasks  # タスク自動登録  # noqa: F401

    scheduler = create_scheduler()
    app.state.scheduler = scheduler
    start_scheduler(scheduler)

    yield

    # シャットダウン時
    stop_scheduler(scheduler)
```

**特徴**:
- アプリケーション起動時にスケジューラーを起動
- アプリケーション停止時にスケジューラーを停止
- app.state.schedulerに保存（必要に応じてアクセス可能）

## 定義済みタスク

### BackupTask

**場所**: `app/infrastructure/batch/tasks/backup.py`

```python
class BackupTask(BaseTask):
    """定期バックアップタスク"""
    name = "backup"
    description = "データベースバックアップを作成"

    @property
    def schedule(self) -> str:
        """スケジュールを設定から取得"""
        settings = get_settings()
        return settings.BACKUP_CRON

    def run(self) -> None:
        from app.infrastructure.database.backup.core import create_backup
        from pathlib import Path
        from datetime import datetime, timedelta

        # バックアップ作成
        backup_path = create_backup(output_dir=Path("./backups"))
        logger.info(f"Backup created: {backup_path}")

        # 古いバックアップを削除
        settings = get_settings()
        retention_days = settings.BACKUP_RETENTION_DAYS
        cutoff = datetime.now() - timedelta(days=retention_days)

        for backup_file in Path("./backups").glob("backup_*.backup.gz"):
            if backup_file.stat().st_mtime < cutoff.timestamp():
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file}")
```

**設定** (`.env`):
```bash
BACKUP_CRON="0 2 * * *"        # 毎日午前2時に実行
BACKUP_RETENTION_DAYS=7        # 7日間保持
```

### CleanupSessionsTask（実装例）

```python
# app/infrastructure/batch/tasks/cleanup_sessions.py
from app.infrastructure.batch.base import BaseTask
from app.infrastructure.batch.registry import TaskRegistry
from app.infrastructure.database import get_db
from app.infrastructure.repositories.session_repository import SessionService
from app.core.logging import get_logger

logger = get_logger(__name__)

class CleanupSessionsTask(BaseTask):
    """期限切れセッション削除タスク"""
    name = "cleanup_sessions"
    description = "期限切れセッションを削除"
    schedule = "0 * * * *"  # 毎時0分に実行

    def run(self) -> None:
        db = next(get_db())
        try:
            service = SessionService(db)
            count = service.cleanup_expired_sessions()
            logger.info(f"Cleaned up {count} expired sessions")
        finally:
            db.close()

# 自動登録
TaskRegistry.register(CleanupSessionsTask)
```

## カスタムタスクの作成

### 基本的な作成手順

1. **タスククラスを定義**

```python
# app/infrastructure/batch/tasks/my_custom_task.py
from app.infrastructure.batch.base import BaseTask
from app.infrastructure.batch.registry import TaskRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)

class MyCustomTask(BaseTask):
    """カスタムタスクの説明"""
    name = "my_custom_task"
    description = "カスタムタスク"
    schedule = "30 3 * * *"  # 毎日午前3時30分に実行

    def run(self) -> None:
        logger.info(f"Starting {self.name}")

        # タスクのロジック
        # 例: データベースクエリ、外部API呼び出し、ファイル処理等

        logger.info(f"Completed {self.name}")

# 自動登録
TaskRegistry.register(MyCustomTask)
```

2. **tasksパッケージに配置**

ファイルを `app/infrastructure/batch/tasks/` に配置するだけで、自動的に登録される。

### Cronスケジュール式

```bash
# フォーマット: 分 時 日 月 曜日
0 * * * *       # 毎時0分
0 2 * * *       # 毎日午前2時
0 0 * * 0       # 毎週日曜日午前0時
0 0 1 * *       # 毎月1日午前0時
*/15 * * * *    # 15分ごと
30 3 * * 1-5    # 平日の午前3時30分
```

**参考**: [Crontab Guru](https://crontab.guru/)

### データベースを使用するタスク

```python
from app.infrastructure.database import get_db

class DatabaseTask(BaseTask):
    name = "database_task"
    description = "データベースを使用するタスク"
    schedule = "0 4 * * *"

    def run(self) -> None:
        db = next(get_db())
        try:
            # データベース操作
            users = db.query(User).all()
            # ...
        finally:
            db.close()
```

### 外部APIを呼び出すタスク

```python
import httpx

class APITask(BaseTask):
    name = "api_task"
    description = "外部APIを呼び出すタスク"
    schedule = "0 5 * * *"

    def run(self) -> None:
        with httpx.Client() as client:
            response = client.get("https://api.example.com/data")
            data = response.json()
            # データ処理
```

### エラーハンドリング

```python
from app.domain.exceptions.base import DomainError

class RobustTask(BaseTask):
    name = "robust_task"
    description = "エラーハンドリングを含むタスク"
    schedule = "0 6 * * *"

    def run(self) -> None:
        try:
            # タスクのロジック
            self._process_data()
        except DomainError as e:
            logger.error(f"Domain error in {self.name}: {e.message}", exc_info=e)
            # Sentryに送信（main.pyのミドルウェアで自動送信）
        except Exception as e:
            logger.error(f"Unexpected error in {self.name}: {str(e)}", exc_info=e)
            # Sentryに送信

    def _process_data(self) -> None:
        # 実際の処理
        pass
```

## 実装例

### 定期的なデータ集計タスク

```python
from app.infrastructure.batch.base import BaseTask
from app.infrastructure.batch.registry import TaskRegistry
from app.infrastructure.database import get_db
from app.core.logging import get_logger
from sqlalchemy import func
from datetime import datetime, timedelta

logger = get_logger(__name__)

class DailyReportTask(BaseTask):
    """日次レポート作成タスク"""
    name = "daily_report"
    description = "日次レポートを作成"
    schedule = "0 1 * * *"  # 毎日午前1時

    def run(self) -> None:
        db = next(get_db())
        try:
            # 昨日の日付
            yesterday = datetime.now().date() - timedelta(days=1)

            # ユーザー登録数
            user_count = (
                db.query(func.count(User.id))
                .filter(func.date(User.created_at) == yesterday)
                .scalar()
            )

            # セッション数
            session_count = (
                db.query(func.count(Session.session_id))
                .filter(func.date(Session.created_at) == yesterday)
                .scalar()
            )

            logger.info(
                f"Daily report for {yesterday}: "
                f"{user_count} users, {session_count} sessions"
            )

            # レポート保存、メール送信等
        finally:
            db.close()

TaskRegistry.register(DailyReportTask)
```

### 動的スケジュール（設定から取得）

```python
from app.core.config import get_settings

class DynamicScheduleTask(BaseTask):
    """動的スケジュールタスク"""
    name = "dynamic_schedule"
    description = "動的スケジュールタスク"

    @property
    def schedule(self) -> str:
        """スケジュールを設定から取得"""
        settings = get_settings()
        return settings.CUSTOM_TASK_CRON

    def run(self) -> None:
        # タスクのロジック
        pass
```

**設定** (`.env`):
```bash
CUSTOM_TASK_CRON="0 7 * * *"
```

## デバッグ・テスト

### 手動実行

```python
from app.infrastructure.batch.tasks.backup import BackupTask

# タスクインスタンスを作成
task = BackupTask()

# 手動実行
task.run()
```

### スケジューラーの状態確認

```python
# app/presentation/api/system/scheduler.py
from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/scheduler/jobs")
async def get_scheduled_jobs(request: Request):
    """スケジューラーのジョブ一覧を取得"""
    scheduler = request.app.state.scheduler
    jobs = scheduler.get_jobs()

    return [
        {
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger),
        }
        for job in jobs
    ]
```

## ベストプラクティス

### 1. タスクは冪等に実装

```python
# ✅ GOOD: 冪等性を保つ
class IdempotentTask(BaseTask):
    name = "idempotent_task"
    description = "冪等なタスク"
    schedule = "0 8 * * *"

    def run(self) -> None:
        # 同じ日に複数回実行しても安全
        today = datetime.now().date()

        # 既に処理済みかチェック
        if self._is_already_processed(today):
            logger.info(f"Already processed for {today}")
            return

        # 処理実行
        self._process(today)
        self._mark_as_processed(today)
```

### 2. 長時間実行タスクは分割

```python
# ❌ BAD: 1つのタスクで大量のデータを処理
class HeavyTask(BaseTask):
    def run(self) -> None:
        all_users = db.query(User).all()  # 数万件
        for user in all_users:
            # 重い処理
            pass

# ✅ GOOD: バッチ処理で分割
class OptimizedTask(BaseTask):
    def run(self) -> None:
        batch_size = 100
        offset = 0

        while True:
            users = db.query(User).limit(batch_size).offset(offset).all()
            if not users:
                break

            for user in users:
                # 処理
                pass

            offset += batch_size
            db.commit()  # バッチごとにコミット
```

### 3. エラーハンドリングを実装

```python
# ✅ GOOD: エラーハンドリング
class RobustTask(BaseTask):
    def run(self) -> None:
        try:
            self._execute()
        except Exception as e:
            logger.error(f"Task {self.name} failed: {str(e)}", exc_info=e)
            # 必要に応じてアラート送信
```

### 4. タスクの実行時間を記録

```python
import time

class MonitoredTask(BaseTask):
    def run(self) -> None:
        start_time = time.time()
        try:
            self._execute()
        finally:
            elapsed = time.time() - start_time
            logger.info(f"Task {self.name} completed in {elapsed:.2f}s")
```

## 参考資料

- [Architecture](../architecture.md) - Clean Architecture実装詳細
- [Database Backup](database-backup.md) - BackupTask詳細
- [Session Management](session-management.md) - CleanupSessionsTask
- [APScheduler Documentation](https://apscheduler.readthedocs.io/)
