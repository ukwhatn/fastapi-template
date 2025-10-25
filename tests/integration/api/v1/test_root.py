"""
v1 APIルートエンドポイントの統合テスト
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """ルートエンドポイントのテスト"""

    def test_root(self, client: TestClient):
        """ルートエンドポイントが正常に動作すること"""
        response = client.get("/v1/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Hello World"
