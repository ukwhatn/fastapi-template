"""
APIエラーハンドリングの統合テスト
"""

import pytest
from fastapi.testclient import TestClient


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_404_not_found(self, client: TestClient):
        """存在しないエンドポイントで404が返ること"""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_404_contains_message(self, client: TestClient):
        """404エラーレスポンスにメッセージが含まれること"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert data["status"] == "error"

    def test_405_method_not_allowed(self, client: TestClient):
        """許可されていないHTTPメソッドで405が返ること"""
        # ヘルスチェックはGETのみ許可
        response = client.post("/system/healthcheck/")
        assert response.status_code == 405
