from pyrogram import Client
from pyrogram.types import ChatJoinRequest
from pyrogram.errors import (
    UserIsBlocked,
    PeerIdInvalid,
    FloodWait,
    RPCError,
)
from database.chats import chat_repo
from database.required_chats import required_chat_repo
from database.verification import verification_repo
from database.statistics import statistics_repo
from services.approval import approval_service
from keyboards.verification import get_verification_dm_keyboard
from utils.helpers import format_card, interpolate_template, escape_html
from utils.logger import logger

@Client.on_chat_join_request()
async def handle_incoming_join_request(client: Client, join_request: ChatJoinRequest):
    """
    Handle incoming Telegram ChatJoinRequest events.
    Creates a verification session and dispatches DM verification instructions.
    """
    user = join_request.from_user
    chat = join_request.chat

    if not user or not chat:
        return

    logger.info(f"[JOIN_REQUEST] User {user.id} ({user.first_name}) requested to join {chat.id} ({chat.title})")

    # 1. Look up target chat configuration
    chat_config = await chat_repo.get_chat(chat.id)
    if not chat_config:
        logger.debug(f"Chat {chat.id} is not configured on this platform. Ignoring request.")
        return

    if not chat_config.get("enabled", True):
        logger.info(f"Chat {chat.id} verification is paused. Ignoring request.")
        return

    owner_id = chat_config["owner_id"]

    # 2. Record statistics & audit log
    await statistics_repo.record_request(chat.id, owner_id)
    await verification_repo.log_event(
        user_id=user.id,
        target_chat_id=chat.id,
        owner_id=owner_id,
        action="JOIN_REQUEST",
        details={
            "first_name": user.first_name,
            "username": user.username,
            "chat_title": chat.title
        }
    )

    # 3. Optional Admin Notification for Incoming Request
    if chat_config.get("admin_notifications", True):
        try:
            admin_card = format_card(
                "📥 NEW JOIN REQUEST",
                f"💬 <b>Chat:</b> {escape_html(chat.title)}\n"
                f"👤 <b>Applicant:</b> {escape_html(user.first_name)} "
                f"({'@' + user.username if user.username else 'ID: ' + str(user.id)})\n"
                f"⏳ Verification DM dispatched."
            )
            await client.send_message(chat_id=owner_id, text=admin_card)
        except Exception as e:
            logger.debug(f"Could not dispatch admin notification to owner {owner_id}: {e}")

    # 4. Fetch mandatory required verification chats
    required_chats = await required_chat_repo.get_required_chats(chat.id)

    # 5. Fast path: If NO requirements are set and auto-approve is ON -> approve instantly
    if not required_chats and chat_config.get("auto_approve", True):
        logger.info(f"No requirements configured for chat {chat.id}. Approving immediately.")
        await approval_service.approve_user(
            client=client,
            target_chat_id=chat.id,
            user_id=user.id,
            owner_id=owner_id,
            user_info={"first_name": user.first_name, "username": user.username, "user_id": user.id}
        )
        try:
            welcome_direct = format_card(
                "🎉 WELCOME!",
                f"Hello {escape_html(user.first_name)}! 👋\n\n"
                f"Your request to join <b>{escape_html(chat.title)}</b> has been approved. Welcome to the community!"
            )
            await client.send_message(chat_id=user.id, text=welcome_direct)
        except Exception:
            pass
        return

    # 6. Create verification session in MongoDB
    timeout_minutes = chat_config.get("verification_timeout", 30)
    session = await verification_repo.create_session(
        user_id=user.id,
        target_chat_id=chat.id,
        owner_id=owner_id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username,
        timeout_minutes=timeout_minutes
    )

    # 7. Prepare personalized verification DM
    default_text = (
        "Welcome, {first_name}! 👋\n\n"
        "Your request to join <b>{chat_title}</b> has been received.\n\n"
        "Before your request can be approved, please join all required channels/groups below, then tap <b>VERIFY</b>."
    )
    raw_template = chat_config.get("welcome_text") or default_text
    dm_text = interpolate_template(
        template=raw_template,
        first_name=escape_html(user.first_name),
        last_name=escape_html(user.last_name or ""),
        username=user.username,
        user_id=user.id,
        chat_title=escape_html(chat.title),
        chat_username=chat.username
    )
    card_text = format_card("✦ JOIN VERIFICATION ✦", dm_text)
    keyboard = get_verification_dm_keyboard(session["session_id"], required_chats)

    # 8. Send Verification DM
    welcome_photo = chat_config.get("welcome_photo")
    try:
        if welcome_photo:
            await client.send_photo(
                chat_id=user.id,
                photo=welcome_photo,
                caption=card_text,
                reply_markup=keyboard
            )
        else:
            await client.send_message(
                chat_id=user.id,
                text=card_text,
                reply_markup=keyboard
            )
        logger.info(f"[DM_SENT] Verification DM sent to user={user.id} for chat={chat.id}")

    except UserIsBlocked:
        logger.warning(f"User {user.id} has blocked the bot. Cannot deliver verification DM.")
    except PeerIdInvalid:
        logger.warning(f"PeerIdInvalid for user {user.id}. Cannot message user directly.")
    except RPCError as e:
        logger.error(f"RPCError sending verification DM to user {user.id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending verification DM to user {user.id}: {e}")
