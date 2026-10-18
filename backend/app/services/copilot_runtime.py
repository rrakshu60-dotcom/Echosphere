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
                        "approval_queue", "user_management", "profile", "security_preferences", "archive"
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
    ),
    CopilotActionDef(
        name="set_speaker_volume",
        description="Adjust volume level on campus smart speakers (Staff/Admin only)",
        parameters={
            "type": "object",
            "properties": {
                "node_id": {
                    "type": "string",
                    "description": "Speaker node ID (e.g. '13'), node zone name (e.g. 'Auditorium', 'Corridor'), or 'ALL'"
                },
                "volume": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100,
                    "description": "Target volume percentage from 0 to 100"
                }
            },
            "required": ["volume"]
        }
    ),
    CopilotActionDef(
        name="approve_notice",
        description="Approve a pending campus circular for broadcast and publication (Faculty/HoD/Admin only)",
        parameters={
            "type": "object",
            "properties": {
                "announcement_id": {"type": "integer", "description": "ID of the announcement to approve"},
                "remarks": {"type": "string", "description": "Optional approval comments"}
            },
            "required": ["announcement_id"]
        }
    ),
    CopilotActionDef(
        name="reject_notice",
        description="Reject a pending campus circular with feedback (Faculty/HoD/Admin only)",
        parameters={
            "type": "object",
            "properties": {
                "announcement_id": {"type": "integer", "description": "ID of the announcement to reject"},
                "remarks": {"type": "string", "description": "Feedback or reason for rejection"}
            },
            "required": ["announcement_id"]
        }
    ),
    CopilotActionDef(
        name="delete_notice",
        description="Permanently delete an announcement from the feed and database (Admin/Author only)",
        parameters={
            "type": "object",
            "properties": {
                "announcement_id": {"type": "integer", "description": "ID of the announcement to delete"}
            },
            "required": ["announcement_id"]
        }
    ),
    CopilotActionDef(
        name="filter_notices",
        description="Filter campus circulars by category, department, or priority in feed",
        parameters={
            "type": "object",
            "properties": {
                "category": {"type": "string", "description": "Category name (Examinations, Placements, Events, Sports, Academics, Emergency)"},
                "department": {"type": "string", "description": "Department name or code"},
                "priority": {"type": "string", "enum": ["NORMAL", "HIGH", "EMERGENCY"]}
            }
        }
    )
]


