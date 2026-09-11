from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from database.chats import chat_repo
from database.verification import verification_repo
from database.statistics import statistics_repo
from services.membership import membership_service
from services.approval import approval_service
from keyboards.verification import get_missing_verification_keyboard
from utils.helpers import format_card, escape_html
from utils.rate_limit import rate_limiter
from config import settings
from utils.logger import logger

@Client.on_callback_query(filters.regex(r"^verify:([a-fA-F0-9\-]{36})$"))
async def handle_verify_button(client: Client, callback_query: CallbackQuery):
    """
    Execute membership check when applicant taps 'VERIFY' button in private DM.
    """
    user = callback_query.from_user
    session_id = callback_query.matches[0].group(1)

    # 1. Rate Limiting Protection (Prevent spam clicking)
    is_limited, remaining = rate_limiter.is_rate_limited("verify", user.id, settings.RATE_LIMIT_VERIFY_SECONDS)
    if is_limited:
        await callback_query.answer(f"⏳ Please wait {remaining:.1f}s before checking again.", show_alert=False)
        return

    # 2. Look up session in MongoDB
    session = await verification_repo.get_session(session_id)
    if not session:
        await callback_query.answer("❌ Verification session not found or expired.", show_alert=True)
        return

    # Security check: Ensure caller is the authenticated applicant
    if session["user_id"] != user.id:
        await callback_query.answer("⛔ This verification is for another user.", show_alert=True)
        return

    # Check if already approved
    if session.get("status") == "approved":
        await callback_query.answer("🎉 You are already approved!", show_alert=True)
        return

    # Check expiration
    if session.get("expires_at") and session["expires_at"] < datetime.utcnow():
        await verification_repo.mark_expired(session_id)
        await callback_query.answer("⏱ Verification session has expired.", show_alert=True)
        content = (
            "⏱ <b>Verification Session Expired</b>\n\n"
            "Your verification window has closed. Please submit a new Join Request to the channel or group."
        )
        try:
            if callback_query.message.photo:
                await callback_query.message.edit_caption(format_card("⏱ EXPIRED", content))
            else:
                await callback_query.message.edit_text(format_card("⏱ EXPIRED", content))
        except Exception:
            pass
        return

    # 3. Increment attempts
    attempts = await verification_repo.increment_attempts(session_id)
    target_chat_id = session["target_chat_id"]
    owner_id = session["owner_id"]

    chat_config = await chat_repo.get_chat(target_chat_id)
    chat_title = chat_config.get("title", "Community") if chat_config else "Community"

    # 4. Perform official Telegram membership check
    report = await membership_service.verify_all_requirements(
        client=client,
        user_id=user.id,
        target_chat_id=target_chat_id
    )

    # -------------------------------------------------------------
    # Case A: Verification Incomplete (User is missing required chats)
    # -------------------------------------------------------------
    if not report["is_valid"]:
        logger.info(f"[VERIFY] user={user.id} chat={target_chat_id} result=INCOMPLETE missing={len(report['missing_chats'])}")
        await statistics_repo.record_failed(target_chat_id, owner_id)
        await verification_repo.log_event(
            user_id=user.id,
            target_chat_id=target_chat_id,
            owner_id=owner_id,
            action="VERIFY_ATTEMPT_FAILED",
            details={"missing_count": len(report["missing_chats"]), "attempt": attempts}
        )

        missing_list = "\n".join([f"• <b>{escape_html(m['title'])}</b>" for m in report["missing_chats"]])
        content = (
            "❌ <b>Verification Incomplete!</b>\n\n"
            "You still need to join the following channels/groups:\n\n"
            f"{missing_list}\n\n"
            "Join all required chats using the buttons below, then tap <b>VERIFY AGAIN</b>."
        )
        card_text = format_card("❌ MISSING REQUIREMENTS", content)
        keyboard = get_missing_verification_keyboard(session_id, report["missing_chats"])

        try:
            if callback_query.message.photo:
                await callback_query.message.edit_caption(caption=card_text, reply_markup=keyboard)
            else:
                await callback_query.message.edit_text(text=card_text, reply_markup=keyboard)
        except Exception as e:
            logger.debug(f"Message edit error on incomplete check: {e}")

        await callback_query.answer("❌ You have not joined all required channels yet.", show_alert=True)
        return

    # -------------------------------------------------------------
    # Case B: Verification SUCCESSFUL (All requirements satisfied)
    # -------------------------------------------------------------
    logger.info(f"[VERIFY] user={user.id} chat={target_chat_id} result=SUCCESS")
    await verification_repo.mark_verified(session_id)
    await statistics_repo.record_verified(target_chat_id, owner_id)
    await verification_repo.log_event(
        user_id=user.id,
        target_chat_id=target_chat_id,
        owner_id=owner_id,
        action="VERIFIED",
        details={"session_id": session_id, "attempts": attempts}
    )

    auto_approve = chat_config.get("auto_approve", True) if chat_config else True

    if auto_approve:
        # Execute instant approval
        success, reason = await approval_service.approve_user(
            client=client,
            target_chat_id=target_chat_id,
            user_id=user.id,
            owner_id=owner_id,
            session_id=session_id,
            user_info={"first_name": user.first_name, "username": user.username, "user_id": user.id}
        )

        content = (
            f"🎉 <b>Verification Successful!</b>\n\n"
            f"Your request to join <b>{escape_html(chat_title)}</b> has been approved.\n\n"
            "Welcome to the community! 🚀"
        )
        card_text = format_card("✅ APPROVED", content)

        try:
            if callback_query.message.photo:
                await callback_query.message.edit_caption(caption=card_text, reply_markup=None)
            else:
                await callback_query.message.edit_text(text=card_text, reply_markup=None)
        except Exception as e:
            logger.debug(f"Message edit error on approval: {e}")

        await callback_query.answer("🎉 Verification successful! Your join request has been approved.", show_alert=True)

    else:
        # Manual approval mode
        content = (
            f"✅ <b>Verification Successful!</b>\n\n"
            f"Your membership requirements for <b>{escape_html(chat_title)}</b> have been verified.\n\n"
            "An administrator has been notified to finalize your admission."
        )
        card_text = format_card("✅ VERIFIED", content)

        try:
            if callback_query.message.photo:
                await callback_query.message.edit_caption(caption=card_text, reply_markup=None)
            else:
                await callback_query.message.edit_text(text=card_text, reply_markup=None)
        except Exception as e:
            logger.debug(f"Message edit error on manual verification: {e}")

        # Notify admin of manual request ready for approval
        if chat_config and chat_config.get("admin_notifications", True):
            try:
                first_name = escape_html(user.first_name)
                username = f"@{user.username}" if user.username else f"ID: {user.id}"
                admin_text = format_card(
                    "🔔 USER VERIFIED (MANUAL APPROVAL)",
                    f"👤 <b>User:</b> {first_name} ({username})\n"
                    f"💬 <b>Chat:</b> {escape_html(chat_title)}\n\n"
                    f"User has passed all verification requirements. You can now approve them in Telegram."
                )
                await client.send_message(chat_id=owner_id, text=admin_text)
            except Exception:
                pass

        await callback_query.answer("✅ Verification passed! Waiting for admin approval.", show_alert=True)
