from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from database.chats import chat_repo
from services.telegram import telegram_service
from utils.helpers import format_card, extract_chat_identifier, extract_chat_from_message, escape_html
from utils.states import state_manager, States
from keyboards.main import get_cancel_keyboard
from keyboards.chats import get_select_chat_reply_keyboard
from utils.logger import logger

@Client.on_callback_query(filters.regex(r"^menu:add_chat$"))
async def cb_add_chat_prompt(client: Client, callback_query: CallbackQuery):
    """Prompt user to provide chat username, link, or tap the 1-tap selector."""
    user = callback_query.from_user
    state_manager.set_state(user.id, States.WAITING_FOR_CHAT_LINK)

    content = (
        "<b>Choose how to connect your Group or Channel:</b>\n\n"
        "⚡ <b>Option 1 (1-Tap Select):</b> Tap the button below on your keyboard to pick your channel/group!\n\n"
        "👉 <b>Option 2:</b> <b>FORWARD ANY POST/MESSAGE</b> from your channel or group here!\n\n"
        "👉 <b>Option 3:</b> Send the public <b>@username</b> or numeric <b>Chat ID</b> (e.g. <code>-1001234567890</code>)\n\n"
        "⚠️ <i>Important: Ensure you have already added this bot as an <b>Administrator</b> with 'Invite Users via Link' permission!</i>"
    )

    text = format_card("➕ ADD GROUP / CHANNEL", content)
    await callback_query.message.reply_text(
        text="👇 <i>Select a channel or forward a message:</i>",
        reply_markup=get_select_chat_reply_keyboard()
    )
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_cancel_keyboard("menu:dashboard")
    )
    await callback_query.answer()


@Client.on_message(filters.private & ~filters.command(["start", "help", "cancel"]))
async def handle_chat_link_input(client: Client, message: Message):
    """Process incoming chat link input or forwarded message when user is in WAITING_FOR_CHAT_LINK state."""
    user = message.from_user
    if not user:
        return

    # Handle cancel button from reply keyboard
    if message.text == "❌ Cancel":
        state_manager.clear_state(user.id)
        await message.reply_text(
            "Action cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return

    current_state = state_manager.get_state(user.id)
    if current_state != States.WAITING_FOR_CHAT_LINK:
        message.continue_propagation()
        return

    # Check for private links first
    raw_text = (message.text or message.caption or "").strip()
    if "t.me/+" in raw_text or "t.me/joinchat/" in raw_text:
        content = (
            "⚠️ <b>Private invite links (t.me/+) cannot be resolved directly by Telegram bots.</b>\n\n"
            "👉 <b>Easy Solution:</b> Simply <b>FORWARD ANY POST/MESSAGE</b> from your channel or group here!\n\n"
            "Or send its numeric Chat ID (e.g. <code>-100123456789</code>)."
        )
        await message.reply_text(
            format_card("⚠️ FORWARD A POST", content),
            reply_markup=get_cancel_keyboard("menu:dashboard")
        )
        return

    extracted = extract_chat_from_message(message)
    identifier = extracted.get("id")

    if not identifier:
        await message.reply_text(
            "❌ Could not determine the chat. Please <b>forward a post from the channel</b> or send its <b>@username</b>."
        )
        return

    status_msg = await message.reply_text("🔍 Resolving chat and verifying administrator permissions...")

    # 1. Resolve chat
    chat, err = await telegram_service.resolve_chat(client, identifier)
    if not chat:
        state_manager.clear_state(user.id)
        content = (
            f"❌ <b>Could not connect chat</b>\n\n"
            f"Reason: {err or 'Unknown error'}\n\n"
            "Please ensure that:\n"
            "1. The link or username is typed correctly.\n"
            "2. The bot is added to the channel or group as an admin."
        )
        await status_msg.edit_text(
            format_card("❌ CONNECTION FAILED", content),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="menu:add_chat")],
                [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu:dashboard")]
            ])
        )
        return

    # 2. Check bot admin permissions
    perm_check = await telegram_service.verify_bot_permissions(client, chat.id)
    
    if not perm_check["is_admin"]:
        state_manager.clear_state(user.id)
        content = (
            f"❌ <b>Bot is not an administrator in {escape_html(chat.title)}</b>\n\n"
            "Please promote this bot to <b>Administrator</b> in your chat settings and try again."
        )
        await status_msg.edit_text(
            format_card("❌ PERMISSION ERROR", content),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Try Again", callback_data="menu:add_chat")],
                [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu:dashboard")]
            ])
        )
        return

    if perm_check["missing_permissions"]:
        state_manager.clear_state(user.id)
        missing_list = "\n".join([f"• {p}" for p in perm_check["missing_permissions"]])
        content = (
            f"⚠️ <b>Missing Required Permissions in {escape_html(chat.title)}</b>\n\n"
            f"The bot is an admin, but is missing required permissions:\n"
            f"<b>{missing_list}</b>\n\n"
            "Please grant these permissions in your chat admin privileges and try again."
        )
        await status_msg.edit_text(
            format_card("⚠️ PERMISSION REQUIRED", content),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Verify Again", callback_data="menu:add_chat")],
                [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="menu:dashboard")]
            ])
        )
        return

    # 3. Chat is fully verified - Persist to database
    chat_type = chat.type.value if hasattr(chat.type, "value") else str(chat.type)
    await chat_repo.add_chat(
        chat_id=chat.id,
        owner_id=user.id,
        title=chat.title,
        chat_type=chat_type,
        username=chat.username
    )

    state_manager.clear_state(user.id)

    content = (
        f"💬 <b>Chat:</b> {escape_html(chat.title)}\n"
        f"🏷 <b>Type:</b> <code>{chat_type.capitalize()}</code>\n"
        f"🆔 <b>ID:</b> <code>{chat.id}</code>\n\n"
        f"<b>Permission Checklist:</b>\n"
        f"✅ Bot is admin\n"
        f"✅ Can receive join requests\n"
        f"✅ Can approve join requests\n"
        f"✅ Can check member status\n\n"
        f"🎉 <i>Target chat is connected and active! You can now configure required verification chats.</i>"
    )

    text = format_card("✅ CHAT CONNECTED", content)
    await status_msg.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ Configure Chat", callback_data=f"chat:manage:{chat.id}")],
            [InlineKeyboardButton("📂 My Chats", callback_data="menu:my_chats")]
        ])
    )
