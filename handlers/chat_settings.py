from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.chats import chat_repo
from database.required_chats import required_chat_repo
from services.statistics import statistics_service
from keyboards.chats import (
    get_chat_dashboard_keyboard,
    get_chat_settings_keyboard,
    get_confirm_remove_chat_keyboard,
)
from utils.helpers import format_card, escape_html
from utils.states import state_manager, States
from utils.logger import logger

@Client.on_callback_query(filters.regex(r"^chat:manage:(-?\d+)$"))
async def cb_manage_chat(client: Client, callback_query: CallbackQuery):
    """Render management dashboard for a specific connected chat."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))
    state_manager.clear_state(user.id)

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found or unauthorized.", show_alert=True)
        return

    required_chats = await required_chat_repo.get_required_chats(chat_id)
    req_count = len(required_chats)

    status_str = "🟢 Active" if chat.get("enabled", True) else "🔴 Paused"
    auto_str = "🟢 ON (Instant)" if chat.get("auto_approve", True) else "🔴 OFF (Manual)"
    notif_str = "🔔 Enabled" if chat.get("admin_notifications", True) else "🔕 Disabled"
    timeout_str = f"{chat.get('verification_timeout', 30)} minutes"
    has_photo = "🖼 Custom Photo Set" if chat.get("welcome_photo") else "None (Text Only)"

    content = (
        f"💬 <b>Chat Title:</b> {escape_html(chat.get('title', ''))}\n"
        f"🆔 <b>Chat ID:</b> <code>{chat_id}</code>\n"
        f"🏷 <b>Type:</b> <code>{chat.get('type', 'group').capitalize()}</code>\n\n"
        f"⚙️ <b>CONFIGURED SETTINGS:</b>\n"
        f"• Status: <b>{status_str}</b>\n"
        f"• Auto-Approve: <b>{auto_str}</b>\n"
        f"• Verification Timeout: <b>{timeout_str}</b>\n"
        f"• Admin Alerts: <b>{notif_str}</b>\n"
        f"• Welcome Banner: <b>{has_photo}</b>\n"
        f"• Required Chats: <b>{req_count} configured</b>"
    )

    text = format_card(chat.get("title", "CHAT DASHBOARD")[:24].upper(), content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_chat_dashboard_keyboard(chat, req_count)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:toggle_status:(-?\d+)$"))
async def cb_toggle_chat_status(client: Client, callback_query: CallbackQuery):
    """Toggle target chat active/paused state."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    new_status = await chat_repo.toggle_enabled(chat_id, user.id)
    if new_status is None:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    msg = "🟢 Chat verification resumed!" if new_status else "🔴 Chat verification paused."
    await callback_query.answer(msg)
    
    # Refresh view
    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    required_chats = await required_chat_repo.get_required_chats(chat_id)
    await callback_query.message.edit_reply_markup(
        reply_markup=get_chat_dashboard_keyboard(chat, len(required_chats))
    )


@Client.on_callback_query(filters.regex(r"^chat:toggle_auto:(-?\d+)$"))
async def cb_toggle_auto_approve(client: Client, callback_query: CallbackQuery):
    """Toggle auto-approval setting for target chat."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    new_val = await chat_repo.toggle_auto_approve(chat_id, user.id)
    if new_val is None:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    msg = "🟢 Auto-Approve enabled!" if new_val else "🔴 Auto-Approve disabled."
    await callback_query.answer(msg)

    # Refresh view
    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    required_chats = await required_chat_repo.get_required_chats(chat_id)
    await callback_query.message.edit_reply_markup(
        reply_markup=get_chat_dashboard_keyboard(chat, len(required_chats))
    )


@Client.on_callback_query(filters.regex(r"^chat:toggle_notif:(-?\d+)$"))
async def cb_toggle_notifications(client: Client, callback_query: CallbackQuery):
    """Toggle admin notifications for target chat."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    new_val = await chat_repo.toggle_admin_notifications(chat_id, user.id)
    if new_val is None:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    msg = "🔔 Notifications enabled!" if new_val else "🔕 Notifications muted."
    await callback_query.answer(msg)

    # Refresh view
    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    required_chats = await required_chat_repo.get_required_chats(chat_id)
    await callback_query.message.edit_reply_markup(
        reply_markup=get_chat_dashboard_keyboard(chat, len(required_chats))
    )


