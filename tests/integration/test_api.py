"""
API統合テスト
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthCheck:
    """ヘルスチェックエンドポイントのテスト"""

    def test_healthcheck(self, client: TestClient):
        """ヘルスチェックが正常に動作すること"""
        response = client.get("/system/healthcheck/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRootEndpoint:
    """ルートエンドポイントのテスト"""

    def test_root(self, client: TestClient):
        """ルートエンドポイントが正常に動作すること"""
        response = client.get("/v1/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Hello World"


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_404_not_found(self, client: TestClient):
        """存在しないエンドポイントで404が返ること"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
