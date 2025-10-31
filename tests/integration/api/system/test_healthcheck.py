"""
システムヘルスチェックエンドポイントの統合テスト
"""

from fastapi.testclient import TestClient


class TestHealthCheck:
    """ヘルスチェックエンドポイントのテスト"""

    def test_healthcheck(self, client: TestClient) -> None:
        """ヘルスチェックが正常に動作すること"""
        response = client.get("/api/system/healthcheck/")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_healthcheck_returns_json(self, client: TestClient) -> None:
        """ヘルスチェックがJSON形式で返すこと"""
        response = client.get("/api/system/healthcheck/")
        assert response.headers["content-type"] == "application/json"

    def test_healthcheck_no_authentication_required(self, client: TestClient) -> None:
        """ヘルスチェックは認証不要であること"""
        # 認証ヘッダーなしでアクセス可能
        response = client.get("/api/system/healthcheck/")
        assert response.status_code == 200
