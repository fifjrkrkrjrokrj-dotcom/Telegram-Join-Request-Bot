from typing import List, Dict, Any, Optional
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)

try:
    from pyrogram.types import KeyboardButtonRequestChat
except ImportError:
    try:
        from pyrogram.types import KeyboardButtonRequestPeer as KeyboardButtonRequestChat
    except ImportError:
        KeyboardButtonRequestChat = None

def get_select_chat_reply_keyboard() -> Optional[ReplyKeyboardMarkup]:
    """Native Telegram reply keyboard for 1-tap channel or group selection."""
    if not KeyboardButtonRequestChat:
        return None
    try:
        return ReplyKeyboardMarkup(
            [
                [
                    KeyboardButton(
                        "📢 1-Tap Select Channel",
                        request_chat=KeyboardButtonRequestChat(
                            button_id=1,
                            chat_is_channel=True,
                            bot_is_member=True
                        )
                    ),
                    KeyboardButton(
                        "👥 1-Tap Select Group",
                        request_chat=KeyboardButtonRequestChat(
                            button_id=2,
                            chat_is_channel=False,
                            bot_is_member=True
                        )
                    )
                ],
                [KeyboardButton("❌ Cancel")]
            ],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    except Exception:
        return None

def get_chats_list_keyboard(chats: List[Dict[str, Any]], page: int = 1, per_page: int = 5) -> InlineKeyboardMarkup:
    """List connected chats with pagination."""
    keyboard: List[List[InlineKeyboardButton]] = []
    
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    current_chats = chats[start_idx:end_idx]

    for chat in current_chats:
        chat_id = chat["chat_id"]
        status_icon = "🟢" if chat.get("enabled", True) else "🔴"
        title = chat.get("title", "Unnamed Chat")
        keyboard.append([
            InlineKeyboardButton(f"{status_icon} {title}", callback_data=f"chat:manage:{chat_id}")
        ])

    # Pagination controls
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"menu:my_chats:{page - 1}"))
    if end_idx < len(chats):
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"menu:my_chats:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("➕ Add New Chat", callback_data="menu:add_chat")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu:dashboard")])
    return InlineKeyboardMarkup(keyboard)


def get_chat_dashboard_keyboard(chat: Dict[str, Any], req_count: int = 0) -> InlineKeyboardMarkup:
    """Main management dashboard for a specific connected chat."""
    chat_id = chat["chat_id"]
    is_active = chat.get("enabled", True)
    auto_approve = chat.get("auto_approve", True)
    admin_notif = chat.get("admin_notifications", True)

    status_btn_text = "🟢 Status: ACTIVE" if is_active else "🔴 Status: PAUSED"
    auto_btn_text = "🟢 Auto Approve: ON" if auto_approve else "🔴 Auto Approve: OFF"
    notif_btn_text = "🔔 Notifications: ON" if admin_notif else "🔕 Notifications: OFF"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(status_btn_text, callback_data=f"chat:toggle_status:{chat_id}"),
            InlineKeyboardButton(auto_btn_text, callback_data=f"chat:toggle_auto:{chat_id}"),
        ],
        [
            InlineKeyboardButton(f"🔗 Required Chats ({req_count})", callback_data=f"chat:req_chats:{chat_id}"),
            InlineKeyboardButton("⚙️ Settings", callback_data=f"chat:settings:{chat_id}"),
        ],
        [
            InlineKeyboardButton("📝 Welcome Message", callback_data=f"chat:welcome_msg:{chat_id}"),
            InlineKeyboardButton("🖼 Welcome Photo", callback_data=f"chat:welcome_photo:{chat_id}"),
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data=f"chat:stats:{chat_id}"),
            InlineKeyboardButton(notif_btn_text, callback_data=f"chat:toggle_notif:{chat_id}"),
        ],
        [
            InlineKeyboardButton("🗑 Remove Chat", callback_data=f"chat:confirm_remove:{chat_id}"),
        ],
        [
            InlineKeyboardButton("🔙 Back to My Chats", callback_data="menu:my_chats"),
        ]
    ])


def get_chat_settings_keyboard(chat: Dict[str, Any]) -> InlineKeyboardMarkup:
    """Detailed settings menu for a target chat."""
    chat_id = chat["chat_id"]
    auto_approve = chat.get("auto_approve", True)
    admin_notif = chat.get("admin_notifications", True)
    timeout = chat.get("verification_timeout", 30)

    auto_text = "🟢 Auto Approve: ON" if auto_approve else "🔴 Auto Approve: OFF"
    notif_text = "🔔 Notifications: ON" if admin_notif else "🔕 Notifications: OFF"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(auto_text, callback_data=f"chat:toggle_auto:{chat_id}")],
        [InlineKeyboardButton(notif_text, callback_data=f"chat:toggle_notif:{chat_id}")],
        [InlineKeyboardButton(f"⏱ Timeout: {timeout} min", callback_data=f"chat:set_timeout:{chat_id}")],
        [InlineKeyboardButton("🔙 Back to Chat Dashboard", callback_data=f"chat:manage:{chat_id}")]
    ])


def get_required_chats_menu_keyboard(chat_id: int, required_chats: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Menu listing all configured required verification chats."""
    keyboard: List[List[InlineKeyboardButton]] = []

    for idx, req in enumerate(required_chats, start=1):
        req_id = str(req["_id"])
        prefix = "📢" if req.get("type") == "channel" else "👥"
        title = req.get("title", "Chat")
        keyboard.append([
            InlineKeyboardButton(f"{idx}. {prefix} {title}", callback_data=f"chat:req_view:{chat_id}:{req_id}")
        ])

    keyboard.append([InlineKeyboardButton("➕ Add Required Chat", callback_data=f"chat:req_add:{chat_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Chat Dashboard", callback_data=f"chat:manage:{chat_id}")])
    return InlineKeyboardMarkup(keyboard)


def get_single_required_chat_keyboard(chat_id: int, req_id: str, is_first: bool = False, is_last: bool = False) -> InlineKeyboardMarkup:
    """Actions on an individual required chat item."""
    reorder_row = []
    if not is_first:
        reorder_row.append(InlineKeyboardButton("⬆️ Move Up", callback_data=f"chat:req_move:{chat_id}:{req_id}:up"))
    if not is_last:
        reorder_row.append(InlineKeyboardButton("⬇️ Move Down", callback_data=f"chat:req_move:{chat_id}:{req_id}:down"))

    keyboard = []
    if reorder_row:
        keyboard.append(reorder_row)

    keyboard.append([
        InlineKeyboardButton("✏️ Edit Button Text", callback_data=f"chat:req_edit_text:{chat_id}:{req_id}"),
        InlineKeyboardButton("🔗 Edit Invite Link", callback_data=f"chat:req_edit_link:{chat_id}:{req_id}"),
    ])
    keyboard.append([InlineKeyboardButton("🗑 Remove Requirement", callback_data=f"chat:req_delete:{chat_id}:{req_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Requirements", callback_data=f"chat:req_chats:{chat_id}")])
    return InlineKeyboardMarkup(keyboard)


def get_confirm_remove_chat_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Confirmation prompt before deleting target chat."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ YES, REMOVE CHAT", callback_data=f"chat:do_remove:{chat_id}"),
            InlineKeyboardButton("❌ CANCEL", callback_data=f"chat:manage:{chat_id}"),
        ]
    ])
