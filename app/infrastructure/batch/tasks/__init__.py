"""バッチタスク実装"""

# タスクをインポートすることで自動的にレジストリに登録される
from . import backup  # noqa: F401

__all__ = ["backup"]
