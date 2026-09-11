import re
import html
from typing import Optional, Dict, Any

def format_card(title: str, content: str = "") -> str:
    """Format text inside a sleek premium Unicode card."""
    lines = [
        "╭━━━━━━━━━━━━━━━━━━━━╮",
        f"       {title}",
        "╰━━━━━━━━━━━━━━━━━━━━╯"
    ]
    if content:
        lines.append("")
        lines.append(content.strip())
    return "\n".join(lines)


def interpolate_template(
    template: str,
    first_name: str = "",
    last_name: Optional[str] = None,
    username: Optional[str] = None,
    user_id: int = 0,
    chat_title: str = "",
    chat_username: Optional[str] = None
) -> str:
    """Safely interpolate placeholder variables in custom welcome messages."""
    replacements: Dict[str, str] = {
        "{first_name}": first_name or "there",
        "{last_name}": last_name or "",
        "{username}": f"@{username}" if username else (first_name or "user"),
        "{user_id}": str(user_id) if user_id else "",
        "{chat_title}": chat_title or "this community",
        "{chat_username}": f"@{chat_username}" if chat_username else (chat_title or "chat"),
    }
    
    result = template
    for key, val in replacements.items():
        result = result.replace(key, val)
    return result


def extract_chat_identifier(text: str) -> Optional[str]:
    """
    Extract a username, invite link, or numeric ID from user input.
    Examples:
    - https://t.me/example -> 'example'
    - @example -> 'example'
    - -100123456789 -> '-100123456789'
    - https://t.me/+joinhash -> 'https://t.me/+joinhash'
    """
    if not text:
        return None
        
    text = text.strip()
    
    # Check numeric ID
    if text.lstrip("-").isdigit():
        return text

    # Check joinchat / invite hash link
    if "t.me/+" in text or "t.me/joinchat/" in text:
        return text

    # Extract username from t.me URL
    url_match = re.search(r"(?:https?://)?(?:www\.)?t\.me/([a-zA-Z0-9_]{4,})", text)
    if url_match:
        return url_match.group(1)

    # Extract @username
    if text.startswith("@"):
        return text[1:]

    # Direct username string without @
    if re.match(r"^[a-zA-Z0-9_]{4,32}$", text):
        return text

    return text


def format_duration(seconds: float) -> str:
    """Format seconds into human-readable duration."""
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    remaining_secs = seconds % 60
    if minutes < 60:
        if remaining_secs > 0:
            return f"{minutes}m {remaining_secs}s"
        return f"{minutes}m"
    hours = minutes // 60
    remaining_mins = minutes % 60
    return f"{hours}h {remaining_mins}m"


def escape_html(text: str) -> str:
    """Escape text for safe HTML rendering in Telegram messages."""
    return html.escape(str(text)) if text else ""


def extract_chat_from_message(message: Any) -> Dict[str, Any]:
    """
    Safely extract chat info from a Telegram message (native shared chat, forward, or text).
    """
    res = {
        "id": None,
        "title": None,
        "username": None,
        "type": None,
        "is_forward": False
    }

    # 1. Native Telegram Chat Shared event (KeyboardButtonRequestChat)
    chat_shared = getattr(message, "chat_shared", None)
    if chat_shared:
        shared_chat = getattr(chat_shared, "chat", None)
        chat_id = shared_chat.id if shared_chat else getattr(chat_shared, "chat_id", getattr(chat_shared, "id", None))
        chat_title = (getattr(shared_chat, "title", None) or getattr(shared_chat, "first_name", None)) if shared_chat else f"Chat {chat_id}"
        chat_username = getattr(shared_chat, "username", None) if shared_chat else None
        chat_type = getattr(shared_chat, "type", "channel") if shared_chat else "channel"
        if hasattr(chat_type, "value"):
            chat_type = chat_type.value
        res.update({
            "id": chat_id,
            "title": chat_title or f"Chat {chat_id}",
            "username": chat_username,
            "type": str(chat_type),
            "is_forward": False
        })
        return res

    # 2. Modern Telegram Forward Origin (Pyrogram 2.0+ / Pyrofork)
    origin = getattr(message, "forward_origin", None)
    if origin:
        chat = getattr(origin, "chat", None) or getattr(origin, "sender_chat", None)
        if chat:
            chat_type = chat.type.value if hasattr(chat.type, "value") else str(chat.type)
            res.update({
                "id": chat.id,
                "title": getattr(chat, "title", None) or getattr(chat, "first_name", None) or f"Chat {chat.id}",
                "username": getattr(chat, "username", None),
                "type": chat_type,
                "is_forward": True
            })
            return res

    # 3. Legacy forward_from_chat
    try:
        f_chat = getattr(message, "forward_from_chat", None)
        if f_chat:
            chat_type = f_chat.type.value if hasattr(f_chat.type, "value") else str(f_chat.type)
            res.update({
                "id": f_chat.id,
                "title": getattr(f_chat, "title", None) or getattr(f_chat, "first_name", None) or f"Chat {f_chat.id}",
                "username": getattr(f_chat, "username", None),
                "type": chat_type,
                "is_forward": True
            })
            return res
    except Exception:
        pass

    # 4. Direct text or caption parsing
    text = (getattr(message, "text", "") or getattr(message, "caption", "") or "").strip()
    if text:
        ident = extract_chat_identifier(text)
        res["id"] = ident
        return res

    return res
