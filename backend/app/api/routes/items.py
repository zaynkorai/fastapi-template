import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import func, select

from app import crud
from app.api.deps import CurrentUser, SessionDep, CurrentTeam
from app.models import Item, ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message, Team

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=ItemsPublic)
def read_items(
    session: SessionDep,
    current_user: CurrentUser,
    current_team: CurrentTeam,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve items.
    """
    if current_user.is_superuser:
        count_statement = select(func.count()).select_from(Item)
        count = session.exec(count_statement).one()
        statement = select(Item).offset(skip).limit(limit)
        items = session.exec(statement).all()
    else:
        # Filter items by current_user AND current_team
        count_statement = (
            select(func.count())
            .select_from(Item)
            .where(Item.owner_id == current_user.id, Item.team_id == current_team.id)
        )
        count = session.exec(count_statement).one()
        statement = (
            select(Item)
            .where(Item.owner_id == current_user.id, Item.team_id == current_team.id)
            .offset(skip)
            .limit(limit)
        )
        items = session.exec(statement).all()

    return ItemsPublic(data=items, count=count)


@router.get("/{id}", response_model=ItemPublic)
def read_item(
    session: SessionDep,
    current_user: CurrentUser,
    current_team: CurrentTeam,
    id: uuid.UUID,
) -> Any:
    """
    Get item by ID.
    """
    item = crud.get_item_by_team(session=session, team_id=current_team.id, item_id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (
        item.owner_id != current_user.id or item.team_id != current_team.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    return item


@router.post("/", response_model=ItemPublic)
def create_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    current_team: CurrentTeam,
    item_in: ItemCreate,
) -> Any:
    """
    Create new item.
    """
    item = crud.create_item(
        session=session,
        item_in=item_in,
        owner_id=current_user.id,
        team_id=current_team.id,
    )
    return item


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    current_team: CurrentTeam,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item.
    """
    item = crud.get_item_by_team(session=session, team_id=current_team.id, item_id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (
        item.owner_id != current_user.id or item.team_id != current_team.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    item = crud.update_item(session=session, db_item=item, item_in=item_in)
    return item


@router.delete("/{id}")
def delete_item(
    session: SessionDep,
    current_user: CurrentUser,
    current_team: CurrentTeam,
    id: uuid.UUID,
) -> Message:
    """
    Delete an item.
    """
    item = crud.get_item_by_team(session=session, team_id=current_team.id, item_id=id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (
        item.owner_id != current_user.id or item.team_id != current_team.id
    ):
        raise HTTPException(status_code=400, detail="Not enough permissions")
    session.delete(item)
    session.commit()
    return Message(message="Item deleted successfully")
