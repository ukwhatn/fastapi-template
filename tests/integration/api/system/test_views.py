"""
システムビューエンドポイントの統合テスト
"""

from typing import Any
from fastapi.testclient import TestClient


class TestViewsEndpoint:
    """ビューエンドポイントのテスト"""

    def test_views_index_without_templates(self, client: TestClient) -> None:
        """テンプレートが無効の場合、404が返ること"""
        response = client.get("/api/system/views/")
        # テンプレートディレクトリが存在しない場合は404
        assert response.status_code == 404
        data: Any = response.json()
        assert "message" in data
        assert "Templates not enabled" in data["message"]

    # TODO: テンプレートが有効な場合のテストを追加
    # @pytest.mark.skip(reason="Requires template setup")
    # def test_views_index_with_templates(self, client: TestClient) -> None:
    #     """テンプレートが有効な場合、HTMLが返ること"""
    #     pass
