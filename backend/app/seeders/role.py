from sqlalchemy.orm import Session

from app.models.role import Role

DEFAULT_ROLES = [
    "Dev Admin",
    "College Admin",
    "Principal",
    "HoD",
    "Teacher",
    "Student",
]


def seed_roles(db: Session) -> None:
    """
    Inserts the default roles into the database.

    Safe to execute multiple times.
    Existing roles will not be inserted again.
    """

    for role_name in DEFAULT_ROLES:
        role = db.query(Role).filter(Role.name == role_name).first()

        if role is None:
            db.add(
                Role(
                    name=role_name,
                )
            )

    db.commit()
