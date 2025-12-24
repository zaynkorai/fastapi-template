import uuid
from typing import Any

from sqlmodel import Session, select

from app.core.security import get_password_hash, verify_password
from app.models import Item, ItemCreate, ItemUpdate, User, UserCreate, UserUpdate, Team, TeamCreate, UserTeamLink


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": get_password_hash(user_create.password)}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> Any:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    session_user = session.exec(statement).first()
    return session_user


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = get_user_by_email(session=session, email=email)
    if not db_user:
        return None
    if not verify_password(password, db_user.hashed_password):
        return None
    return db_user


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID, team_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id, "team_id": team_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def get_items_by_team(
    *, session: Session, team_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Item]:
    statement = select(Item).where(Item.team_id == team_id).offset(skip).limit(limit)
    return session.exec(statement).all()


def get_item_by_team(*, session: Session, team_id: uuid.UUID, item_id: uuid.UUID) -> Item | None:
    statement = select(Item).where(Item.team_id == team_id, Item.id == item_id)
    return session.exec(statement).first()


def update_item(*, session: Session, db_item: Item, item_in: ItemUpdate) -> Any:
    item_data = item_in.model_dump(exclude_unset=True)
    db_item.sqlmodel_update(item_data)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def create_team(*, session: Session, team_in: TeamCreate, user_id: uuid.UUID) -> Team:
    db_obj = Team.model_validate(team_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    # Link the creating user to the new team
    user_team_link = UserTeamLink(user_id=user_id, team_id=db_obj.id)
    session.add(user_team_link)
    session.commit()
    session.refresh(user_team_link)
    return db_obj


def get_team(*, session: Session, team_id: uuid.UUID) -> Team | None:
    statement = select(Team).where(Team.id == team_id)
    return session.exec(statement).first()


def get_team_by_name(*, session: Session, name: str) -> Team | None:
    statement = select(Team).where(Team.name == name)
    return session.exec(statement).first()


def get_teams_for_user(*, session: Session, user_id: uuid.UUID) -> list[Team]:
    statement = select(Team).join(UserTeamLink).where(UserTeamLink.user_id == user_id)
    return session.exec(statement).all()


def add_user_to_team(*, session: Session, team: Team, user: User) -> Team:
    user_team_link = UserTeamLink(user_id=user.id, team_id=team.id)
    session.add(user_team_link)
    session.commit()
    session.refresh(user_team_link)
    session.refresh(team)  # Refresh team to reflect new user
    return team


def remove_user_from_team(*, session: Session, team: Team, user: User) -> Team:
    statement = select(UserTeamLink).where(
        UserTeamLink.user_id == user.id, UserTeamLink.team_id == team.id
    )
    user_team_link = session.exec(statement).first()
    if user_team_link:
        session.delete(user_team_link)
        session.commit()
    session.refresh(team)  # Refresh team to reflect user removal
    return team
