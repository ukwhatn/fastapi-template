"""アプリケーション用のロギングユーティリティ。"""

import logging
import sys


def is_fastapi_context() -> bool:
    """
    FastAPI/uvicornコンテキストで実行中かどうかを判定する。

    Returns:
        bool: uvicornがロードされている場合True、そうでない場合False。
    """
    return "uvicorn" in sys.modules


def get_logger(name: str) -> logging.Logger:
    """
    ロガーインスタンスを取得する。

    FastAPI/uvicornコンテキスト（Webサーバー）で実行中の場合は"uvicorn"ロガーを使用し、
    FastAPIのロギングと一貫したフォーマット・出力を保証する。
    それ以外の場合は、内部スクリプトやユーティリティ用に提供されたモジュール名を使用する。

    Args:
        name: ロガー名、通常は呼び出し元モジュールの__name__を指定。

    Returns:
        logging.Logger: 設定済みのロガーインスタンス。

    Examples:
        >>> # FastAPIコンテキスト内
        >>> logger = get_logger(__name__)  # uvicornロガーを返す
        >>>
        >>> # マイグレーションスクリプト内
        >>> logger = get_logger(__name__)  # app.infrastructure.database.migrationロガーを返す
    """
    if is_fastapi_context():
        return logging.getLogger("uvicorn")
    return logging.getLogger(name)
