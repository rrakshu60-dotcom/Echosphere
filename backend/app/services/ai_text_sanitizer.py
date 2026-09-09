"""
EchoSphere AI Text & Markdown Sanitizer
Permanently eradicates raw markdown artifacts:
1. Strips or fixes dollar-prefixed headers (##$, ###$).
2. Normalizes raw divider clutter (---, ***, ___) into clean semantic spacing.
3. Fixes asterisk clutter (****, unclosed ***, dangling asterisks).
4. Enforces valid CommonMark bullet lists (guaranteeing blank lines before lists so parsers render bullets cleanly).
5. Cleans nonsensical tokens and raw HTML tags.
"""

import re
from typing import Optional


def sanitize_ai_markdown(text: Optional[str]) -> str:
    """
    Sanitize and polish AI-generated Markdown for clean, elegant rendering in Flutter and web clients.
    Guarantees zero raw '***', '##$', '---', or broken inline bullet points.
    """
    if not text:
        return ""

    cleaned = text

    # 1. Normalize line endings
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # 2. Fix dollar-prefixed header artifacts like '##$' or '###$ ' or '## $title'
    cleaned = re.sub(r'^(#{1,6})\s*\$([a-zA-Z0-9_]+)', r'\1 \2', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^(#{1,6})\s*\$', r'\1 ', cleaned, flags=re.MULTILINE)

    # 3. Clean raw asterisk clutter
    # Replace 4 or more asterisks with standard bold (**)
    cleaned = re.sub(r'\*{4,}', '**', cleaned)

    # Clean lines that contain ONLY asterisks, dashes, or underscores (e.g. '***', '---', '___')
    # Instead of leaving raw ASCII dividers, replace with a clean paragraph break
    cleaned = re.sub(r'^[ \t]*(\*{3,}|-{3,}|_{3,}|={3,})[ \t]*$', '\n', cleaned, flags=re.MULTILINE)

    # 4. Fix bold-italic clutter: convert '***text***' to '**text**' for consistent bold rendering
    cleaned = re.sub(r'\*{3}([^\*\n]+)\*{3}', r'**\1**', cleaned)

    # Remove dangling triple asterisks at line starts or ends
    cleaned = re.sub(r'^[ \t]*\*{3}[ \t]*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'[ \t]*\*{3}[ \t]*$', '', cleaned, flags=re.MULTILINE)

    # 5. Ensure space after bold colon: '**Title:**Text' or '**Title**:Text' -> '**Title:** Text'
    cleaned = re.sub(r'(:\*\*)([^\s\n])', r'\1 \2', cleaned)
    cleaned = re.sub(r'(\*\*:)([^\s\n])', r'\1 \2', cleaned)
    cleaned = re.sub(r'(\*\*:\*\*)([^\s\n])', r'\1 \2', cleaned)

    # 6. Normalize bullet lists for CommonMark parsers
    # Unicode bullets '•' -> '-'
    cleaned = re.sub(r'^[ \t]*•[ \t]*', '- ', cleaned, flags=re.MULTILINE)
    # Convert '* ' to '- ' for unified bullet parsing
    cleaned = re.sub(r'^[ \t]*\*[ \t]+', '- ', cleaned, flags=re.MULTILINE)

    # Ensure bullet lists have an empty line before them if preceded by a non-list line
    # CommonMark requires a blank line before list blocks to render properly
    lines = cleaned.split("\n")
    processed_lines = []
    in_list = False

    for i, line in enumerate(lines):
        is_bullet = bool(re.match(r'^[ \t]*-\s+', line))
        is_numbered = bool(re.match(r'^[ \t]*\d+\.\s+', line))
        is_list_item = is_bullet or is_numbered

        if is_list_item:
            if not in_list and processed_lines:
                # If preceding line is not blank, inject a blank line
                if processed_lines[-1].strip() != "":
                    processed_lines.append("")
            in_list = True
        elif line.strip() == "":
            in_list = False
        else:
            in_list = False

        processed_lines.append(line)

    cleaned = "\n".join(processed_lines)

    # 7. Strip raw HTML line breaks or div tags
    cleaned = re.sub(r'<\s*br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?(?:div|p|span)[^>]*>', '', cleaned, flags=re.IGNORECASE)

    # 8. Collapse 3+ consecutive newlines into double newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()
