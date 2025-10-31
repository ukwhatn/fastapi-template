# Database Backup

本テンプレートのデータベースバックアップシステム。pg_dump/pg_restore不要、psycopg2直接使用によるgzip圧縮JSON形式バックアップ、S3連携、トランザクション保証を提供。

## 特徴

- **pg_dump/pg_restore不要**: psycopg2を直接使用、依存関係最小化
- **gzip圧縮JSON形式**: 可読性と圧縮率のバランス
- **マイグレーションバージョン記録**: リストア時に自動調整
- **トランザクション保証**: all-or-nothing、失敗時は自動ロールバック
- **差分表示**: リストア前に変更内容を確認可能
- **S3連携**: リモートバックアップのアップロード/ダウンロード/一覧
- **自動クリーンアップ**: 古いバックアップを自動削除（設定可能）

## アーキテクチャ

### コンポーネント構成

```
┌────────────────────────────────────────────────────┐
│ Makefile / CLI                                     │
│  - make db:backup:oneshot                          │
│  - make db:backup:restore FILE="xxx.backup.gz"     │
│  - make db:backup:diff FILE="xxx.backup.gz"        │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ app/utils/backup_cli.py                            │
│  - CLIエントリーポイント                           │
│  - コマンドライン引数パース                        │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ app/infrastructure/database/backup/core.py         │
│  - create_backup()                                 │
│  - calculate_diff()                                │
│  - restore_backup()                                │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ app/infrastructure/database/backup/models.py       │
│  - BackupMetadata (Pydantic)                       │
│  - TableBackup                                     │
│  - BackupData                                      │
│  - DiffSummary                                     │
│  - RestoreResult                                   │
└────────────────┬───────────────────────────────────┘
                 │
                 ↓
┌────────────────────────────────────────────────────┐
│ PostgreSQL Database                                │
│  + alembic_version table                           │
└────────────────────────────────────────────────────┘
```

## データモデル

### BackupData

**場所**: `app/infrastructure/database/backup/models.py`

```python
class BackupMetadata(BaseModel):
    """バックアップメタデータ"""
    timestamp: datetime
    migration_version: str
    database_name: str
    database_host: str

class TableBackup(BaseModel):
    """テーブルバックアップ"""
    row_count: int
    columns: list[str]
    data: list[list[Any]]

class BackupData(BaseModel):
    """バックアップデータ全体"""
    metadata: BackupMetadata
    tables: dict[str, TableBackup]
```

**ファイル形式**:
```json
{
  "metadata": {
    "timestamp": "2025-11-01T12:34:56.789Z",
    "migration_version": "0aa2828fc065",
    "database_name": "myapp_db",
    "database_host": "localhost"
  },
  "tables": {
    "users": {
      "row_count": 100,
      "columns": ["id", "name", "email", "created_at"],
      "data": [
        [1, "Alice", "alice@example.com", "2025-01-01T00:00:00Z"],
        [2, "Bob", "bob@example.com", "2025-01-02T00:00:00Z"]
      ]
    },
    "sessions": {
      "row_count": 50,
      "columns": ["session_id", "data", "expires_at"],
      "data": [...]
    }
  }
}
```

## コア機能

### create_backup

**場所**: `app/infrastructure/database/backup/core.py`

```python
def create_backup(output_dir: Path | None = None) -> Path:
    """
    データベースのバックアップを作成する

    Args:
        output_dir: 出力先ディレクトリ（Noneの場合は ./backups）

    Returns:
        Path: 作成されたバックアップファイルのパス

    Raises:
        RuntimeError: バックアップの作成に失敗した場合
    """
```

**処理フロー**:
1. マイグレーションバージョンを取得
2. メタデータ作成
3. 全テーブルのデータを取得（alembic_versionを除く）
4. データをシリアライズ（datetime/bytesの変換）
5. JSON化
6. gzip圧縮
7. ファイル保存（`backup_YYYYMMDD_HHMMSS.backup.gz`）

**使用例**:
```python
from pathlib import Path
from app.infrastructure.database.backup.core import create_backup

backup_path = create_backup(output_dir=Path("./backups"))
print(f"Backup created: {backup_path}")
```

**コマンドライン**:
```bash
make db:backup:oneshot

# または直接実行
uv run python app/utils/backup_cli.py create --output-dir ./backups
```

**出力例**:
```
Creating database backup...
Migration version: 0aa2828fc065
- users: 100 rows (12.34 KB)
- sessions: 50 rows (8.56 KB)
Total: 2 tables, 150 rows
Backup size: 20.90 KB → 5.12 KB (compressed)
Saved to: ./backups/backup_20251101_123456.backup.gz
```

### calculate_diff

```python
def calculate_diff(backup_path: Path) -> DiffSummary:
    """
    バックアップファイルと現在のデータベースの差分を計算する

    Args:
        backup_path: バックアップファイルのパス

    Returns:
        DiffSummary: 差分サマリ

    Raises:
        RuntimeError: 差分計算に失敗した場合
    """
```

