from pyrogram import Client
from pyrogram.types import ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from database.chats import chat_repo
from database.users import user_repo
from utils.helpers import format_card, escape_html
from utils.logger import logger

@Client.on_chat_member_updated()
async def handle_bot_added_to_chat(client: Client, chat_member_updated: ChatMemberUpdated):
    """
    Automatically detect when the bot is promoted to administrator in any channel or group.
    Instantly registers the chat for the user who added it and sends them a DM.
    """
    new_member = chat_member_updated.new_chat_member
    old_member = chat_member_updated.old_chat_member
    chat = chat_member_updated.chat
    from_user = chat_member_updated.from_user

    if not new_member or not new_member.user.is_self:
        return

    # Check if bot became admin/owner
    if new_member.status in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
        logger.info(f"[AUTO_DETECT] Bot promoted to admin in {chat.id} ({chat.title}) by user {from_user.id if from_user else 'Unknown'}")
        
        if not from_user:
            return

        # Register user in DB
        await user_repo.upsert_user(
            user_id=from_user.id,
            first_name=from_user.first_name,
            last_name=from_user.last_name,
            username=from_user.username
        )

        chat_type = chat.type.value if hasattr(chat.type, "value") else str(chat.type)
        await chat_repo.add_chat(
            chat_id=chat.id,
            owner_id=from_user.id,
            title=chat.title,
            chat_type=chat_type,
            username=chat.username
        )

        content = (
            f"💬 <b>Chat:</b> {escape_html(chat.title)}\n"
            f"🏷 <b>Type:</b> <code>{chat_type.capitalize()}</code>\n"
            f"🆔 <b>ID:</b> <code>{chat.id}</code>\n\n"
            "✅ <b>Bot is verified as Administrator!</b>\n"
            "This chat has been automatically connected to your Join Verify dashboard.\n\n"
            "Tap below to add mandatory sponsor channels or customize your welcome message."
        )

        try:
            await client.send_message(
                chat_id=from_user.id,
                text=format_card("🎉 CHAT AUTO-CONNECTED", content),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⚙️ Configure Chat", callback_data=f"chat:manage:{chat.id}")],
                    [InlineKeyboardButton("🔗 Add Required Chats", callback_data=f"chat:req_chats:{chat.id}")],
                    [InlineKeyboardButton("📂 My Chats", callback_data="menu:my_chats")]
                ])
            )
        except Exception as e:
            logger.debug(f"Could not send auto-connect DM to {from_user.id}: {e}")
