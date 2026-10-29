from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.ai_schema import (
    AiChatRequest, AiChatResponse, MatchedAnnouncementItem,
    AiDraftRequest, AiDraftResponse,
    AiPriorityRequest, AiPriorityResponse,
    AiSummarizeRequest, AiSummarizeResponse,
    AiEmergencyRequest, AiEmergencyResponse,
    AiSpamRequest, AiSpamResponse,
    AiValidateRequest, AiValidateResponse,
    AiDuplicateRequest, AiDuplicateResponse,
    AiStatusResponse, AiTrainResponse,
)
from app.core.dependencies import get_current_user, require_roles
from app.core.throttle import check_ai_quota
from app.core.roles import role_name
from app.models.user import User
from app.services.ai_service import AIService

# Every AI route needs a signed-in user: they call paid-quota models and can read campus data.
_HEAVY_AI_PATHS = ("/ai/chat", "/ai/draft", "/ai/synthesize")


def _ai_caller(request: Request, current_user: User = Depends(get_current_user)) -> User:
    """Every AI route needs a signed-in user, and POSTs count towards that user's AI quota."""
    if request.method == "POST":
        check_ai_quota(int(current_user.id), heavy=request.url.path.endswith(_HEAVY_AI_PATHS))
    return current_user


router = APIRouter(prefix="/ai", tags=["EchoSphere AI"], dependencies=[Depends(_ai_caller)])


def _caller_profile(user: User) -> Dict[str, Optional[str]]:
    """Who is asking, taken from the sign-in token only (never from the request body)."""
    dept = user.department
    return {
        "full_name": user.full_name,
        "user_role": role_name(user),
        "department": (dept.code or dept.name) if dept else None,
        "usn_or_emp_id": user.usn or user.employee_id,
    }


@router.get("/status", response_model=AiStatusResponse)
def ai_status():
    """Return status of AI engine, model in use, and local ML health."""
    return AiStatusResponse(**AIService.get_status())

@router.post("/train", response_model=AiTrainResponse)
def ai_train(
    current_user: User = Depends(
        require_roles("Dev Admin", "Developer", "College Admin", "Principal")
    )
):
    """Train or retrain local Campus ML models."""
    res = AIService.train_models()
    return AiTrainResponse(**res)

@router.get("/router/status")
def ai_router_status():
    """Return real-time metrics across Gemma, Cloudflare LLaMA, Gemini, and Campus ML."""
    from app.services.model_router import ModelRouter
    return ModelRouter.get_instance().get_router_status()

@router.post("/chat", response_model=AiChatResponse)
def ai_chat(
    req: AiChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        caller = _caller_profile(current_user)
        res = AIService.process_chat(
            prompt=req.prompt,
            user_role=caller["user_role"],
            department=caller["department"],
            full_name=caller["full_name"],
            usn_or_emp_id=caller["usn_or_emp_id"],
            db=db,
            history=req.history,
            session_id=req.session_id
        )
        matched = [MatchedAnnouncementItem(**m) for m in res.get("matched_announcements", [])]
        return AiChatResponse(
            response=res["response"],
            category_badge=res["category_badge"],
            context_badge=res.get("context_badge"),
            suggested_actions=res.get("suggested_actions", []),
            navigation_target=res.get("navigation_target"),
            matched_announcements=matched,
            model_used=res.get("model_used", "EchoSphere Campus ML Engine (Local)"),
            copilot_action=res.get("copilot_action")
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/draft", response_model=AiDraftResponse)
def ai_draft(req: AiDraftRequest):
    try:
        res = AIService.draft_announcement(
            topic=req.topic,
            category=req.category or "Academics",
            target_role=req.target_role or "STUDENT",
            department=req.department
        )
        return AiDraftResponse(
            title=res["title"],
            content=res["content"],
            suggested_priority=res["suggested_priority"],
            suggested_category=res["suggested_category"]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/priority", response_model=AiPriorityResponse)
def ai_priority(req: AiPriorityRequest, current_user: User = Depends(get_current_user)):
    try:
        res = AIService.recommend_priority(
            title=req.title,
            content=req.content,
            user_role=role_name(current_user)
        )
        return AiPriorityResponse(
            priority=res["priority"],
            category=res["category"],
            reasoning=res["reasoning"],
            is_allowed=res.get("is_allowed", True)
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/summarize", response_model=AiSummarizeResponse)
def ai_summarize(req: AiSummarizeRequest):
    try:
        summary = AIService.summarize(content=req.content)
        return AiSummarizeResponse(
            summary=summary,
            model_used="EchoSphere Campus ML Engine (Local)"
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/emergency", response_model=AiEmergencyResponse)
def ai_emergency(req: AiEmergencyRequest, current_user: User = Depends(get_current_user)):
    try:
        # Whether it is an emergency does not depend on who asks; whether they may publish one does.
        res = AIService.recommend_priority("", req.text, user_role=role_name(current_user))
        return AiEmergencyResponse(
            is_emergency=res["is_emergency"],
            reason=res["reasoning"],
            can_publish_emergency=res["can_publish_emergency"]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/spam", response_model=AiSpamResponse)
def ai_spam(req: AiSpamRequest):
    try:
        res = AIService.check_spam(text=req.text)
        return AiSpamResponse(
            is_spam=res["is_spam"],
            reason=res["reason"],
            flags=res.get("flags", [])
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/validate", response_model=AiValidateResponse)
def ai_validate(req: AiValidateRequest):
    try:
        res = AIService.validate_content(title=req.title or "", text=req.text)
        return AiValidateResponse(
            is_valid=res["is_valid"],
            missing_fields=res.get("missing_fields", []),
            reason=res["reason"],
            suggestion=res.get("suggestion")
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/duplicate", response_model=AiDuplicateResponse)
def ai_duplicate(req: AiDuplicateRequest, db: Session = Depends(get_db)):
    try:
        res = AIService.check_duplicate(
            new_title=req.new_title,
            new_text=req.new_text,
            department=req.department,
            db=db
        )
        return AiDuplicateResponse(
            is_duplicate=res["is_duplicate"],
            similarity_score=res["similarity_score"],
            matched_title=res.get("matched_title"),
            reason=res["reason"]
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/synthesize")
def ai_synthesize_speech(req: Dict[str, Any], request: Request):
    """
    Synthesizes speech for arbitrary text using Kokoro-82M and Microsoft Edge-TTS neural voices
    (with gTTS and pyttsx3 offline fallbacks).
    """
    from app.services.tts_service import synthesize_text_audio
    text = str(req.get("text") or "")
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Text is required")
    gender = str(req.get("gender") or "female")
    accent = str(req.get("accent") or "american")
    voice_preset: Optional[str] = str(req["voice_preset"]) if req.get("voice_preset") else None
    base_url = str(request.base_url).rstrip("/")
    res = synthesize_text_audio(
        text=text,
        gender=gender,
        accent=accent,
        voice_preset=voice_preset,
    )
    return {
        "status": "ready",
        "audio_url": f"{base_url}{res['url_path']}",
        "file_name": res["file_name"],
        "engine": res.get("engine", "Neural Speech"),
        "type": res.get("type", "mp3"),
        "duration_sec": res.get("duration_sec"),
    }

