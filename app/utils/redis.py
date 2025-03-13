import pickle

import redis

from app.core import get_settings

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

    def get(self, key: str) -> any:
        """
        データ取得
        """
        data = self.connect.get(key)
        if data is None:
            return None
        return pickle.loads(data)

    def set(self, key: str, value: any, expire: int = None) -> bool:
        """
        データ設定
        """
        if expire is not None:
            return self.connect.set(key, pickle.dumps(value), ex=expire)

        return self.connect.set(key, pickle.dumps(value))

    def delete(self, key: str) -> int:
        """
        データ削除
        """
        return self.connect.delete(key)
