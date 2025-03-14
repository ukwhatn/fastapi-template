from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import deps
from db import crud
from db.schemas.item import Item, ItemCreate, ItemUpdate

router = APIRouter()


@router.get("/", response_model=List[Item])
def read_items(
    db_session: deps.DBWithSession = Depends(deps.get_db_with_session),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    複数アイテム取得
    """
    items = crud.item.get_multi(db_session.db, skip=skip, limit=limit)
    return items


@router.post("/", response_model=Item)
def create_item(
    *,
    db: Session = Depends(deps.get_db),
    item_in: ItemCreate,
    owner_id: int = 1,  # 仮のowner_id
    _: str = Depends(deps.get_api_key),  # APIキー認証
) -> Any:
    """
    アイテム作成（APIキー認証必須）
    """
    item = crud.item.create_with_owner(db=db, obj_in=item_in, owner_id=owner_id)
    return item


@router.put("/{id}", response_model=Item)
def update_item(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    item_in: ItemUpdate,
    _: str = Depends(deps.get_api_key),  # APIキー認証
) -> Any:
    """
    アイテム更新（APIキー認証必須）
    """
    item = crud.item.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 所有者確認などのロジックをここに追加

    item = crud.item.update(db=db, db_obj=item, obj_in=item_in)
    return item


@router.get("/{id}", response_model=Item)
def read_item(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
) -> Any:
    """
    アイテム取得
    """
    item = crud.item.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.delete("/{id}", response_model=Item)
def delete_item(
    *,
    db: Session = Depends(deps.get_db),
    id: int,
    _: str = Depends(deps.get_api_key),  # APIキー認証
) -> Any:
    """
    アイテム削除（APIキー認証必須）
    """
    item = crud.item.get(db=db, id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 所有者確認などのロジックをここに追加

    item = crud.item.remove(db=db, id=id)
    return item
