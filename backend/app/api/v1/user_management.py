from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.dependencies import require_roles
from app.core.roles import ROLE_LEVELS, STAFF_ROLES, is_dev_admin, role_name
from app.models.role import Role
from app.models.user import User
from app.schemas.user_management import UserCreate, UserResponse, UserUpdateRole
from app.services.user_management_service import UserManagementService

router = APIRouter(prefix="/users", tags=["User Management Module"])


# Who may create, change or delete which accounts. Viewing the directory is open to every staff role;
# these rules only apply to changes. HoDs and Teachers are further limited to their own department.
_MANAGEABLE_ROLES = {
    "College Admin": {"HoD", "Teacher", "Student"},
    "Admin": {"HoD", "Teacher", "Student"},
    "Principal": {"HoD", "Teacher", "Student"},
    "HoD": {"Teacher", "Student"},
    "Teacher": {"Student"},
}
_DEPARTMENT_SCOPED_ROLES = {"HoD", "Teacher"}


def _manageable_roles(current_user: User) -> set:
    if is_dev_admin(current_user):
        return set(ROLE_LEVELS)
    return _MANAGEABLE_ROLES.get(role_name(current_user), set())


def _own_department(current_user: User) -> Optional[int]:
    """The department a HoD or Teacher is limited to (None: not department-limited)."""
    if role_name(current_user) not in _DEPARTMENT_SCOPED_ROLES:
        return None
    if not current_user.department_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has no department, so you cannot manage accounts. Ask an administrator to set it.",
        )
    return current_user.department_id


def _check_can_assign_role(current_user: User, new_role: str) -> None:
    if new_role not in _manageable_roles(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not allowed to give the {new_role} role.",
        )


def _check_department(current_user: User, department_id: Optional[int]) -> None:
    own = _own_department(current_user)
    if own is not None and department_id != own:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage accounts in your own department.",
        )


def _check_can_manage(current_user: User, target: User) -> None:
    """Accounts can only be changed or removed by a role allowed to manage them, never by their owner."""
    if target.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot change the role or status of your own account, or delete it.",
        )
    if role_name(target) not in _manageable_roles(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"You are not allowed to manage {role_name(target)} accounts.",
        )
    _check_department(current_user, target.department_id)


@router.get("/", response_model=List[UserResponse])
def list_users(
    department_id: Optional[int] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 250,
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    users = UserManagementService.list_users(
        db=db,
        department_id=department_id,
        role_name=role,
        search=search,
        skip=skip,
        limit=limit,
    )
    result = []
    for u in users:
        dept_name = None
        if hasattr(u, 'department') and u.department:
            dept_name = getattr(u.department, 'name', None) or getattr(u.department, 'code', None)
        result.append(UserResponse(
            id=u.id,
            full_name=u.full_name,
            official_email=u.official_email,
            usn=u.usn,
            employee_id=u.employee_id,
            role=u.role.name if u.role else "Student",
            department_id=u.department_id,
            department=dept_name,
            semester=getattr(u, 'semester', None),
            section=getattr(u, 'section', None),
            is_active=u.is_active if hasattr(u, 'is_active') else True,
        ))
    return result

@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    req: UserCreate,
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    _check_can_assign_role(current_user, req.role_name or "Student")
    department_id = req.department_id
    own = _own_department(current_user)
    if own is not None:
        if department_id is None:
            department_id = own
        _check_department(current_user, department_id)
    user = UserManagementService.create_user(
        db=db,
        full_name=req.full_name,
        official_email=req.official_email,
        password=req.password,
        role_name=req.role_name or "Student",
        username=req.username,
        department_id=department_id,
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
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
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
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    target = UserManagementService.get_user_by_id(db=db, user_id=user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    _check_can_manage(current_user, target)
    if req.role_name:
        _check_can_assign_role(current_user, req.role_name)
    elif req.role_id is not None:
        new_role = db.query(Role).filter(Role.id == req.role_id).first()
        if not new_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown role.")
        _check_can_assign_role(current_user, new_role.name)
    if req.department_id is not None:
        _check_department(current_user, req.department_id)
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
    current_user: User = Depends(require_roles(*STAFF_ROLES)),
    db: Session = Depends(get_db),
):
    target = UserManagementService.get_user_by_id(db=db, user_id=user_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    _check_can_manage(current_user, target)
    success = UserManagementService.delete_user(db=db, user_id=user_id, deleted_by=current_user)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return {"message": "User deleted successfully", "id": user_id}
