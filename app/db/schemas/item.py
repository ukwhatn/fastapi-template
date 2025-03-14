from typing import Optional

from .base import BaseModelSchema, BaseSchema


class ItemBase(BaseSchema):
    """
    Itemの基本スキーマ
    """

    title: str
    description: Optional[str] = None


class ItemCreate(ItemBase):
    """
    Item作成時のスキーマ
    """

    pass


class ItemUpdate(ItemBase):
    """
    Item更新時のスキーマ
    """

    title: Optional[str] = None


class Item(ItemBase, BaseModelSchema):
    """
    Item取得時のスキーマ
    """

    owner_id: int
