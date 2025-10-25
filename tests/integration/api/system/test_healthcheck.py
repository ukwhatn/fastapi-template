"""
システムヘルスチェックエンドポイントの統合テスト
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

    def test_healthcheck_returns_json(self, client: TestClient):
        """ヘルスチェックがJSON形式で返すこと"""
        response = client.get("/system/healthcheck/")
        assert response.headers["content-type"] == "application/json"

    def test_healthcheck_no_authentication_required(self, client: TestClient):
        """ヘルスチェックは認証不要であること"""
        # 認証ヘッダーなしでアクセス可能
        response = client.get("/system/healthcheck/")
        assert response.status_code == 200
