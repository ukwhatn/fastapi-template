"""
v1 APIルートエンドポイントの統合テスト
"""

from typing import Any
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """ルートエンドポイントのテスト"""

    def test_root(self, client: TestClient) -> None:
        """ルートエンドポイントが正常に動作すること"""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        data: Any = response.json()
        assert "message" in data
        assert data["message"] == "Hello World"
