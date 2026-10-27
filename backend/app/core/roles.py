from typing import Optional

from app.models.user import User

# Same levels as the app's AuthController.getRoleLevel.
ROLE_LEVELS = {
    "Dev Admin": 6,
    "Developer": 6,
    "Principal": 5,
    "College Admin": 4,
    "Admin": 4,
    "HoD": 3,
    "Teacher": 2,
    "Student": 1,
}

STAFF_ROLES = ("Dev Admin", "Developer", "College Admin", "Principal", "HoD", "Teacher")
EXECUTIVE_ROLES = ("Dev Admin", "Developer", "College Admin", "Admin", "Principal")


def role_name(user: Optional[User]) -> str:
    return user.role.name if user is not None and user.role else "Student"


def role_level(name: Optional[str]) -> int:
    return ROLE_LEVELS.get(name or "Student", 1)


def is_staff(user: Optional[User]) -> bool:
    return user is not None and role_name(user) in STAFF_ROLES


def is_dev_admin(user: Optional[User]) -> bool:
    return user is not None and role_level(role_name(user)) == ROLE_LEVELS["Dev Admin"]
