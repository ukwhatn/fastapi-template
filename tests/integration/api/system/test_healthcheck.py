"""
システムヘルスチェックエンドポイントの統合テスト
"""

from fastapi.testclient import TestClient


class TestHealthCheck:
    """ヘルスチェックエンドポイントのテスト"""

    def test_healthcheck_success(self, client: TestClient) -> None:
        """ヘルスチェックが正常に動作すること"""
        response = client.get("/api/system/healthcheck/")
        assert response.status_code == 200

        data = response.json()
        # レスポンス構造の検証
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert "database" in data
        assert "environment" in data

        # 正常時はstatus=ok
        assert data["status"] == "ok"

        # uptimeは0以上
        assert data["uptime_seconds"] >= 0.0

        # database構造の検証
        db = data["database"]
        assert "status" in db
        assert "connection" in db
        assert "error" in db

        # DB有効時はhealthy
        assert db["status"] == "healthy"
        assert db["connection"] is True
        assert db["error"] is None

        # 環境情報
        assert data["environment"] in ["local", "test", "staging", "production"]

    def test_healthcheck_returns_json(self, client: TestClient) -> None:
        """ヘルスチェックがJSON形式で返すこと"""
        response = client.get("/api/system/healthcheck/")
        assert response.headers["content-type"] == "application/json"

    def test_healthcheck_no_authentication_required(self, client: TestClient) -> None:
        """ヘルスチェックは認証不要であること"""
        response = client.get("/api/system/healthcheck/")
        assert response.status_code == 200
