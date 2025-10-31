"""
APIエラーハンドリングの統合テスト
"""

from typing import Any
from fastapi.testclient import TestClient


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_404_not_found(self, client: TestClient) -> None:
        """存在しないエンドポイントで404が返ること"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_404_contains_message(self, client: TestClient) -> None:
        """404エラーレスポンスにメッセージが含まれること"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data: Any = response.json()
        assert "message" in data
        assert data["status"] == "error"

    def test_405_method_not_allowed(self, client: TestClient) -> None:
        """許可されていないHTTPメソッドで405が返ること"""
        # ヘルスチェックはGETのみ許可
        response = client.post("/api/system/healthcheck/")
        assert response.status_code == 405
