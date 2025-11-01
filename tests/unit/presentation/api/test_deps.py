"""
依存性注入（deps）の単体テスト
"""

from typing import Any
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException

from app.presentation.api.deps import get_api_key, get_session


class TestAPIKeyAuthentication:
    """APIキー認証のテスト"""

    def test_valid_api_key(self) -> None:
        """正しいAPIキーで認証成功"""
        with patch("app.presentation.api.deps.get_settings") as mock_settings:
            mock_settings.return_value.API_KEY = "test-api-key"

            result = get_api_key(api_key_header="Bearer test-api-key")
            assert result == "test-api-key"

    def test_missing_authorization_header(self) -> None:
        """Authorizationヘッダーがない場合は403エラー"""
        with pytest.raises(HTTPException) as exc_info:
            get_api_key(api_key_header="")

        assert exc_info.value.status_code == 403
        assert "Authorization header missing" in exc_info.value.detail

    def test_invalid_scheme(self) -> None:
        """Bearerスキームでない場合は403エラー"""
        with pytest.raises(HTTPException) as exc_info:
            get_api_key(api_key_header="Basic test-api-key")

        assert exc_info.value.status_code == 403
        assert "must start with 'Bearer'" in exc_info.value.detail

    def test_missing_api_key_value(self) -> None:
        """APIキー値が空の場合は403エラー"""
        with patch("app.presentation.api.deps.get_settings") as mock_settings:
            mock_settings.return_value.API_KEY = "test-api-key"

            with pytest.raises(HTTPException) as exc_info:
                get_api_key(api_key_header="Bearer ")

            assert exc_info.value.status_code == 403
            assert "Invalid API key" in exc_info.value.detail

    def test_invalid_api_key(self) -> None:
        """間違ったAPIキーで403エラー"""
        with patch("app.presentation.api.deps.get_settings") as mock_settings:
            mock_settings.return_value.API_KEY = "correct-api-key"

            with pytest.raises(HTTPException) as exc_info:
                get_api_key(api_key_header="Bearer wrong-api-key")

            assert exc_info.value.status_code == 403
            assert "Invalid API key" in exc_info.value.detail

    def test_case_insensitive_bearer_scheme(self) -> None:
        """Bearerスキームは大文字小文字を区別しない"""
        with patch("app.presentation.api.deps.get_settings") as mock_settings:
            mock_settings.return_value.API_KEY = "test-api-key"

            result = get_api_key(api_key_header="bearer test-api-key")
            assert result == "test-api-key"


class TestSessionDependency:
    """セッション取得のテスト"""

    def test_get_session_from_request_state(self) -> None:
        """リクエストstateからセッションを取得"""
        from app.utils.schemas import SessionSchema

        mock_request: Any = Mock()
        expected_session = SessionSchema(
            data={"user_id": "123"},
        )
        mock_request.state.session = expected_session

        result = get_session(mock_request)
        assert result == expected_session
        assert result.data["user_id"] == "123"
