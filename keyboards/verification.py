from typing import List, Dict, Any
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_verification_dm_keyboard(session_id: str, required_chats: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Build the initial verification keyboard with mandatory join buttons and verify action."""
    keyboard: List[List[InlineKeyboardButton]] = []

    for req in required_chats:
        btn_text = req.get("button_text") or f"📢 Join {req.get('title', 'Chat')}"
        invite_link = req.get("invite_link") or (f"https://t.me/{req['username']}" if req.get("username") else None)
        
        if invite_link:
            keyboard.append([InlineKeyboardButton(btn_text, url=invite_link)])

    # Action button
    keyboard.append([
        InlineKeyboardButton("✅ VERIFY", callback_data=f"verify:{session_id}")
    ])
    return InlineKeyboardMarkup(keyboard)


def get_missing_verification_keyboard(session_id: str, missing_chats: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Build the retry keyboard showing only remaining channels/groups."""
    keyboard: List[List[InlineKeyboardButton]] = []

    for missing in missing_chats:
        btn_text = missing.get("button_text") or f"📢 Join {missing.get('title', 'Chat')}"
        invite_link = missing.get("invite_link")

        if invite_link:
            keyboard.append([InlineKeyboardButton(f"👉 {btn_text}", url=invite_link)])

    # Retry action button
    keyboard.append([
        InlineKeyboardButton("🔄 VERIFY AGAIN", callback_data=f"verify:{session_id}")
    ])
    return InlineKeyboardMarkup(keyboard)
