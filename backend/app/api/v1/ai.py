from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.ai_schema import (
    AiChatRequest, AiChatResponse, MatchedAnnouncementItem,
    AiDraftRequest, AiDraftResponse,
    AiPriorityRequest, AiPriorityResponse,
    AiSummarizeRequest, AiSummarizeResponse,
    AiExpandRequest, AiExpandResponse,
    AiGrammarRequest, AiGrammarResponse,
    AiEmergencyRequest, AiEmergencyResponse,
    AiSpamRequest, AiSpamResponse,
    AiValidateRequest, AiValidateResponse,
    AiDuplicateRequest, AiDuplicateResponse,
    AiClassifyRequest, AiClassifyResponse,
    AiIntentRequest, AiIntentResponse,
    AiStatusResponse, AiTrainResponse
)
from app.core.dependencies import require_roles
from app.models.user import User
from app.services.ai_service import AIService
from app.services.campus_ml_engine import CampusMLEngine

router = APIRouter(prefix="/ai", tags=["EchoSphere AI"])

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
def ai_chat(req: AiChatRequest, db: Session = Depends(get_db)):
    try:
        res = AIService.process_chat(
            prompt=req.prompt,
            user_role=req.user_role or "STUDENT",
            department=req.department,
            full_name=req.full_name,
            usn_or_emp_id=req.usn_or_emp_id,
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

@router.post("/copilot/chat")
def ai_copilot_chat(req: Dict[str, Any]):
    """
    CopilotKit Agent Protocol Endpoint.
    Processes conversational instructions with active app state and dispatches in-app actions.
    """
    from app.services.copilot_runtime import CopilotRuntime
    try:
        message = req.get("message", "")
        app_state = req.get("app_state", {})
        user_role = req.get("user_role", "STUDENT")
        department = req.get("department", "CSE")
        full_name = req.get("full_name", "Campus Member")
        history = req.get("history", [])

        res = CopilotRuntime.process_copilot_request(
            message=message,
            app_state=app_state,
            user_role=user_role,
            department=department,
            full_name=full_name,
            history=history
        )
        return res
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
def ai_priority(req: AiPriorityRequest):
    try:
        res = AIService.recommend_priority(
            title=req.title,
            content=req.content,
            user_role=req.user_role or "STUDENT"
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
        return AiSummarizeResponse(summary=summary)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/expand", response_model=AiExpandResponse)
def ai_expand(req: AiExpandRequest):
    try:
        expanded = AIService.expand_text(text=req.text, category=req.category or "Academics")
        return AiExpandResponse(original=req.text, expanded_text=expanded)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/grammar", response_model=AiGrammarResponse)
def ai_grammar(req: AiGrammarRequest):
    try:
        res = AIService.check_grammar(text=req.text)
        return AiGrammarResponse(
            original=res["original"],
            corrected_text=res["corrected_text"],
            improvements=res.get("improvements", [])
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.post("/emergency", response_model=AiEmergencyResponse)
def ai_emergency(req: AiEmergencyRequest):
    try:
        res = AIService.recommend_priority("Check Emergency", req.text, user_role=req.user_role or "STUDENT")
        is_em = res["priority"] == "EMERGENCY"
        return AiEmergencyResponse(
            is_emergency=is_em,
            reason=res["reasoning"],
            can_publish_emergency=res.get("is_allowed", False)
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

@router.post("/classify", response_model=AiClassifyResponse)
def ai_classify(req: AiClassifyRequest):
    res = AIService.recommend_priority("Notice", req.announcement)
    return AiClassifyResponse(category=res["category"], priority=res["priority"])

@router.post("/intent", response_model=AiIntentResponse)
def ai_intent(req: AiIntentRequest):
    intent, _ = CampusMLEngine.get_instance().predict_intent(req.question)
    return AiIntentResponse(intent=intent.lower())
