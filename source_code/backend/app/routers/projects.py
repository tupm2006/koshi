from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models.entities import Project, User, ProjectMember, ProjectMemberRoleEnum
from app.schemas.project import (
    ProjectCreate,
    ProjectOut,
    ProjectMemberAdd,
    ProjectMemberUpdate,
    ProjectMemberOut,
)
from app.security import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])

def check_project_admin(project_id: int, user_id: int, db: Session) -> bool:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return False
    if project.owner_id == user_id:
        return True
    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.role.in_([ProjectMemberRoleEnum.OWNER, ProjectMemberRoleEnum.PM])
    ).first()
    return membership is not None

@router.get("", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Project).all()

@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(req: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    project = Project(
        name=req.name,
        description=req.description,
        owner_id=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Automatically assign the creator as OWNER in project_members
    membership = ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        role=ProjectMemberRoleEnum.OWNER
    )
    db.add(membership)
    db.commit()

    return project

@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@router.get("/{project_id}/members", response_model=List[ProjectMemberOut])
def list_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    members = db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()
    return members

@router.post("/{project_id}/members", response_model=ProjectMemberOut, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: int,
    req: ProjectMemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_project_admin(project_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owners or project managers can add team members"
        )

    target_user = db.query(User).filter(User.id == req.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == req.user_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User is already a member of this project")

    membership = ProjectMember(
        project_id=project_id,
        user_id=req.user_id,
        role=req.role or ProjectMemberRoleEnum.MEMBER
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership

@router.patch("/{project_id}/members/{user_id}", response_model=ProjectMemberOut)
def update_project_member_role(
    project_id: int,
    user_id: int,
    req: ProjectMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    if not check_project_admin(project_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owners or project managers can modify roles"
        )

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Project member not found")

    membership.role = req.role
    db.commit()
    db.refresh(membership)
    return membership

@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    # Allow users to leave project themselves or admins to remove others
    is_self = current_user.id == user_id
    if not is_self and not check_project_admin(project_id, current_user.id, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project admins can remove other members"
        )

    membership = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id
    ).first()
    if not membership:
        raise HTTPException(status_code=404, detail="Project member not found")

    db.delete(membership)
    db.commit()
    return None
