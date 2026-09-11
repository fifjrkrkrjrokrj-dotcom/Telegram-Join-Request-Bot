from pyrogram import Client, filters
from pyrogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from database.chats import chat_repo
from database.required_chats import required_chat_repo
from services.telegram import telegram_service
from keyboards.chats import (
    get_required_chats_menu_keyboard,
    get_single_required_chat_keyboard,
    get_select_chat_reply_keyboard,
)
from utils.helpers import format_card, extract_chat_identifier, extract_chat_from_message, escape_html
from utils.states import state_manager, States
from utils.logger import logger
from pyrogram.types import ReplyKeyboardRemove

@Client.on_callback_query(filters.regex(r"^chat:req_chats:(-?\d+)$"))
async def cb_required_chats_list(client: Client, callback_query: CallbackQuery):
    """List all mandatory verification channels/groups for target chat."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))
    state_manager.clear_state(user.id)

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    required_chats = await required_chat_repo.get_required_chats(chat_id)

    content = (
        f"🔗 <b>Mandatory Verification Requirements for {escape_html(chat.get('title', ''))}</b>\n\n"
        "Users sending a Join Request must be a member of <b>ALL</b> configured channels/groups below before their request is approved."
    )
    text = format_card("🔗 REQUIRED CHATS", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_required_chats_menu_keyboard(chat_id, required_chats)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:req_add:(-?\d+)$"))
async def cb_prompt_add_required_chat(client: Client, callback_query: CallbackQuery):
    """Prompt user to provide username or link of required channel/group."""
    user = callback_query.from_user
    chat_id = int(callback_query.matches[0].group(1))

    chat = await chat_repo.get_chat_for_owner(chat_id, user.id)
    if not chat:
        await callback_query.answer("❌ Chat not found.", show_alert=True)
        return

    state_manager.set_state(user.id, States.WAITING_FOR_REQ_CHAT_LINK, {"target_chat_id": chat_id})
    content = (
        "<b>Add Required Verification Channel/Group:</b>\n\n"
        "⚡ <b>Option 1 (1-Tap Select):</b> Tap the button on your keyboard to pick your channel/group!\n\n"
        "👉 <b>Option 2:</b> <b>FORWARD ANY POST/MESSAGE</b> from the required channel/group here!\n\n"
        "👉 <b>Option 3:</b> Send the <b>@username</b> or numeric <b>Chat ID</b> (e.g. <code>-100123456789</code>)\n\n"
        "<i>Note: If the required channel is private, ensure this bot is an Admin there to check user memberships!</i>"
    )
    text = format_card("➕ ADD REQUIRED CHAT", content)
    reply_kb = get_select_chat_reply_keyboard()
    if reply_kb:
        try:
            await callback_query.message.reply_text(
                text="👇 <i>Pick a channel using the keyboard below or forward a post:</i>",
                reply_markup=reply_kb
            )
        except Exception as e:
            logger.warning(f"Could not send native reply keyboard: {e}")

    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data=f"chat:req_chats:{chat_id}")]
        ])
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:req_view:(-?\d+):([a-fA-F0-9]{24})$"))
async def cb_view_single_required_chat(client: Client, callback_query: CallbackQuery):
    """View and manage individual required chat configuration."""
    user = callback_query.from_user
    match = callback_query.matches[0]
    chat_id = int(match.group(1))
    req_id = match.group(2)
    state_manager.clear_state(user.id)

    req = await required_chat_repo.get_required_chat_by_id(req_id, user.id)
    if not req:
        await callback_query.answer("❌ Requirement not found.", show_alert=True)
        return

    all_reqs = await required_chat_repo.get_required_chats(chat_id)
    req_ids = [str(r["_id"]) for r in all_reqs]
    is_first = (req_ids.index(req_id) == 0) if req_id in req_ids else False
    is_last = (req_ids.index(req_id) == len(req_ids) - 1) if req_id in req_ids else False

    content = (
        f"📢 <b>Title:</b> {escape_html(req.get('title', ''))}\n"
        f"🆔 <b>Chat ID:</b> <code>{req.get('req_chat_id')}</code>\n"
        f"🏷 <b>Type:</b> <code>{req.get('type', 'channel').capitalize()}</code>\n"
        f"🔘 <b>Button Text:</b> <code>{escape_html(req.get('button_text', ''))}</code>\n"
        f"🔗 <b>Invite Link:</b> {req.get('invite_link') or 'N/A'}\n"
        f"🔢 <b>Display Order:</b> <code>#{req.get('order', 1)}</code>"
    )
    text = format_card("⚙️ REQUIRED CHAT CONFIG", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_single_required_chat_keyboard(chat_id, req_id, is_first, is_last)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:req_move:(-?\d+):([a-fA-F0-9]{24}):(up|down)$"))
async def cb_move_required_chat(client: Client, callback_query: CallbackQuery):
    """Move required chat up or down in the display hierarchy."""
    user = callback_query.from_user
    match = callback_query.matches[0]
    chat_id = int(match.group(1))
    req_id = match.group(2)
    direction = match.group(3)

    moved = await required_chat_repo.move_order(req_id, user.id, direction)
    if moved:
        await callback_query.answer(f"Moved {direction}!")
    else:
        await callback_query.answer("Cannot move further.")

    # Refresh view
    await cb_view_single_required_chat(client, callback_query)


@Client.on_callback_query(filters.regex(r"^chat:req_delete:(-?\d+):([a-fA-F0-9]{24})$"))
async def cb_delete_required_chat(client: Client, callback_query: CallbackQuery):
    """Remove required chat constraint."""
    user = callback_query.from_user
    match = callback_query.matches[0]
    chat_id = int(match.group(1))
    req_id = match.group(2)

    deleted = await required_chat_repo.delete_required_chat(req_id, user.id)
    if deleted:
        await callback_query.answer("🗑 Requirement deleted.", show_alert=True)
    else:
        await callback_query.answer("❌ Could not delete requirement.", show_alert=True)

    # Return to required chats list
    all_reqs = await required_chat_repo.get_required_chats(chat_id)
    content = "🔗 <b>Mandatory Verification Requirements:</b>"
    text = format_card("🔗 REQUIRED CHATS", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_required_chats_menu_keyboard(chat_id, all_reqs)
    )


@Client.on_callback_query(filters.regex(r"^chat:req_edit_text:(-?\d+):([a-fA-F0-9]{24})$"))
async def cb_prompt_edit_button_text(client: Client, callback_query: CallbackQuery):
    """Prompt user to send new button text."""
    user = callback_query.from_user
    match = callback_query.matches[0]
    chat_id = int(match.group(1))
    req_id = match.group(2)

    state_manager.set_state(
        user.id,
        States.WAITING_FOR_REQ_BTN_TEXT,
        {"target_chat_id": chat_id, "req_id": req_id}
    )
    content = "Send the new <b>Button Text</b> (e.g., <code>📢 Join VIP Updates</code>):"
    text = format_card("✏️ EDIT BUTTON TEXT", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data=f"chat:req_view:{chat_id}:{req_id}")]
        ])
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^chat:req_edit_link:(-?\d+):([a-fA-F0-9]{24})$"))
async def cb_prompt_edit_invite_link(client: Client, callback_query: CallbackQuery):
    """Prompt user to send custom invite URL."""
    user = callback_query.from_user
    match = callback_query.matches[0]
    chat_id = int(match.group(1))
    req_id = match.group(2)

    state_manager.set_state(
        user.id,
        States.WAITING_FOR_REQ_INVITE_LINK,
        {"target_chat_id": chat_id, "req_id": req_id}
    )
    content = "Send the new <b>Invite URL</b> (e.g., <code>https://t.me/+AbCdEfGhIjK</code>):"
    text = format_card("🔗 EDIT INVITE LINK", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Cancel", callback_data=f"chat:req_view:{chat_id}:{req_id}")]
        ])
    )
    await callback_query.answer()


# Message handler for required chat interactive inputs
@Client.on_message(filters.private & ~filters.command(["start", "help", "cancel"]))
async def handle_required_chat_inputs(client: Client, message: Message):
    """Process incoming text or forwarded messages for adding or modifying required chat settings."""
    user = message.from_user
    if not user:
        return

    # Handle cancel button from reply keyboard
    if message.text == "❌ Cancel":
        state_manager.clear_state(user.id)
        await message.reply_text("Action cancelled.", reply_markup=ReplyKeyboardRemove())
        return

    state = state_manager.get_state(user.id)
    if state not in (States.WAITING_FOR_REQ_CHAT_LINK, States.WAITING_FOR_REQ_BTN_TEXT, States.WAITING_FOR_REQ_INVITE_LINK):
        message.continue_propagation()
        return

    data = state_manager.get_data(user.id)
    target_chat_id = data.get("target_chat_id")

    if not target_chat_id:
        message.continue_propagation()
        return

    if state == States.WAITING_FOR_REQ_CHAT_LINK:
        raw_text = (message.text or message.caption or "").strip()
        if "t.me/+" in raw_text or "t.me/joinchat/" in raw_text:
            await message.reply_text(
                "⚠️ <b>Private invite links cannot be resolved directly by Telegram bots.</b>\n\n"
                "👉 Simply <b>FORWARD ANY POST/MESSAGE</b> from the required channel or group to this chat!"
            )
            return

        extracted = extract_chat_from_message(message)
        identifier = extracted.get("id")

        if not identifier:
            await message.reply_text("❌ Invalid chat identifier. Please forward a post or send a valid @username.")
            return

        status_msg = await message.reply_text("🔍 Resolving required chat...")
        chat, err = await telegram_service.resolve_chat(client, identifier)

        # Extract details from resolved chat or forwarded metadata
        if chat:
            chat_id = chat.id
            chat_title = chat.title
            chat_username = chat.username
            chat_type = chat.type.value if hasattr(chat.type, "value") else str(chat.type)
            invite_link = await telegram_service.get_chat_invite_link(client, chat.id)
            if not invite_link and chat_username:
                invite_link = f"https://t.me/{chat_username}"
        else:
            # If resolution failed but we have forward metadata
            if extracted.get("is_forward") and extracted.get("id"):
                chat_id = int(extracted["id"]) if str(extracted["id"]).lstrip("-").isdigit() else extracted["id"]
                chat_title = extracted.get("title") or f"Chat {chat_id}"
                chat_username = extracted.get("username")
                chat_type = extracted.get("type") or "channel"
                invite_link = f"https://t.me/{chat_username}" if chat_username else None
            else:
                state_manager.clear_state(user.id)
                await status_msg.edit_text(f"❌ Could not resolve chat: {err or 'Unknown error'}\n\nPlease ensure the bot is added as Admin in the channel first.")
                return

        await required_chat_repo.add_required_chat(
            owner_id=user.id,
            target_chat_id=target_chat_id,
            req_chat_id=chat_id,
            title=chat_title,
            chat_type=chat_type,
            username=chat_username,
            invite_link=invite_link
        )
        state_manager.clear_state(user.id)

        note = ""
        if not invite_link:
            note = "\n\n⚠️ <i>No invite link was automatically found. Please tap 'Edit Invite Link' below to set the button URL for applicants!</i>"

        content = (
            f"✅ <b>Required Chat Added!</b>\n\n"
            f"💬 <b>Title:</b> {escape_html(chat_title)}\n"
            f"🆔 <b>ID:</b> <code>{chat_id}</code>\n"
            f"🔗 <b>Invite Link:</b> {invite_link or 'Not set'}{note}\n\n"
            "Applicants will now be required to join this chat before approval."
        )
        await status_msg.edit_text(
            format_card("✅ REQUIREMENT SAVED", content),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 View Required Chats", callback_data=f"chat:req_chats:{target_chat_id}")],
                [InlineKeyboardButton("⚙️ Chat Dashboard", callback_data=f"chat:manage:{target_chat_id}")]
            ])
        )

    elif state == States.WAITING_FOR_REQ_BTN_TEXT:
        req_id = data.get("req_id")
        if not req_id or not message.text:
            return

        await required_chat_repo.update_required_chat(req_id, user.id, {"button_text": message.text.strip()})
        state_manager.clear_state(user.id)
        await message.reply_text(
            "✅ <b>Button text updated!</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ View Config", callback_data=f"chat:req_view:{target_chat_id}:{req_id}")],
                [InlineKeyboardButton("🔗 Required Chats", callback_data=f"chat:req_chats:{target_chat_id}")]
            ])
        )

    elif state == States.WAITING_FOR_REQ_INVITE_LINK:
        req_id = data.get("req_id")
        if not req_id or not message.text:
            return

        new_link = message.text.strip()
        await required_chat_repo.update_required_chat(req_id, user.id, {"invite_link": new_link})
        state_manager.clear_state(user.id)
        await message.reply_text(
            "✅ <b>Invite URL updated!</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ View Config", callback_data=f"chat:req_view:{target_chat_id}:{req_id}")],
                [InlineKeyboardButton("🔗 Required Chats", callback_data=f"chat:req_chats:{target_chat_id}")]
            ])
        )
