import redis
import pickle


class RedisCrud:
    def __init__(self, db: int):
        self.connect = redis.Redis(host='redis', port=6379, db=db)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.connect.close()

    def get(self, key: str):
        data = self.connect.get(key)
        if data is None:
            return None
        return pickle.loads(data)

    def set(self, key: str, value: any, expire: int = None):
        if expire is not None:
            return self.connect.set(key, pickle.dumps(value), ex=expire)

        return self.connect.set(key, pickle.dumps(value))

    def delete(self, key: str):
        return self.connect.delete(key)
