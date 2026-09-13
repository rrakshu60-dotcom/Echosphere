from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.repositories.audit_log_repository import (
    create_audit_log,
    get_all_audit_logs,
    get_audit_log_by_id,
)


from typing import Any, Optional

def create_audit_log_service(
    db: Session,
    user_id: Any,
    action: str,
    entity: str,
    entity_id: Any,
    description: str | None = None,
) -> AuditLog:
    """
    Create an audit log entry.
    """

    return create_audit_log(
        db=db,
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        description=description,
    )


def get_all_audit_logs_service(
    db: Session,
) -> list[AuditLog]:
    """
    Retrieve all audit logs.
    """

    return get_all_audit_logs(db)


def get_audit_log_by_id_service(
    db: Session,
    audit_log_id: int,
) -> AuditLog | None:
    """
    Retrieve a specific audit log.
    """

    return get_audit_log_by_id(
        db=db,
        audit_log_id=audit_log_id,
    )
