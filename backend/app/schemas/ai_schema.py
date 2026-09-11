from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class AiChatRequest(BaseModel):
    prompt: str
    user_role: Optional[str] = "STUDENT"
    department: Optional[str] = None
    full_name: Optional[str] = None
    user_id: Optional[int] = None
    usn_or_emp_id: Optional[str] = None
    context: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None

class MatchedAnnouncementItem(BaseModel):
    id: int
    title: str
    category: str
    priority: str
    department: str
    content: str
    created_at: str

class AiChatResponse(BaseModel):
    response: str
    category_badge: str = "EchoSphere AI"
    context_badge: Optional[str] = None
    suggested_actions: List[str] = []
    navigation_target: Optional[str] = None
    matched_announcements: List[MatchedAnnouncementItem] = []
    model_used: Optional[str] = "EchoSphere Campus ML Engine (Local)"
    copilot_action: Optional[Dict[str, Any]] = None

class AiTrainResponse(BaseModel):
    status: str
    intents_trained: int
    intent_samples: int
    kb_documents: int

class AiStatusResponse(BaseModel):
    engine: str
    gemini_model: str
    is_gemini_available: bool
    is_cloudflare_available: Optional[bool] = False
    is_qwen_available: Optional[bool] = False
    local_ml_available: bool
    kb_indexed_documents: int
    router_metrics: Optional[Dict[str, Any]] = None

class AiDraftRequest(BaseModel):
    topic: str
    category: Optional[str] = "Academics"
    target_role: Optional[str] = "STUDENT"
    department: Optional[str] = None

class AiDraftResponse(BaseModel):
    title: str
    content: str
    suggested_priority: str
    suggested_category: str

class AiPriorityRequest(BaseModel):
    title: str
    content: str
    user_role: Optional[str] = "STUDENT"

class AiPriorityResponse(BaseModel):
    priority: str
    category: str
    reasoning: str
    is_allowed: bool = True

class AiSummarizeRequest(BaseModel):
    content: str

class AiSummarizeResponse(BaseModel):
    summary: str
    model_used: Optional[str] = "Fine-Tuned Qwen 2.5 3B (Local Campus Model)"

class AiExpandRequest(BaseModel):
    text: str
    category: Optional[str] = "Academics"

class AiExpandResponse(BaseModel):
    original: str
    expanded_text: str

class AiGrammarRequest(BaseModel):
    text: str

class AiGrammarResponse(BaseModel):
    original: str
    corrected_text: str
    improvements: List[str] = []

class AiEmergencyRequest(BaseModel):
    text: str
    user_role: Optional[str] = "STUDENT"

class AiEmergencyResponse(BaseModel):
    is_emergency: bool
    reason: str
    can_publish_emergency: bool = False

class AiSpamRequest(BaseModel):
    text: str

class AiSpamResponse(BaseModel):
    is_spam: bool
    reason: str
    flags: List[str] = []

class AiValidateRequest(BaseModel):
    title: Optional[str] = ""
    text: str

class AiValidateResponse(BaseModel):
    is_valid: bool
    missing_fields: List[str] = []
    reason: str
    suggestion: Optional[str] = None

class AiDuplicateRequest(BaseModel):
    new_title: str
    new_text: str
    department: Optional[str] = None

class AiDuplicateResponse(BaseModel):
    is_duplicate: bool
    similarity_score: float
    matched_title: Optional[str] = None
    reason: str

class AiClassifyRequest(BaseModel):
    announcement: str

class AiClassifyResponse(BaseModel):
    category: str
    priority: str

class AiIntentRequest(BaseModel):
    question: str

class AiIntentResponse(BaseModel):
    intent: str

class CopilotChatRequest(BaseModel):
    message: str
    app_state: Optional[Dict[str, Any]] = None
    user_role: Optional[str] = "STUDENT"
    department: Optional[str] = "CSE"
    full_name: Optional[str] = "Campus Member"
    history: Optional[List[Dict[str, Any]]] = None

