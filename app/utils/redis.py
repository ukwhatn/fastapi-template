import json
from typing import Any, Optional

import redis

from core import get_settings

settings = get_settings()


class RedisCrud:
    """
    Redis基本操作クラス
    """

    def __init__(self, db: int = 0):
        """
        Redisインスタンス初期化
        """
        self.connect = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=db
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connect.close()

    def get(self, key: str) -> Optional[Any]:
        """
        データ取得
        注: 複雑なオブジェクトはJSON形式で保存されており、
        基本型 (str, int, float, bool, list, dict) のみサポート
        """
        data = self.connect.get(key)
        if data is None:
            return None

        try:
            # デコードしてJSON解析
            return json.loads(data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            # エラーログを出力し、Noneを返す
            print(f"Error decoding Redis data for key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        データ設定
        注: 複雑なオブジェクトはJSON形式で保存、
        基本型 (str, int, float, bool, list, dict) のみサポート
        """
        try:
            # JSON文字列に変換してバイト列としてエンコード
            json_data = json.dumps(value).encode("utf-8")

            if expire is not None:
                return self.connect.set(key, json_data, ex=expire)

            return self.connect.set(key, json_data)
        except (TypeError, ValueError) as e:
            # シリアル化できないオブジェクトの場合はエラーログを出力
            print(f"Error encoding value for Redis key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> int:
        """
        データ削除
        """
        return self.connect.delete(key)
