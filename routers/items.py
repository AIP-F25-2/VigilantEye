from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from crud import ItemCRUD
from schemas import Item, ItemCreate, ItemUpdate, Message

router = APIRouter(prefix="/items", tags=["items"])

@router.post("/", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    return ItemCRUD.create_item(db=db, item=item)

@router.get("/", response_model=List[Item])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = ItemCRUD.get_items(db, skip=skip, limit=limit)
    return items

@router.get("/{item_id}", response_model=Item)
def read_item(item_id: int, db: Session = Depends(get_db)):
    db_item = ItemCRUD.get_item(db, item_id=item_id)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@router.put("/{item_id}", response_model=Item)
def update_item(item_id: int, item_update: ItemUpdate, db: Session = Depends(get_db)):
    db_item = ItemCRUD.update_item(db, item_id=item_id, item_update=item_update)
    if db_item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@router.delete("/{item_id}", response_model=Message)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    success = ItemCRUD.delete_item(db, item_id=item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Item not found")
    return Message(message="Item deleted successfully")
