"""
pytest設定と共通フィクスチャ（DB不要）
"""

import os
from typing import Any

import pytest
from cryptography.fernet import Fernet


def pytest_configure(config: Any) -> None:
    """
    pytest実行前の設定

    暗号化キーをモジュールインポート前に設定する必要があるため、
    フィクスチャではなくpytest_configureフックで設定
    """
    # テスト用暗号化キーを設定
    key = Fernet.generate_key().decode()
    os.environ["SESSION_ENCRYPTION_KEY"] = key


# pytest_configure後にインポート（環境変数設定後にモジュールをロード）
from app.core.config import get_settings


@pytest.fixture
def api_key() -> str:
    """
    テスト用APIキー

    Returns:
        APIキー文字列
    """
    settings = get_settings()
    return settings.API_KEY