**差分情報**:
```python
class TableDiff(BaseModel):
    current_rows: int  # 現在の行数
    backup_rows: int   # バックアップの行数
    diff: int          # 差分（backup - current）

class DiffSummary(BaseModel):
    tables: dict[str, TableDiff]
    total_current_rows: int
    total_backup_rows: int
    total_diff: int
```

**使用例**:
```python
from app.infrastructure.database.backup.core import calculate_diff

diff = calculate_diff(Path("./backups/backup_20251101_123456.backup.gz"))
for table_name, table_diff in diff.tables.items():
    print(f"{table_name}: {table_diff.current_rows} → {table_diff.backup_rows} ({table_diff.diff:+d})")
```

**コマンドライン**:
```bash
make db:backup:diff FILE="backup_20251101_123456.backup.gz"

# または直接実行
uv run python app/utils/backup_cli.py diff ./backups/backup_20251101_123456.backup.gz
```

**出力例**:
```
Calculating diff with backup: backup_20251101_123456.backup.gz
Backup created at: 2025-11-01T12:34:56.789Z

Table Diff Summary:
  users: 120 → 100 (+20)
  sessions: 45 → 50 (-5)

Total: 165 rows → 150 rows (+15)
```

### restore_backup

```python
def restore_backup(backup_path: Path, show_diff: bool = True) -> RestoreResult:
    """
    バックアップからデータベースをリストアする

    Args:
        backup_path: バックアップファイルのパス
        show_diff: リストア前にdiffを計算して表示するか

    Returns:
        RestoreResult: リストア結果

    Raises:
        RuntimeError: リストアに失敗した場合
    """
```

**処理フロー（トランザクション内）**:
1. バックアップファイルを読み込み
2. 差分を計算（show_diff=Trueの場合）
3. トランザクション開始
4. 全テーブルをTRUNCATE（alembic_versionを除く）
5. マイグレーションバージョンを調整
6. データを投入
7. コミット

**失敗時の挙動**:
- トランザクションが自動的にロールバック
- データベースは元の状態のまま

**使用例**:
```python
from app.infrastructure.database.backup.core import restore_backup

result = restore_backup(
    backup_path=Path("./backups/backup_20251101_123456.backup.gz"),
    show_diff=True
)

if result.success:
    print(f"Restored {result.restored_tables} tables with {result.restored_rows} rows")
else:
    print(f"Restore failed: {result.message}")
```

**コマンドライン**:
```bash
# 通常のリストア
make db:backup:restore FILE="backup_20251101_123456.backup.gz"

# ドライラン（差分のみ表示、実際にはリストアしない）
make db:backup:restore:dry-run FILE="backup_20251101_123456.backup.gz"

# または直接実行
uv run python app/utils/backup_cli.py restore ./backups/backup_20251101_123456.backup.gz
uv run python app/utils/backup_cli.py restore ./backups/backup_20251101_123456.backup.gz --dry-run
```

**出力例**:
```
Restoring from backup: backup_20251101_123456.backup.gz
Backup created at: 2025-11-01T12:34:56.789Z
Migration version: 0aa2828fc065

Calculating diff before restore...
  users: 120 → 100 (+20)
  sessions: 45 → 50 (-5)

Starting restore transaction...
Truncating table: users
Truncating table: sessions
Adjusting migration version: 0aa2828fc065 → 0aa2828fc065
Restoring table: users (100 rows)
Restoring table: sessions (50 rows)
Committing transaction...

Restore completed: 2 tables, 150 rows
```

## S3連携

### S3へのアップロード

```bash
make db:backup:upload FILE="backup_20251101_123456.backup.gz"

# または直接実行
uv run python app/utils/backup_cli.py upload ./backups/backup_20251101_123456.backup.gz
```

### S3からのダウンロード

```bash
make db:backup:download FILE="backup_20251101_123456.backup.gz"

# または直接実行
uv run python app/utils/backup_cli.py download backup_20251101_123456.backup.gz
```

### S3バックアップ一覧

```bash
make db:backup:list:remote

# または直接実行
uv run python app/utils/backup_cli.py list-s3
```

### S3からのリストア

```bash
make db:backup:restore:s3 FILE="backup_20251101_123456.backup.gz"

# または直接実行
uv run python app/utils/backup_cli.py restore-s3 backup_20251101_123456.backup.gz
```

**処理フロー**:
1. S3からバックアップファイルをダウンロード
2. ローカルにリストア

## バッチ自動バックアップ

**場所**: `app/infrastructure/batch/tasks/backup.py`

```python
class BackupTask(BaseTask):
    """定期バックアップタスク"""
    name = "backup"
    description = "データベースバックアップを作成"
    schedule: str  # BACKUP_CRONから取得

    def run(self):
        # バックアップ作成
        backup_path = create_backup(output_dir=Path("./backups"))
        logger.info(f"Backup created: {backup_path}")

        # 古いバックアップを削除（BACKUP_RETENTION_DAYSに基づく）
        retention_days = get_settings().BACKUP_RETENTION_DAYS
        cutoff = datetime.now() - timedelta(days=retention_days)

        for backup_file in Path("./backups").glob("backup_*.backup.gz"):
            if backup_file.stat().st_mtime < cutoff.timestamp():
                backup_file.unlink()
                logger.info(f"Deleted old backup: {backup_file}")
```

