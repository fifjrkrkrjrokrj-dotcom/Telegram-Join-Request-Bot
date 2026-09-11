from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Primary dashboard navigation keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Group / Channel", callback_data="menu:add_chat"),
        ],
        [
            InlineKeyboardButton("📂 My Chats", callback_data="menu:my_chats"),
            InlineKeyboardButton("📊 Statistics", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("❓ Help & Guide", callback_data="menu:help"),
            InlineKeyboardButton("🔄 Refresh", callback_data="menu:dashboard"),
        ]
    ])


def get_cancel_keyboard(target: str = "menu:dashboard") -> InlineKeyboardMarkup:
    """Standard cancel button returning to a specific menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Cancel", callback_data=target)]
    ])


def get_back_to_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Back button returning to main dashboard."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu:dashboard")]
    ])
