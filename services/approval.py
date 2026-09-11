import asyncio
from typing import Tuple, Optional, Dict, Any
from pyrogram import Client
from pyrogram.errors import (
    FloodWait,
    ChatAdminRequired,
    UserAlreadyParticipant,
    PeerIdInvalid,
    RPCError,
)
from utils.logger import logger
from utils.helpers import format_card, escape_html
from database.chats import chat_repo
from database.verification import verification_repo
from database.statistics import statistics_repo

class ApprovalService:
    """Manages execution and lifecycle of Telegram Join Request approvals."""

    async def approve_user(
        self,
        client: Client,
        target_chat_id: int,
        user_id: int,
        owner_id: int,
        session_id: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Approve the Telegram Join Request for the user.
        Returns: (success: bool, status_message: str)
        """
        try:
            logger.info(f"[APPROVE] Attempting approval for user={user_id} in chat={target_chat_id}")
            await client.approve_chat_join_request(
                chat_id=target_chat_id,
                user_id=user_id
            )
            
            # Record metrics & audit logs
            if session_id:
                await verification_repo.mark_approved(session_id)
            await statistics_repo.record_approved(target_chat_id, owner_id)
            await verification_repo.log_event(
                user_id=user_id,
                target_chat_id=target_chat_id,
                owner_id=owner_id,
                action="APPROVED",
                details={"session_id": session_id}
            )

            # Check if owner wants admin notifications
            chat = await chat_repo.get_chat(target_chat_id)
            if chat and chat.get("admin_notifications", True):
                await self._notify_owner_approval(client, owner_id, chat, user_info or {"user_id": user_id})

            logger.info(f"[APPROVE] Successfully approved user={user_id} in chat={target_chat_id}")
            return True, "Approved successfully"

        except UserAlreadyParticipant:
            logger.info(f"[APPROVE] User {user_id} is already participant in {target_chat_id}")
            if session_id:
                await verification_repo.mark_approved(session_id)
            return True, "User is already a member"

        except FloodWait as e:
            logger.warning(f"FloodWait during approval ({e.value}s). Retrying...")
            await asyncio.sleep(e.value)
            return await self.approve_user(client, target_chat_id, user_id, owner_id, session_id, user_info)

        except ChatAdminRequired:
            logger.error(f"[APPROVE] Bot lacks admin permission to approve requests in {target_chat_id}")
            return False, "Bot is missing permission to approve join requests in this chat."

        except PeerIdInvalid:
            logger.error(f"[APPROVE] Invalid peer {target_chat_id}")
            return False, "Target chat ID or user ID is invalid."

        except RPCError as e:
            # Check for already handled or expired requests
            err_msg = (e.MESSAGE or str(e)).lower()
            if "hide_requester_missing" in err_msg or "request" in err_msg and "not found" in err_msg:
                logger.info(f"[APPROVE] Request for {user_id} in {target_chat_id} was already resolved.")
                return True, "Request already resolved"
            logger.error(f"[APPROVE] RPCError approving user {user_id} in {target_chat_id}: {e}")
            return False, f"Telegram API error: {e.MESSAGE or str(e)}"

        except Exception as e:
            logger.error(f"[APPROVE] Unexpected error approving user {user_id} in {target_chat_id}: {e}")
            return False, "An unexpected internal error occurred."

    async def decline_user(
        self,
        client: Client,
        target_chat_id: int,
        user_id: int,
        owner_id: int,
        reason: str = "Verification failed"
    ) -> bool:
        """Decline a pending join request."""
        try:
            await client.decline_chat_join_request(
                chat_id=target_chat_id,
                user_id=user_id
            )
            await verification_repo.log_event(
                user_id=user_id,
                target_chat_id=target_chat_id,
                owner_id=owner_id,
                action="DECLINED",
                details={"reason": reason}
            )
            return True
        except Exception as e:
            logger.warning(f"Could not decline request for user {user_id}: {e}")
            return False

    async def _notify_owner_approval(
        self,
        client: Client,
        owner_id: int,
        chat: Dict[str, Any],
        user_info: Dict[str, Any]
    ) -> None:
        """Send a polite approval notification to the chat owner."""
        try:
            first_name = escape_html(user_info.get("first_name", "User"))
            username = f"@{user_info['username']}" if user_info.get("username") else f"ID: {user_info.get('user_id')}"
            chat_title = escape_html(chat.get("title", "Your Chat"))

            text = format_card(
                "🎉 REQUEST APPROVED",
                f"👤 <b>User:</b> {first_name} ({username})\n"
                f"💬 <b>Chat:</b> {chat_title}\n"
                f"✅ Verification completed & request approved automatically."
            )
            await client.send_message(chat_id=owner_id, text=text)
        except Exception as e:
            logger.debug(f"Could not notify owner {owner_id} of approval: {e}")


approval_service = ApprovalService()
