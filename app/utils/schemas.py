from typing import Dict, Any

from pydantic import BaseModel, ConfigDict


class SessionSchema(BaseModel):
    """
    セッションデータスキーマ
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: Dict[str, Any] = {}
