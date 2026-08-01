from sqlalchemy.orm import Session

from app.core.password import hash_password
from app.models.department import Department
from app.models.role import Role
from app.models.user import User


def seed_users(db: Session):
    """
    Seed default users.
    """

    roles = {role.name: role for role in db.query(Role).all()}

    departments = {
        department.code: department for department in db.query(Department).all()
    }

    users = [
        {
            "full_name": "Dev Admin",
            "username": "ESDev01",
            "official_email": "rrakshu60@gmail.com",
            "password": "rakshitha@1228",
            "employee_id": "DEVADM01",
            "role": "Dev Admin",
            "department": None,
        },
        {
            "full_name": "College Administrator",
            "username": "admin",
            "official_email": "admin@echosphere.edu",
            "password": "Admin@123",
            "employee_id": "ADM001",
            "role": "College Admin",
            "department": None,
        },
        {
            "full_name": "College Admin (Primary)",
            "username": "CAdmin",
            "official_email": "cadmin@echosphere.edu",
            "password": "Dbit@ES01",
            "employee_id": "DBITADM001",
            "role": "College Admin",
            "department": None,
        },
        {
            "full_name": "Principal",
            "username": "principal",
            "official_email": "principal@echosphere.edu",
            "password": "Principal@123",
            "employee_id": "PRI001",
            "role": "Principal",
            "department": None,
        },
        {
            "full_name": "CSE HoD",
            "username": "hod_cse",
            "official_email": "hod.cse@echosphere.edu",
            "password": "Hod@123",
            "employee_id": "HOD001",
            "role": "HoD",
            "department": "CSE",
        },
        {
            "full_name": "CSE Teacher",
            "username": "teacher_cse",
            "official_email": "teacher.cse@echosphere.edu",
            "password": "Teacher@123",
            "employee_id": "TCH001",
            "role": "Teacher",
            "department": "CSE",
        },
        {
            "full_name": "Student One",
            "username": "student1",
            "official_email": "student1@echosphere.edu",
            "password": "Student@123",
            "usn": "1EC22CS001",
            "semester": 5,
            "section": "A",
            "role": "Student",
            "department": "CSE",
        },
        {
            "full_name": "Rakshitha S",
            "username": "1db23ci079",
            "official_email": "1db23ci079@echosphere.edu",
            "password": "rakshitha@1228",
            "usn": "1DB23CI079",
            "semester": 5,
            "section": "A",
            "role": "Student",
            "department": "AIML",
        },
        {
            "full_name": "Dr. B Kursheed",
            "username": "dbitaimlt022022",
            "official_email": "b.kursheed@echosphere.edu",
            "password": "Kursh@2022",
            "employee_id": "DBITAIMLT022022",
            "role": "Teacher",
            "department": "AIML",
        },
    ]

    for data in users:
        existing_user = (
            db.query(User).filter(User.official_email == data["official_email"]).first()
        )

        if existing_user:
            continue

        role = roles.get(data["role"])

        if role is None:
            raise ValueError(f"Role '{data['role']}' not found.")

        department = None

        if data["department"]:
            department = departments.get(data["department"])

            if department is None:
                raise ValueError(f"Department '{data['department']}' not found.")

        user = User(
            full_name=data["full_name"],
            username=data["username"],
            official_email=data["official_email"],
            password_hash=hash_password(data["password"]),
            employee_id=data.get("employee_id"),
            usn=data.get("usn"),
            semester=data.get("semester"),
            section=data.get("section"),
            role_id=role.id,
            department_id=department.id if department else None,
        )

        db.add(user)

    db.commit()

    print("Users seeded successfully.")
