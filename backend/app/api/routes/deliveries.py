import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import User, Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message
from sqlalchemy.exc import NoResultFound
import sqlalchemy as sa

router = APIRouter(prefix="/deliveries", tags=["deliveries"])


@router.get("/", response_model=DeliveriesPublic)
def read_items(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve deliveries.
    """
    items_public = ItemsPublic(data=[], count=0)
    if current_user.role == 'admin':
        count_statement = select(func.count()).select_from(Item)
        count = session.exec(count_statement).one()
        statement = select(Item).offset(skip).limit(limit)
        items = session.exec(statement).all()

    else:
        count_statement = (
            select(func.count())
            .select_from(Item)
            .where(Item.owner_id == current_user.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Item)
            .where(Item.owner_id == current_user.id)
            .offset(skip)
            .limit(limit)
        )
        items = session.exec(statement).all()
    
    for item in items:
        item_dict = item.model_dump()
        user = session.get(User, item_dict['owner_id'])
        item_dict["owner_name"] = user.full_name
        items_public.data.append(ItemPublic(**item_dict))
        items_public.count += 1
        
    return items_public


@router.get("/{id}", response_model=ItemPublic)
def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if current_user == 'client' and (item.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")

    item_dict = item.model_dump()
    user = session.get(User, item_dict['owner_id'])
    item_dict["owner_name"] = user.full_name
    # Return the item as ItemPublic
    return ItemPublic(**item_dict)


@router.post("/", response_model=ItemPublic)
def create_item(
    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> Any:
    """
    Create new item.
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=400, detail="Not enough permissions")

    try:
        session.execute(
            sa.select(User).where(User.id == item_in.owner_id)
        ).scalar_one()
    except NoResultFound:
        raise HTTPException(status_code=400, detail=f"Owner with id {item_in.owner_id} does not exist")

    user = session.get(User, item_in.owner_id)
    item = Item.model_validate(item_in, update={"owner_name": user.full_name})
    session.add(item)
    session.commit()
    session.refresh(item)

    return ItemPublic.model_validate(item, update={"owner_name": user.full_name})


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if current_user == 'client' and (item.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    update_dict = item_in.model_dump(exclude_unset=True)
    item.sqlmodel_update(update_dict)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/{id}")
def delete_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an item.
    """
    item = session.get(Item, id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if current_user == 'client' and (item.owner_id != current_user.id):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    session.delete(item)
    session.commit()
    return Message(message="Item deleted successfully")