**設定** (`.env`):
```bash
BACKUP_CRON="0 2 * * *"        # 毎日午前2時にバックアップ
BACKUP_RETENTION_DAYS=7        # 7日間保持
```

## Makefileコマンド一覧

### ローカルバックアップ

```bash
# バックアップ作成
make db:backup:oneshot

# バックアップ一覧
make db:backup:list

# 差分表示
make db:backup:diff FILE="backup_20251101_123456.backup.gz"

# リストア
make db:backup:restore FILE="backup_20251101_123456.backup.gz"

# ドライラン（差分のみ表示）
make db:backup:restore:dry-run FILE="backup_20251101_123456.backup.gz"
```

### S3バックアップ

```bash
# S3へアップロード
make db:backup:upload FILE="backup_20251101_123456.backup.gz"

# S3からダウンロード
make db:backup:download FILE="backup_20251101_123456.backup.gz"

# S3バックアップ一覧
make db:backup:list:remote

# S3からリストア
make db:backup:restore:s3 FILE="backup_20251101_123456.backup.gz"

# S3からのドライラン
make db:backup:restore:s3:dry-run FILE="backup_20251101_123456.backup.gz"
```

## 実装例

### プログラムからのバックアップ作成

```python
from pathlib import Path
from app.infrastructure.database.backup.core import create_backup

# バックアップ作成
try:
    backup_path = create_backup(output_dir=Path("./backups"))
    print(f"Backup created: {backup_path}")
except RuntimeError as e:
    print(f"Backup failed: {e}")
```

### プログラムからのリストア

```python
from pathlib import Path
from app.infrastructure.database.backup.core import restore_backup

# リストア
try:
    result = restore_backup(
        backup_path=Path("./backups/backup_20251101_123456.backup.gz"),
        show_diff=True
    )
    if result.success:
        print(f"Restored {result.restored_rows} rows")
    else:
        print(f"Restore failed: {result.message}")
except RuntimeError as e:
    print(f"Restore failed: {e}")
```

### カスタムバックアップタスク

```python
from app.infrastructure.batch.base import BaseTask
from app.infrastructure.database.backup.core import create_backup
from pathlib import Path

class CustomBackupTask(BaseTask):
    name = "custom_backup"
    description = "カスタムバックアップタスク"
    schedule = "0 3 * * *"  # 毎日午前3時

    def run(self):
        # バックアップ作成
        backup_path = create_backup(output_dir=Path("./custom_backups"))
        logger.info(f"Custom backup created: {backup_path}")

        # S3へアップロード
        # ... S3アップロード処理
```

## ベストプラクティス

### 1. リストア前に必ず差分を確認

```bash
# ❌ BAD: 差分確認なしでリストア
make db:backup:restore FILE="backup_xxx.backup.gz"

# ✅ GOOD: まず差分を確認
make db:backup:diff FILE="backup_xxx.backup.gz"
# 確認後にリストア
make db:backup:restore FILE="backup_xxx.backup.gz"

# または、ドライランで差分確認
make db:backup:restore:dry-run FILE="backup_xxx.backup.gz"
```

### 2. 定期的にS3へアップロード

```bash
# バックアップ作成後にS3へアップロード
make db:backup:oneshot && make db:backup:upload FILE="$(ls -t backups/*.backup.gz | head -1 | xargs basename)"
```

### 3. 本番環境では自動バックアップを有効化

```bash
# .env
BACKUP_CRON="0 2 * * *"        # 毎日午前2時
BACKUP_RETENTION_DAYS=7        # 7日間保持
```

### 4. リストア前にバックアップを作成

```bash
# ✅ GOOD: 現在の状態をバックアップしてからリストア
make db:backup:oneshot
make db:backup:restore FILE="old_backup.backup.gz"
```

## トラブルシューティング

### バックアップファイルが大きすぎる

**原因**: 大量のデータ

**対策**:
```bash
# gzip圧縮率を確認
gzip -l ./backups/backup_xxx.backup.gz

# 不要なデータを削除してからバックアップ
# 例: 古いセッションを削除
make db:cleanup:sessions
make db:backup:oneshot
```

### リストアが失敗する

**原因**: マイグレーションバージョンの不一致、データ型の不一致等

**対策**:
```bash
# ログを確認
tail -f logs/app.log

# ドライランで差分を確認
make db:backup:restore:dry-run FILE="backup_xxx.backup.gz"

# マイグレーションバージョンを確認
make db:current
```

### S3へのアップロードが失敗する

**原因**: AWS認証情報の不足、S3バケットへのアクセス権限不足

**対策**:
```bash
# AWS認証情報を確認
aws s3 ls s3://your-bucket-name/

# .envを確認
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY
# S3_BUCKET_NAME
```

## 参考資料

- [Architecture](../architecture.md) - Clean Architecture実装詳細
- [Batch System](batch-system.md) - 自動バックアップタスク
- [API Reference](../api-reference.md) - 共通コンポーネント
