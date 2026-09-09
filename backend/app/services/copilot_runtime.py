"""
EchoSphere CopilotKit Agent Runtime
Implements the CopilotKit Agent Protocol for EchoSphere.
Bridges application state (useCopilotReadable) with executable in-app actions (useCopilotAction).
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.services.model_router import ModelRouter
from app.services.ai_text_sanitizer import sanitize_ai_markdown

logger = logging.getLogger("EchoSphere.CopilotRuntime")


class CopilotActionDef(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


# Official EchoSphere CopilotKit Action Definitions
ECHOSPHERE_COPILOT_ACTIONS: List[CopilotActionDef] = [
    CopilotActionDef(
        name="navigate",
        description="Navigate the user to a specific screen or tab in EchoSphere",
        parameters={
            "type": "object",
            "properties": {
                "screen": {
                    "type": "string",
                    "enum": [
                        "home", "notices", "speaker_queue", "announcement_management",
                        "user_management", "profile_settings", "security_preferences", "archive"
                    ],
                    "description": "Destination screen"
                },
                "filter_category": {"type": "string", "description": "Optional category filter to apply"},
                "filter_dept": {"type": "string", "description": "Optional department filter to apply"}
            },
            "required": ["screen"]
        }
    ),
    CopilotActionDef(
        name="create_announcement_draft",
        description="Open announcement creation dialog pre-filled with synthesized title and description",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Official circular headline"},
                "content": {"type": "string", "description": "Structured announcement body"},
                "category": {"type": "string", "description": "Target category (Academics, Examinations, Placements, Events)"},
                "priority": {"type": "string", "enum": ["NORMAL", "HIGH", "EMERGENCY"]},
                "deliver_speaker": {"type": "boolean", "description": "Whether to broadcast via campus smart speakers"}
            },
            "required": ["title", "content"]
        }
    ),
    CopilotActionDef(
        name="toggle_theme",
        description="Toggle between sleek dark glassmorphism and crisp light theme",
        parameters={
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["dark", "light", "toggle"]}
            },
            "required": ["mode"]
        }
    ),
    CopilotActionDef(
        name="control_speaker_queue",
        description="Perform audio playback actions on campus smart speakers (Staff/Admin only)",
        parameters={
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["play", "pause", "resume", "advance", "clear"]},
                "node_id": {"type": "string", "description": "Target speaker node or 'ALL'"}
            },
            "required": ["action"]
        }
    )
]


class CopilotRuntime:
    """
    EchoSphere Copilot Runtime Engine.
    Processes conversational instructions in the context of active app state
    and generates response text along with executable CopilotKit client actions.
    """
    @staticmethod
    def process_copilot_request(
        message: str,
        app_state: Dict[str, Any],
        user_role: str = "STUDENT",
        department: str = "CSE",
        full_name: str = "Campus Member",
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        router = ModelRouter.get_instance()

        # Build rich CopilotKit prompt with system context and available action tools
        actions_schema_str = json.dumps([a.model_dump() for a in ECHOSPHERE_COPILOT_ACTIONS], indent=2)
        system_instruction = (
            f"You are the EchoSphere Copilot, an intelligent in-app companion with direct action-execution capabilities.\n\n"
            f"User Profile & Authority:\n"
            f"- Name: {full_name}\n"
            f"- Role: {user_role}\n"
            f"- Department: {department}\n\n"
            f"Current Application View State:\n"
            f"- Active Route: {app_state.get('active_route', '/home')}\n"
            f"- Current Filter: {app_state.get('current_filter', 'All')}\n"
            f"- Theme: {app_state.get('current_theme', 'dark')}\n\n"
            f"Available Copilot Actions:\n"
            f"{actions_schema_str}\n\n"
            f"Formatting & Execution Rules:\n"
            f"1. When the user requests an action (e.g. 'go to speaker queue', 'filter exam circulars', 'switch to dark mode', 'draft a notice'), "
            f"answer politely and embed the action tag at the end of your response: [[ACTION:action_name:JSON_PARAMETERS]].\n"
            f"2. Strict RBAC: Students can NEVER invoke speaker controls or create announcements.\n"
            f"3. Respond in clean, natural CommonMark Markdown with NO raw asterisk clutter (***) or broken symbol tags (##$, ---)."
        )

        result = router.route_and_generate(
            prompt=message,
            user_role=user_role,
            department=department,
            full_name=full_name,
            system_instruction=system_instruction,
            history=history,
            category_badge="EchoSphere Copilot"
        )

        response_text = result.get("response", "")
        extracted_action: Optional[Dict[str, Any]] = None

        # Parse any [[ACTION:name:params]] tag embedded by the model
        import re
        action_match = re.search(r'\[\[ACTION:([a-zA-Z0-9_]+):(\{.*?\})\]\]', response_text)
        if action_match:
            act_name = action_match.group(1)
            act_params_raw = action_match.group(2)
            try:
                act_params = json.loads(act_params_raw)
                extracted_action = {
                    "action": act_name,
                    "parameters": act_params
                }
                # Strip the raw tag from the user-visible response
                response_text = response_text.replace(action_match.group(0), "").strip()
            except Exception as e:
                logger.debug(f"Error parsing Copilot action payload: {e}")

        # If model used navigation_target instead, map to copilot action
        if not extracted_action and result.get("navigation_target"):
            nav = result["navigation_target"]
            if nav.startswith("nav:hardware:speakers"):
                extracted_action = {"action": "navigate", "parameters": {"screen": "speaker_queue"}}
            elif nav.startswith("action:create_notice"):
                extracted_action = {"action": "create_announcement_draft", "parameters": {"title": "", "content": ""}}
            elif "filter:" in nav:
                category = nav.split(":")[-1]
                extracted_action = {"action": "navigate", "parameters": {"screen": "notices", "filter_category": category}}

        result["response"] = sanitize_ai_markdown(response_text)
        result["copilot_action"] = extracted_action
        return result
