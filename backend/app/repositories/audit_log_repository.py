from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


from typing import Any, Optional

def create_audit_log(
    db: Session,
    user_id: Any,
    action: str,
    entity: str,
    entity_id: Any,
    description: str | None = None,
) -> AuditLog:
    """
    Create a new audit log entry.
    """

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        description=description,
    )

    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)

    return audit_log


def get_all_audit_logs(
    db: Session,
) -> list[AuditLog]:
    """
    Retrieve all audit logs ordered by newest first.
    """

    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()


def get_audit_log_by_id(
    db: Session,
    audit_log_id: int,
) -> AuditLog | None:
    """
    Retrieve a single audit log by its ID.
    """

    return db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()
