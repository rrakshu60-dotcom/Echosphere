"""
EchoSphere AI Text & Markdown Sanitizer
Permanently eradicates raw markdown artifacts:
1. Strips or fixes dollar-prefixed headers (##$, ###$).
2. Normalizes raw divider clutter (---, ----, ***, ___, ///) into clean semantic spacing.
3. Fixes asterisk clutter (****, unclosed ***, dangling asterisks).
4. De-synthesizes bolding on names in conversational greetings (e.g. "**EchoSphere Campus AI Assistant**" -> "EchoSphere Campus AI Assistant").
5. Enforces valid CommonMark bullet lists (guaranteeing blank lines before lists so parsers render bullets cleanly).
6. Cleans nonsensical tokens, raw slashes, and raw HTML tags.
"""

import re
from typing import Optional


def sanitize_ai_markdown(text: Optional[str]) -> str:
    """
    Sanitize and polish AI-generated Markdown for clean, elegant rendering in Flutter and web clients.
    Guarantees zero raw '***', '##$', '---', '----', '///', or broken inline bullet points.
    """
    if not text:
        return ""

    cleaned = text

    # 1. Normalize line endings
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")

    # 1.1 Strip embedded [[ACTION:...]] tags from conversational text
    cleaned = re.sub(r'\[\[ACTION:[\s\S]*?\]\]', '', cleaned)

    # 1.2 Strip patronizing "Feel free to ask about..." boilerplate
    cleaned = re.sub(r'\s*Feel free to ask about[^\.\n]*\.?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*Ask me about recent circulars[^\.\n]*\.?', '', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s*Ask me about[^\.\n]*\.?', '', cleaned, flags=re.IGNORECASE)

    # 2. Strip stray slash clutter (e.g. '///', '////') often used by LLMs as dividers or delimiters
    cleaned = re.sub(r'^[ \t]*///+[ \t]*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'///+', '', cleaned)

    # 3. Fix dollar-prefixed header artifacts like '##$' or '###$ ' or '## $title'
    cleaned = re.sub(r'^(#{1,6})\s*\$([a-zA-Z0-9_]+)', r'\1 \2', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^(#{1,6})\s*\$', r'\1 ', cleaned, flags=re.MULTILINE)

    # 4. Clean raw horizontal dividers (e.g. '---', '----', '***', '____', '===')
    # Replace standalone divider lines with a clean single paragraph break
    cleaned = re.sub(r'^[ \t]*(-{3,}|\*{3,}|_{3,}|={3,})[ \t]*$', '\n', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'\n[ \t]*-{3,}[ \t]*\n', '\n\n', cleaned)

    # 5. Clean raw asterisk clutter
    # Replace 4 or more asterisks with standard bold (**)
    cleaned = re.sub(r'\*{4,}', '**', cleaned)

    # Convert '***text***' to '**text**' for consistent bold rendering
    cleaned = re.sub(r'\*{3}([^\*\n]+)\*{3}', r'**\1**', cleaned)

    # Remove dangling triple asterisks at line starts or ends
    cleaned = re.sub(r'^[ \t]*\*{3}[ \t]*', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'[ \t]*\*{3}[ \t]*$', '', cleaned, flags=re.MULTILINE)

    # 6. De-synthesize excessive bolding in conversational greetings:
    cleaned = re.sub(r'I am (?:the )?\*\*([^\*]+)\*\*', r'I am \1', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'Hello,?\s*\*\*([^\*]+)\*\*', r'Hello \1', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'as \*\*([^\*]+)\*\*', r'as \1', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\*\*(EchoSphere Campus AI Assistant|EchoSphere AI|EchoSphere|Dev Admin|College Admin|Principal|Teacher|Student|HoD)\*\*', r'\1', cleaned, flags=re.IGNORECASE)

    # 7. Ensure space after bold colon: '**Title:**Text' or '**Title**:Text' -> '**Title:** Text'
    cleaned = re.sub(r'(:\*\*)([^\s\n])', r'\1 \2', cleaned)
    cleaned = re.sub(r'(\*\*:)([^\s\n])', r'\1 \2', cleaned)
    cleaned = re.sub(r'(\*\*:\*\*)([^\s\n])', r'\1 \2', cleaned)

    # 8. Normalize bullet lists for CommonMark parsers
    # Unicode bullets '•' -> '-'
    cleaned = re.sub(r'^[ \t]*•[ \t]*', '- ', cleaned, flags=re.MULTILINE)
    # Convert '* ' to '- ' for unified bullet parsing
    cleaned = re.sub(r'^[ \t]*\*[ \t]+', '- ', cleaned, flags=re.MULTILINE)

    # Ensure bullet lists have an empty line before them if preceded by a non-list line
    lines = cleaned.split("\n")
    processed_lines = []
    in_list = False

    for line in lines:
        is_bullet = bool(re.match(r'^[ \t]*-\s+', line))
        is_numbered = bool(re.match(r'^[ \t]*\d+\.\s+', line))
        is_list_item = is_bullet or is_numbered

        if is_list_item:
            if not in_list and processed_lines:
                if processed_lines[-1].strip() != "":
                    processed_lines.append("")
            in_list = True
        elif line.strip() == "":
            in_list = False
        else:
            in_list = False

        processed_lines.append(line)

    cleaned = "\n".join(processed_lines)

    # 9. Strip raw HTML line breaks or div tags
    cleaned = re.sub(r'<\s*br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'</?(?:div|p|span)[^>]*>', '', cleaned, flags=re.IGNORECASE)

    # 10. Collapse 3+ consecutive newlines into double newlines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

    return cleaned.strip()
