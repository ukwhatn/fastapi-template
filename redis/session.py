import secrets
import os

from .redis import RedisCrud


class SessionCrud:
    def __init__(self):
        self.crud = RedisCrud(db=0)

        self.cookie_name = os.environ.get("SESSION_COOKIE_NAME", "session_id")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.crud.__exit__(exc_type, exc_value, traceback)

    def _get(self, key):
        return self.crud.get(key)

    def _set(self, key, value):
        data = self.crud.set(key, value, expire=int(os.environ.get("SESSION_EXPIRE", 60 * 60 * 24)))
        return data

    def _delete(self, key):
        return self.crud.delete(key)

    def create(self, response, data):
        session_id = secrets.token_urlsafe(16)
        self._set(session_id, data)
        response.set_cookie(key=self.cookie_name, value=session_id)

    def get(self, request):
        sess_id = request.cookies.get(self.cookie_name)
        if sess_id is None:
            return None
        return self._get(sess_id)

    def delete(self, request, response):
        sess_id = request.cookies.get(self.cookie_name)
        if sess_id is None:
            return None
        self._delete(sess_id)
        response.delete_cookie(key=self.cookie_name)
