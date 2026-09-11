from enum import Enum


class AnnouncementStatus(str, Enum):
    DRAFT = "Draft"
    PENDING_APPROVAL = "Pending Approval"
    SCHEDULED = "Scheduled"
    PUBLISHED = "Published"
    ARCHIVED = "Archived"
    REJECTED = "Rejected"


class AnnouncementPriority(str, Enum):
    LOW = "Low"
    NORMAL = "Normal"
    HIGH = "High"


class EmergencyLevel(str, Enum):
    NORMAL = "Normal"
    EMERGENCY = "Emergency"