class CopilotChatResponse(BaseModel):
    response: str
    copilot_action: Optional[Dict[str, Any]] = None
    category_badge: Optional[str] = "EchoSphere Copilot"
    context_badge: Optional[str] = None
    model_used: Optional[str] = None
    suggested_actions: List[str] = []
    navigation_target: Optional[str] = None


class ScheduleConflictCheckRequest(BaseModel):
    title: str
    content: str
    scheduled_at: Optional[str] = None
    category: Optional[str] = None
    exclude_notice_id: Optional[int] = None


class ConflictDetail(BaseModel):
    conflicting_notice_id: int
    conflicting_title: str
    conflicting_department: str
    conflicting_venue: str
    conflicting_time: str
    conflict_type: str  # "venue_collision" | "academic_clash"
    conflict_message: str


class SuggestedAlternativeSlot(BaseModel):
    label: str
    start_time: str
    end_time: str
    venue: str
    slot_type: str  # "same_day_later" | "same_day_morning" | "next_day" | "alternative_venue"


class ScheduleConflictCheckResponse(BaseModel):
    has_conflict: bool
    draft_event: Optional[Dict[str, Any]] = None
    conflicts: List[ConflictDetail] = []
    suggested_alternatives: List[SuggestedAlternativeSlot] = []


class AudienceCheckRequest(BaseModel):
    title: str
    content: str
    selected_audience: str


class AudienceCheckResponse(BaseModel):
    has_mismatch: bool
    detected_audience: Optional[str] = None
    suggested_audiences: List[str] = []
    warning_message: Optional[str] = None
    mismatch_type: Optional[str] = None


class UserProfileContext(BaseModel):
    role: Optional[str] = "Student"
    department: Optional[str] = None
    semester: Optional[int] = None
    usn: Optional[str] = None


class NoticeItemContext(BaseModel):
    id: int
    title: str
    description: Optional[str] = ""
    department: Optional[str] = "General"
    target_audience: Optional[str] = "Entire College"
    category: Optional[str] = "General"
    priority: Optional[str] = "NORMAL"
    emergency_level: Optional[str] = "NORMAL"
    created_at: Optional[str] = None


class RelevanceScoreRequest(BaseModel):
    user_profile: UserProfileContext
    announcements: List[NoticeItemContext]


class RelevanceScoreItem(BaseModel):
    announcement_id: int
    score: float
    is_highly_relevant: bool
    reasons: List[str] = []


class RelevanceScoreResponse(BaseModel):
    scores: List[RelevanceScoreItem]


class AnnouncementTranslationRequest(BaseModel):
    target_language: str = "kn"
    title: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None


class AnnouncementTranslationResponse(BaseModel):
    target_language: str
    language_name: str
    native_name: str
    translated_title: str
    translated_content: str
    translated_summary: Optional[str] = None


class VoiceNoticeRequest(BaseModel):
    audio_base64: Optional[str] = None
    audio_format: Optional[str] = "m4a"
    raw_transcript: Optional[str] = None


class VoiceNoticeResponse(BaseModel):
    title: str
    content: str
    suggested_category: str = "Academic"
    suggested_priority: str = "NORMAL"
    suggested_audience: str = "Entire College"
    extracted_event: Optional[Dict[str, Any]] = None
    transcription: str


class DocumentOcrRequest(BaseModel):
    file_base64: str
    mime_type: Optional[str] = "image/jpeg"
    filename: Optional[str] = "circular.jpg"


class DocumentOcrResponse(BaseModel):
    title: str
    content: str
    suggested_category: str = "Academic"
    suggested_priority: str = "NORMAL"
    suggested_audience: str = "Entire College"
    reference_number: Optional[str] = None
    extracted_event: Optional[Dict[str, Any]] = None
    raw_text: Optional[str] = None


