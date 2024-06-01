import os
import secrets

from .redis import RedisCrud
from .schemas import SessionSchema


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

    def create(self, response, data: SessionSchema) -> SessionSchema | None:
        session_id = secrets.token_urlsafe(64)
        self._set(session_id, data)
        response.set_cookie(key=self.cookie_name, value=session_id)
        return self._get(session_id)

    def get(self, request) -> SessionSchema | None:
        sess_id = request.cookies.get(self.cookie_name)
        if sess_id is None:
            return None
        return self._get(sess_id)

    def update(self, request, response, data: SessionSchema) -> SessionSchema | None:
        sess_id = request.cookies.get(self.cookie_name)

        # create new session if not exists
        if sess_id is None:
            return self.create(response, data)

        self._set(sess_id, data)
        return data

    def delete(self, request, response) -> None:
        sess_id = request.cookies.get(self.cookie_name)
        if sess_id is None:
            return None
        self._delete(sess_id)
        response.delete_cookie(key=self.cookie_name)
