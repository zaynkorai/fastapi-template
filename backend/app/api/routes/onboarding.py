from typing import Any, List
import uuid

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from app.api.deps import SessionDep, CurrentUser
from app.models import Team, TeamCreate, TeamPublic, User, Message
from app import crud

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


def get_current_user_not_onboarded(
    session: SessionDep, current_user: CurrentUser
) -> User:
    user_teams = crud.get_teams_for_user(session=session, user_id=current_user.id)
    if user_teams:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already part of one or more teams and has completed onboarding.",
        )
    return current_user

CurrentUserNotOnboarded = Depends(get_current_user_not_onboarded)


@router.post("/create_team", response_model=TeamPublic)
def create_team_onboarding(
    *,
    session: SessionDep,
    current_user_not_onboarded: Annotated[User, CurrentUserNotOnboarded],
    team_in: TeamCreate,
) -> Any:
    """
    Allows a user who is not yet part of any team to create their first team.
    """
    team = crud.get_team_by_name(session=session, name=team_in.name)
    if team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team with this name already exists in the system.",
        )
    
    team = crud.create_team(session=session, team_in=team_in, user_id=current_user_not_onboarded.id)
    return team


@router.post("/join_team", response_model=TeamPublic)
def join_team_onboarding(
    *,
    session: SessionDep,
    current_user_not_onboarded: Annotated[User, CurrentUserNotOnboarded],
    team_id: uuid.UUID,
) -> Any:
    """
    Allows a user who is not yet part of any team to join an existing team.
    """
    team = crud.get_team(session=session, team_id=team_id)
    if not team:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team not found.")
    
    # Check if user is already in the team (though CurrentUserNotOnboarded should prevent this)
    if current_user_not_onboarded in team.users:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member of this team.")

    team = crud.add_user_to_team(session=session, team=team, user=current_user_not_onboarded)
    return team