class CopilotRuntime:
    """
    EchoSphere Copilot Runtime Engine.
    Processes conversational instructions in the context of active app state
    and generates response text along with executable CopilotKit client actions.
    Supports 100% free offline deterministic execution alongside cloud LLM inference.
    """
    @classmethod
    def process_copilot_request(
        cls,
        message: str,
        app_state: Dict[str, Any],
        user_role: str = "STUDENT",
        department: str = "CSE",
        full_name: str = "Campus Member",
        history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        import re

        clean_msg = message.strip()
        lower_msg = clean_msg.lower()
        role_upper = (user_role or "STUDENT").upper()
        is_student = role_upper in ["STUDENT", "STUDENTS", "PUPIL", "USER", "GUEST"]

        # =====================================================================
        # 1. INTENT REGEX PATTERNS
        # =====================================================================
        vol_match = re.search(
            r'(?:set\s+(?:the\s+)?(?:volume\s+of\s+)?([a-zA-Z0-9\s_-]+?)\s+(?:volume\s+)?to\s+(\d{1,3})%?|set\s+volume\s+to\s+(\d{1,3})%?|volume\s+(\d{1,3})%?)',
            lower_msg
        )
        mute_match = re.search(r'mute\s+(?:the\s+)?([a-zA-Z0-9\s_-]+)', lower_msg)
        approve_match = re.search(r'\bapprove\s+(?:notice|announcement|circular)?\s*#?(\d+)\b', lower_msg)
        reject_match = re.search(r'\breject\s+(?:notice|announcement|circular)?\s*#?(\d+)\b', lower_msg)
        delete_match = re.search(r'\bdelete\s+(?:notice|announcement|circular)?\s*#?(\d+)\b', lower_msg)
        speaker_ctrl_match = re.search(r'\b(play|pause|resume|skip|advance|clear)\s+(?:the\s+)?(?:speaker|audio|announcement|queue)\b', lower_msg)

        # =====================================================================
        # 2. RBAC SECURITY GUARDRAILS (Students cannot perform admin actions)
        # =====================================================================
        is_admin_action = bool(vol_match or mute_match or approve_match or reject_match or delete_match or speaker_ctrl_match)
        if is_student and is_admin_action:
            return {
                "response": (
                    "I cannot execute administrative operations from a student account. "
                    "Speaker hardware controls, volume adjustments, and notice approval/deletion "
                    "are strictly restricted to faculty and campus administrators."
                ),
                "category_badge": "Access Restricted",
                "suggested_actions": ["Browse Active Notices", "Check Examinations", "View Placements"],
                "copilot_action": None,
                "model_used": "EchoSphere Copilot Security Engine"
            }

        # =====================================================================
        # 3. FAST DETERMINISTIC INTENT ENGINE (Zero tokens, zero rate limits)
        # =====================================================================

        # A. Speaker Volume Control (e.g. "Set Auditorium volume to 80%", "mute corridor")
        if mute_match and not is_student:
            target_node = mute_match.group(1).strip().title()
            return {
                "response": f"Muting speaker output for **{target_node}** (Volume set to 0%).",
                "category_badge": "Speaker Hardware",
                "suggested_actions": ["View Speaker Queue", "Unmute Speakers"],
                "navigation_target": "nav:hardware:speakers",
                "copilot_action": {
                    "action": "set_speaker_volume",
                    "parameters": {"node_id": target_node, "volume": 0}
                },
                "model_used": "EchoSphere Copilot Action Engine (Local)"
            }

        if vol_match and not is_student:
            vol_val = None
            target_node = "All Nodes"
            if vol_match.group(2):
                target_node = (vol_match.group(1) or "All Nodes").strip().title()
                vol_val = int(vol_match.group(2))
            elif vol_match.group(3):
                vol_val = int(vol_match.group(3))
            elif vol_match.group(4):
                vol_val = int(vol_match.group(4))

            if vol_val is not None:
                clamped_vol = max(0, min(100, vol_val))
                return {
                    "response": (
                        f"Setting speaker volume for **{target_node}** to **{clamped_vol}%**.\n\n"
                        f"- Node: {target_node}\n"
                        f"- Volume: {clamped_vol}%\n"
                        f"- Hardware command dispatched to corridor speaker nodes."
                    ),
                    "category_badge": "Speaker Hardware",
                    "suggested_actions": ["View Speaker Queue", "Test Audio Tone"],
                    "navigation_target": "nav:hardware:speakers",
                    "copilot_action": {
                        "action": "set_speaker_volume",
                        "parameters": {"node_id": target_node, "volume": clamped_vol}
                    },
                    "model_used": "EchoSphere Copilot Action Engine (Local)"
                }

        # B. Notice Approval (e.g. "Approve notice #12", "approve announcement 5")
        approve_match = re.search(r'\bapprove\s+(?:notice|announcement|circular)?\s*#?(\d+)\b', lower_msg)
        if approve_match and not is_student:
            ann_id = int(approve_match.group(1))
            remarks = "Approved via EchoSphere Copilot"
            if ":" in clean_msg:
                remarks = clean_msg.split(":", 1)[1].strip()
            return {
                "response": (
                    f"Approving campus circular **#{ann_id}** for publication and speaker queue broadcast.\n\n"
                    f"- Status: PUBLISHED\n"
                    f"- Remarks: {remarks}"
                ),
                "category_badge": "Notice Moderation",
                "suggested_actions": ["View Pending Approvals", "View Speaker Queue"],
                "navigation_target": "nav:announcements:approvals",
                "copilot_action": {
                    "action": "approve_notice",
                    "parameters": {"announcement_id": ann_id, "remarks": remarks}
                },
                "model_used": "EchoSphere Copilot Action Engine (Local)"
            }

        # C. Notice Rejection (e.g. "Reject notice #12", "reject announcement 4: duplicate")
        reject_match = re.search(r'\breject\s+(?:notice|announcement|circular)?\s*#?(\d+)\b', lower_msg)
        if reject_match and not is_student:
            ann_id = int(reject_match.group(1))
            remarks = "Does not meet publication criteria (Rejected via Copilot)"
            if ":" in clean_msg:
                remarks = clean_msg.split(":", 1)[1].strip()
            elif "reason" in lower_msg:
                parts = re.split(r'\breason\b', clean_msg, flags=re.IGNORECASE)
                if len(parts) > 1:
                    remarks = parts[1].strip(" :-\t")
            return {
                "response": (
                    f"Rejecting announcement **#{ann_id}**.\n\n"
                    f"- Status: REJECTED\n"
                    f"- Feedback: *\"{remarks}\"*\n"
                    f"The author will receive feedback to revise and resubmit."
                ),
                "category_badge": "Notice Moderation",
                "suggested_actions": ["Review Next Approval", "Open Moderation Queue"],
                "navigation_target": "nav:announcements:approvals",
                "copilot_action": {
                    "action": "reject_notice",
                    "parameters": {"announcement_id": ann_id, "remarks": remarks}
                },
                "model_used": "EchoSphere Copilot Action Engine (Local)"
            }

        # D. Notice Deletion (e.g. "Delete notice #8", "delete announcement 15")
        delete_match = re.search(r'\bdelete\s+(?:notice|announcement|circular)?\s*#?(\d+)\b', lower_msg)
        if delete_match and not is_student:
            ann_id = int(delete_match.group(1))
            return {
                "response": (
                    f"Permanently removing announcement **#{ann_id}** from campus database and active corridor displays."
                ),
                "category_badge": "Notice Management",
                "suggested_actions": ["Browse Active Notices", "Manage Announcements"],
                "navigation_target": "nav:announcements:management",
                "copilot_action": {
                    "action": "delete_notice",
                    "parameters": {"announcement_id": ann_id}
                },
                "model_used": "EchoSphere Copilot Action Engine (Local)"
            }

        # E. Notice Filter (e.g. "filter exam notices", "show placement circulars")
        filter_match = re.search(r'\b(?:filter|show|view)\s+(?:only\s+)?(exam|examination|placement|event|sports|academic|emergency)(?:s)?(?:\s+(?:notices|circulars|announcements))?\b', lower_msg)
        if filter_match:
            raw_cat = filter_match.group(1).lower()
            cat_map = {
                "exam": "Examinations",
                "examination": "Examinations",
                "placement": "Placements",
                "event": "Events",
                "sports": "Sports",
                "academic": "Academics",
                "emergency": "Emergency",
            }
            target_cat = cat_map.get(raw_cat, "All")
            return {
                "response": f"Filtering active circular feed for **{target_cat}** notices.",
                "category_badge": target_cat,
                "suggested_actions": [f"View {target_cat}", "Clear Filters", "Browse All"],
                "navigation_target": f"nav:notices:filter:{target_cat}",
                "copilot_action": {
                    "action": "filter_notices",
                    "parameters": {"category": target_cat}
                },
                "model_used": "EchoSphere Copilot Action Engine (Local)"
            }

        # =====================================================================
        # 3. LLM / MULTI-MODEL ROUTER DELEGATION
        # =====================================================================
        router = ModelRouter.get_instance()
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
            f"1. When the user requests an action, answer politely and embed the action tag at the end of your response: [[ACTION:action_name:JSON_PARAMETERS]].\n"
            f"2. Strict RBAC: Students can NEVER invoke speaker controls, adjust volume, or approve/delete notices.\n"
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
        extracted_action = result.get("copilot_action")

        # Parse any [[ACTION:name:params]] tag embedded by the model if not already extracted
        if not extracted_action:
            action_match = re.search(r'\[\[ACTION:([a-zA-Z0-9_]+):(\{[\s\S]*?\}|[a-zA-Z0-9_:]+)\]\]', response_text)
            if action_match:
                act_name = action_match.group(1)
                act_params_raw = action_match.group(2)
                try:
                    if act_params_raw.startswith("{"):
                        act_params = json.loads(act_params_raw)
                    else:
                        act_params = {"screen": act_params_raw}
                    extracted_action = {
                        "action": act_name,
                        "parameters": act_params
                    }
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
                extracted_action = {"action": "filter_notices", "parameters": {"category": category}}

        result["response"] = sanitize_ai_markdown(response_text)
        result["copilot_action"] = extracted_action
        return result

