from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.user import User


def get_user_by_email(
    db: Session,
    official_email: str,
) -> User | None:
    """
    Fetch a user by official email.
    """

    return (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.department))
        .filter(User.official_email == official_email)
        .first()
    )


def get_user_by_identifier(
    db: Session,
    identifier: str,
):
    """
    Finds a user using either employee ID or email.
    """

    return (
        db.query(User)
        .options(joinedload(User.role), joinedload(User.department))
        .filter(
            or_(
                User.employee_id == identifier,
                User.official_email == identifier,
            )
        )
        .first()
    )


def update_user(
    db: Session,
    user: User,
):
    """
    Persists changes made to a user.
    """

    db.commit()
    db.refresh(user)
    return user
