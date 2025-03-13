from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """
    全スキーマの基本クラス
    """

    model_config = ConfigDict(from_attributes=True)


class TimestampSchema(BaseSchema):
    """
    タイムスタンプフィールドを持つスキーマ
    """

    created_at: datetime
    updated_at: datetime


class BaseModelSchema(TimestampSchema):
    """
    基本フィールドを持つモデルスキーマ
    """

    id: int