@Client.on_callback_query(filters.regex(r"^chat:settings:(-?\d+)$"))
async def cb_chat_settings_menu(client: Client, callback_query: CallbackQuery):
    """Render chat settings submenu."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Unauthorized.", show_alert=True)
        return

    content = (
        f"⚙️ <b>Settings for {escape_html(chat.get('title', 'Chat'))}</b>\n\n"
        "• <b>Auto Approve:</b> Automatically approve requests upon verification.\n"
        "• <b>Notifications:</b> Receive alert when new users verify.\n"
        "• <b>Timeout:</b> Duration in minutes before verification session expires."
    )
    text = format_card("⚙️ CHAT SETTINGS", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_chat_settings_keyboard(chat)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:set_timeout:(-?\d+)$"))
async def cb_cycle_timeout(client: Client, callback_query: CallbackQuery):
    """Cycle timeout between presets (5m, 15m, 30m, 60m, 120m, 1440m)."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    presets = [5, 15, 30, 60, 120, 1440]
    current = chat.get("verification_timeout", 30)
    try:
        next_idx = (presets.index(current) + 1) % len(presets)
        new_timeout = presets[next_idx]
    except ValueError:
        new_timeout = 30

    await chat_repo.update_settings(chat_id, user.id, {"verification_timeout": new_timeout})
    await callback_query.answer(f"⏱ Timeout updated to {new_timeout} minutes.")

    # Refresh settings view
    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    await callback_query.message.edit_reply_markup(reply_markup=get_chat_settings_keyboard(chat))


@Client.on_callback_query(filters.regex(r"^chat:stats:(-?\d+)$"))
async def cb_chat_statistics(client: Client, callback_query: CallbackQuery):
    """Show detailed statistics for target chat."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    text = await statistics_service.get_formatted_chat_stats(chat)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back to Chat", callback_data=f"chat:manage:{chat_id}")]
        ])
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:welcome_msg:(-?\d+)$"))
async def cb_welcome_message_view(client: Client, callback_query: CallbackQuery):
    """View and customize welcome message."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    custom_text = chat.get("welcome_text")
    display_msg = custom_text or (
        "Welcome, {first_name}! 👋\n\n"
        "Your request to join <b>{chat_title}</b> has been received.\n\n"
        "Before your request can be approved, please join all required channels below and press <b>VERIFY</b>."
    )

    content = (
        "📝 <b>CURRENT VERIFICATION MESSAGE:</b>\n\n"
        f"{display_msg}\n\n"
        "<b>Available Dynamic Variables:</b>\n"
        "• <code>{first_name}</code> - User's first name\n"
        "• <code>{last_name}</code> - User's last name\n"
        "• <code>{username}</code> - @username\n"
        "• <code>{user_id}</code> - User numeric ID\n"
        "• <code>{chat_title}</code> - Target chat name\n"
        "• <code>{chat_username}</code> - Target chat @username"
    )

    text = format_card("📝 WELCOME MESSAGE", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✏️ Set Custom Message", callback_data=f"chat:edit_welcome:{chat_id}")],
            [InlineKeyboardButton("🔄 Reset to Default", callback_data=f"chat:reset_welcome:{chat_id}")],
            [InlineKeyboardButton("🔙 Back to Chat", callback_data=f"chat:manage:{chat_id}")],
        ])
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:edit_welcome:(-?\d+)$"))
async def cb_edit_welcome_prompt(client: Client, callback_query: CallbackQuery):
    """Prompt user to send custom welcome text."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    state_manager.set_state(user.id, States.WAITING_FOR_WELCOME_MSG, {"target_chat_id": chat_id})
    content = (
        "Please send your new <b>custom welcome message</b> in the next message.\n\n"
        "You may use Markdown/HTML formatting and dynamic variables like <code>{first_name}</code> and <code>{chat_title}</code>."
    )
    text = format_card("✏️ EDIT WELCOME MESSAGE", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data=f"chat:welcome_msg:{chat_id}")]
        ])
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:reset_welcome:(-?\d+)$"))
async def cb_reset_welcome(client: Client, callback_query: CallbackQuery):
    """Reset welcome message to default template."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    await chat_repo.update_settings(chat_id, user.id, {"welcome_text": None})
    await callback_query.answer("🔄 Reset welcome message to default.")
    # Trigger view reload
    await cb_welcome_message_view(client, callback_query)


