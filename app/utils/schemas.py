from typing import Any

from pydantic import BaseModel, ConfigDict


class SessionSchema(BaseModel):
    """
    セッションデータスキーマ
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: dict[str, Any] = {}
