from typing import Any, List
import uuid

from fastapi import APIRouter, HTTPException, status
from app.api.deps import SessionDep, CurrentUser, CurrentTeam, get_current_active_superuser
from app.models import Team, TeamCreate, TeamPublic, TeamsPublic, User, Message
from app import crud


router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("/", response_model=TeamPublic)
def create_team(
    *, session: SessionDep, current_user: CurrentUser, team_in: TeamCreate
) -> Any:
    """
    Create new team.
    """
    team = crud.get_team_by_name(session=session, name=team_in.name)
    if team:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Team with this name already exists in the system.",
        )
    
    team = crud.create_team(session=session, team_in=team_in, user_id=current_user.id)
    return team


@router.get("/me", response_model=List[TeamPublic])
def read_my_teams(
    session: SessionDep, current_user: CurrentUser
) -> Any:
    """
    Retrieve teams the current user belongs to.
    """
    teams = crud.get_teams_for_user(session=session, user_id=current_user.id)
    return teams


@router.get("/{team_id}", response_model=TeamPublic)
def read_team(
    session: SessionDep, current_user: CurrentUser, team_id: uuid.UUID
) -> Any:
    """
    Get team by ID.
    """
    team = crud.get_team(session=session, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    user_teams = crud.get_teams_for_user(session=session, user_id=current_user.id)
    if team not in user_teams and not current_user.is_superuser:
        raise HTTPException(status_code=400, detail="Not enough permissions")
    
    return team


@router.post("/{team_id}/add_user/{user_id}", response_model=TeamPublic)
def add_user_to_team(
    *,
    session: SessionDep,
    current_user: CurrentUser, # For authorization check
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Any:
    """
    Add a user to a team.
    Only superusers or existing team members can add users.
    """
    team = crud.get_team(session=session, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    user_to_add = session.get(User, user_id)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User to add not found")
    
    # Check if current_user is superuser or a member of the team
    if not current_user.is_superuser:
        current_user_teams = crud.get_teams_for_user(session=session, user_id=current_user.id)
        if team not in current_user_teams:
            raise HTTPException(status_code=403, detail="Not enough permissions to add user to this team")
    
    # Check if user is already in the team
    if user_to_add in team.users:
        raise HTTPException(status_code=400, detail="User is already a member of this team")

    team = crud.add_user_to_team(session=session, team=team, user=user_to_add)
    return team


@router.delete("/{team_id}/remove_user/{user_id}", response_model=TeamPublic)
def remove_user_from_team(
    *,
    session: SessionDep,
    current_user: CurrentUser, # For authorization check
    team_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Any:
    """
    Remove a user from a team.
    Only superusers or existing team members can remove users.
    """
    team = crud.get_team(session=session, team_id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    
    user_to_remove = session.get(User, user_id)
    if not user_to_remove:
        raise HTTPException(status_code=404, detail="User to remove not found")
    
    # Check if current_user is superuser or a member of the team
    if not current_user.is_superuser:
        current_user_teams = crud.get_teams_for_user(session=session, user_id=current_user.id)
        if team not in current_user_teams:
            raise HTTPException(status_code=403, detail="Not enough permissions to remove user from this team")
            
    # Check if user is actually in the team
    if user_to_remove not in team.users:
        raise HTTPException(status_code=400, detail="User is not a member of this team")

    team = crud.remove_user_from_team(session=session, team=team, user=user_to_remove)
    return team