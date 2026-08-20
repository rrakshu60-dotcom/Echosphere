from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.database import get_db
from app.models.user import User
from app.schemas.audit_log_schema import AuditLogResponse
from app.services.audit_log_service import (
    get_all_audit_logs_service,
    get_audit_log_by_id_service,
)

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


@router.get(
    "/",
    response_model=list[AuditLogResponse],
)
def get_all_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Dev Admin",
            "Developer",
            "College Admin",
        )
    ),
):
    return get_all_audit_logs_service(db)


@router.get(
    "/{audit_log_id}",
    response_model=AuditLogResponse,
)
def get_audit_log_by_id(
    audit_log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            "Dev Admin",
            "Developer",
            "College Admin",
        )
    ),
):
    return get_audit_log_by_id_service(
        db=db,
        audit_log_id=audit_log_id,
    )
