from fastapi.testclient import TestClient


def test_healthcheck(client: TestClient) -> None:
    """ヘルスチェックエンドポイントのテスト"""
    response = client.get("/system/healthcheck/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
