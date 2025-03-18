import secrets
from typing import Optional

from fastapi import Request, Response

from core import get_settings
from utils.redis import RedisCrud
from utils.schemas import SessionSchema

settings = get_settings()


class SessionCrud:
    """
    セッション管理クラス
    """

    def __init__(self):
        """
        初期化
        """
        self.crud = RedisCrud(db=0)
        self.cookie_name = settings.SESSION_COOKIE_NAME
        self.expire = settings.SESSION_EXPIRE

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.crud.__exit__(exc_type, exc_value, traceback)

    def _get(self, key: str) -> Optional[SessionSchema]:
        """
        セッションデータ取得
        """
        data = self.crud.get(key)
        if data is None:
            return None
        return SessionSchema.model_validate(data)

    def _set(self, key: str, value: SessionSchema) -> bool:
        """
        セッションデータ設定
        """
        return self.crud.set(key, value.model_dump(), expire=self.expire)

    def _delete(self, key: str) -> int:
        """
        セッションデータ削除
        """
        return self.crud.delete(key)

    def create(
        self, response: Response, data: SessionSchema
    ) -> Optional[SessionSchema]:
        """
        新規セッション作成
        """
        session_id = secrets.token_urlsafe(64)
        self._set(session_id, data)
        response.set_cookie(key=self.cookie_name, value=session_id)
        return self._get(session_id)

    def get(self, request: Request) -> Optional[SessionSchema]:
        """
        セッション取得
        """
        sess_id = request.cookies.get(self.cookie_name)
        if sess_id is None:
            return None
        return self._get(sess_id)

    def update(
        self, request: Request, response: Response, data: SessionSchema
    ) -> Optional[SessionSchema]:
        """
        セッション更新
        """
        sess_id = request.cookies.get(self.cookie_name)

        # セッションが存在しない場合は新規作成
        if sess_id is None:
            return self.create(response, data)

        self._set(sess_id, data)
        return data

    def delete(self, request: Request, response: Response) -> None:
        """
        セッション削除
        """
        sess_id = request.cookies.get(self.cookie_name)
        if sess_id is None:
            return None
        self._delete(sess_id)
        response.delete_cookie(key=self.cookie_name)