@Client.on_callback_query(filters.regex(r"^chat:welcome_photo:(-?\d+)$"))
async def cb_welcome_photo_view(client: Client, callback_query: CallbackQuery):
    """Manage welcome banner photo."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    has_photo = bool(chat.get("welcome_photo"))
    status = "✅ Custom photo is currently set." if has_photo else "❌ No photo set (text only)."

    content = (
        f"🖼 <b>Welcome Banner Photo:</b>\n{status}\n\n"
        "You can attach a promotional banner image that will be sent alongside the verification message in private DM."
    )
    text = format_card("🖼 WELCOME BANNER", content)
    buttons = [
        [InlineKeyboardButton("📤 Upload / Change Photo", callback_data=f"chat:upload_photo:{chat_id}")],
    ]
    if has_photo:
        buttons.append([InlineKeyboardButton("🗑 Remove Photo", callback_data=f"chat:delete_photo:{chat_id}")])
    buttons.append([InlineKeyboardButton("🔙 Back to Chat", callback_data=f"chat:manage:{chat_id}")])

    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:upload_photo:(-?\d+)$"))
async def cb_upload_photo_prompt(client: Client, callback_query: CallbackQuery):
    """Prompt user to send a photo."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    state_manager.set_state(user.id, States.WAITING_FOR_WELCOME_PHOTO, {"target_chat_id": chat_id})
    content = "Please send the <b>photo</b> you would like to use as the welcome banner."
    text = format_card("📤 UPLOAD BANNER", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data=f"chat:welcome_photo:{chat_id}")]
        ])
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:delete_photo:(-?\d+)$"))
async def cb_delete_photo(client: Client, callback_query: CallbackQuery):
    """Remove welcome banner photo."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    await chat_repo.update_settings(chat_id, user.id, {"welcome_photo": None})
    await callback_query.answer("🗑 Welcome photo removed.")
    await cb_welcome_photo_view(client, callback_query)


@Client.on_callback_query(filters.regex(r"^chat:confirm_remove:(-?\d+)$"))
async def cb_confirm_remove_chat(client: Client, callback_query: CallbackQuery):
    """Ask for confirmation before deleting chat."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    content = (
        f"⚠️ <b>ARE YOU SURE YOU WANT TO REMOVE:</b>\n\n"
        f"🔥 <b>{escape_html(chat.get('title', 'Chat'))}</b>\n"
        f"🆔 <code>{chat_id}</code>\n\n"
        "This will disable join request verification and remove all configured required channel rules for this chat."
    )
    text = format_card("⚠️ REMOVE CHAT?", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_confirm_remove_chat_keyboard(chat_id)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:do_remove:(-?\d+)$"))
async def cb_do_remove_chat(client: Client, callback_query: CallbackQuery):
    """Execute target chat removal."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    # Delete chat and its requirement rules
    deleted = await chat_repo.delete_chat(chat_id, user.id)
    if deleted:
        await required_chat_repo.delete_all_for_target_chat(chat_id, user.id)
        await callback_query.answer("🗑 Chat successfully removed.", show_alert=True)
    else:
        await callback_query.answer("❌ Could not remove chat.", show_alert=True)

    # Redirect to My Chats
    chats = await chat_repo.get_owner_chats(user.id)
    content = "📂 <b>Your Connected Chats:</b>"
    text = format_card("📂 MY CHATS", content)
    from keyboards.chats import get_chats_list_keyboard
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_chats_list_keyboard(chats, page=1)
    )


# Message handlers for interactive state inputs (Welcome Text & Photo)
@Client.on_message(filters.private & ~filters.command(["start", "help", "cancel"]))
async def handle_settings_interactive_inputs(client: Client, message: Message):
    """Handle incoming text or photo inputs for settings."""
    user = message.from_user
    if not user:
        return

    # Handle cancel
    if message.text == "❌ Cancel":
        state_manager.clear_state(user.id)
        from pyrogram.types import ReplyKeyboardRemove
        await message.reply_text("Action cancelled.", reply_markup=ReplyKeyboardRemove())
        return

    state = state_manager.get_state(user.id)
    if state not in (States.WAITING_FOR_WELCOME_MSG, States.WAITING_FOR_WELCOME_PHOTO):
        message.continue_propagation()
        return

    data = state_manager.get_data(user.id)
    target_chat_id = data.get("target_chat_id")

    if state == States.WAITING_FOR_WELCOME_MSG and target_chat_id:
        if not message.text:
            await message.reply_text("Please provide text for your welcome message.")
            return

        await chat_repo.update_settings(target_chat_id, user.id, {"welcome_text": message.text})
        state_manager.clear_state(user.id)

        await message.reply_text(
            "✅ <b>Custom welcome message saved successfully!</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Back to Chat", callback_data=f"chat:manage:{target_chat_id}")],
                [InlineKeyboardButton("📝 View Message", callback_data=f"chat:welcome_msg:{target_chat_id}")],
            ])
        )

    elif state == States.WAITING_FOR_WELCOME_PHOTO and target_chat_id:
        if not message.photo:
            await message.reply_text("Please send an actual image photo (compressed photo, not document).")
            return

        # Get highest resolution photo file_id
        photo_file_id = message.photo.file_id
        await chat_repo.update_settings(target_chat_id, user.id, {"welcome_photo": photo_file_id})
        state_manager.clear_state(user.id)

        await message.reply_text(
            "✅ <b>Welcome banner photo updated successfully!</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ Back to Chat", callback_data=f"chat:manage:{target_chat_id}")],
                [InlineKeyboardButton("🖼 View Banner Settings", callback_data=f"chat:welcome_photo:{target_chat_id}")],
            ])
        )
