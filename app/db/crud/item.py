from sqlalchemy.orm import Session

from db.crud.base import CRUDBase
from db.models.item import Item
from db.schemas.item import ItemCreate, ItemUpdate


class CRUDItem(CRUDBase[Item, ItemCreate, ItemUpdate]):
    """
    アイテムのCRUD操作
    """

    def create_with_owner(
        self, db: Session, *, obj_in: ItemCreate, owner_id: int
    ) -> Item:
        """
        所有者情報付きで作成
        """
        db_obj = Item(
            title=obj_in.title,
            description=obj_in.description,
            owner_id=owner_id,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_multi_by_owner(
        self, db: Session, *, owner_id: int, skip: int = 0, limit: int = 100
    ):
        """
        所有者IDで複数取得
        """
        return (
            db.query(self.model)
            .filter(Item.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .all()
        )


item = CRUDItem(Item)
