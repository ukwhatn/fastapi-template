"""システム関連のスキーマ定義"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class DatabaseStatus(BaseModel):
    """
    データベース接続状況

    Attributes:
        status: DB接続の状態（healthy/unhealthy）
        connection: DB接続が確立されているか
        error: エラーメッセージ（エラー時のみ）
    """

    status: Literal["healthy", "unhealthy"]
    connection: bool
    error: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """
    ヘルスチェックレスポンス

    Attributes:
        status: 全体的なヘルス状態（ok/unhealthy）
        timestamp: レスポンス生成時刻
        uptime_seconds: アプリケーション起動からの経過秒数
        database: データベース接続状況
        environment: 実行環境（production/staging/local等）
    """

    status: Literal["ok", "unhealthy"]
    timestamp: datetime
    uptime_seconds: float
    database: DatabaseStatus
    environment: str
