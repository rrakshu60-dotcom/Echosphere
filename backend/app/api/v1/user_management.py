from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.schemas.user_management import UserCreate, UserResponse, UserUpdateRole
from app.services.user_management_service import UserManagementService

router = APIRouter(prefix="/users", tags=["User Management Module"])

@router.get("/", response_model=List[UserResponse])
def list_users(
    department_id: Optional[int] = None,
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal", "HoD")),
    db: Session = Depends(get_db),
):
    users = UserManagementService.list_users(db=db, department_id=department_id)
    result = []
    for u in users:
        result.append(UserResponse(
            id=u.id,
            full_name=u.full_name,
            official_email=u.official_email,
            usn=u.usn,
            employee_id=u.employee_id,
            role=u.role.name if u.role else "Student",
            department_id=u.department_id,
            is_active=u.is_active if hasattr(u, 'is_active') else True,
        ))
    return result

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreate,
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal")),
    db: Session = Depends(get_db),
):
    user = UserManagementService.create_user(
        db=db,
        full_name=req.full_name,
        official_email=req.official_email,
        password=req.password,
        role_name=req.role_name or "Student",
        username=req.username,
        department_id=req.department_id,
        usn=req.usn,
        employee_id=req.employee_id,
        semester=req.semester,
        section=req.section,
    )
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        official_email=user.official_email,
        usn=user.usn,
        employee_id=user.employee_id,
        role=user.role.name if user.role else "Student",
        department_id=user.department_id,
        is_active=user.is_active if hasattr(user, 'is_active') else True,
    )

@router.get("/{user_id}", response_model=UserResponse)
def get_user_detail(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = UserManagementService.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        official_email=user.official_email,
        usn=user.usn,
        employee_id=user.employee_id,
        role=user.role.name if user.role else "Student",
        department_id=user.department_id,
        is_active=user.is_active if hasattr(user, 'is_active') else True,
    )

@router.put("/{user_id}", response_model=UserResponse)
def update_user_role(
    user_id: int,
    req: UserUpdateRole,
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal")),
    db: Session = Depends(get_db),
):
    updated = UserManagementService.update_user(
        db=db,
        user_id=user_id,
        role_id=req.role_id,
        role_name=req.role_name,
        department_id=req.department_id,
        is_active=req.is_active,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return UserResponse(
        id=updated.id,
        full_name=updated.full_name,
        official_email=updated.official_email,
        usn=updated.usn,
        employee_id=updated.employee_id,
        role=updated.role.name if updated.role else "Student",
        department_id=updated.department_id,
        is_active=updated.is_active if hasattr(updated, 'is_active') else True,
    )

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: int,
    current_user: User = Depends(require_roles("Dev Admin", "Developer", "College Admin", "Principal")),
    db: Session = Depends(get_db),
):
    if current_user.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own active session account.")
    success = UserManagementService.delete_user(db=db, user_id=user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return {"message": "User deleted successfully", "id": user_id}
