from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.user import User

from app.core.password import hash_password
from app.models.role import Role

class UserManagementService:
    @staticmethod
    def list_users(db: Session, department_id: Optional[int] = None) -> List[User]:
        query = db.query(User)
        if department_id:
            query = query.filter(User.department_id == department_id)
        return query.order_by(User.id).all()

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def create_user(
        db: Session,
        full_name: str,
        official_email: str,
        password: str,
        role_name: str = "Student",
        username: Optional[str] = None,
        department_id: Optional[int] = None,
        usn: Optional[str] = None,
        employee_id: Optional[str] = None,
        semester: Optional[int] = None,
        section: Optional[str] = None,
    ) -> User:
        role = db.query(Role).filter(Role.name == role_name).first()
        if not role:
            # Fallback for role alias or default
            role = db.query(Role).filter(Role.name == "Student").first()
            if not role:
                role = db.query(Role).first()
        
        final_username = username or official_email.split("@")[0]
        hashed_pw = hash_password(password)

        if not department_id and usn:
            usn_clean = usn.upper()
            dept_code = "AIML"
            if "CI" in usn_clean or "AI" in usn_clean:
                dept_code = "AIML"
            elif "AD" in usn_clean:
                dept_code = "AIDS"
            elif "IS" in usn_clean:
                dept_code = "ISE"
            elif "CS" in usn_clean:
                dept_code = "CSE"
            elif "EC" in usn_clean:
                dept_code = "ECE"
            elif "EE" in usn_clean:
                dept_code = "EEE"
            elif "ME" in usn_clean:
                dept_code = "ME"
            elif "CV" in usn_clean:
                dept_code = "CIVIL"

            from app.models.department import Department
            dept_obj = db.query(Department).filter(Department.code == dept_code).first()
            if dept_obj:
                department_id = dept_obj.id

        new_user = User(
            full_name=full_name,
            official_email=official_email,
            username=final_username,
            password_hash=hashed_pw,
            role_id=role.id if role else 1,
            department_id=department_id,
            usn=usn,
            employee_id=employee_id,
            semester=semester,
            section=section,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def update_user(
        db: Session,
        user_id: int,
        role_id: Optional[int] = None,
        department_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        role_name: Optional[str] = None,
    ) -> Optional[User]:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        if role_name:
            role = db.query(Role).filter(Role.name == role_name).first()
            if role:
                user.role_id = role.id
        elif role_id is not None:
            user.role_id = role_id

        if department_id is not None:
            user.department_id = department_id
        if is_active is not None and hasattr(user, 'is_active'):
            user.is_active = is_active
        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def delete_user(db: Session, user_id: int) -> bool:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True

