import asyncio
from typing import Optional, Tuple, Dict, Any, List
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus, ChatType
from pyrogram.errors import (
    FloodWait,
    ChatAdminRequired,
    UserNotParticipant,
    PeerIdInvalid,
    UsernameInvalid,
    UsernameNotOccupied,
    RPCError,
)
from utils.logger import logger

class TelegramService:
    """High-level wrapper for Pyrogram Telegram API interactions."""

    async def resolve_chat(self, client: Client, chat_identifier: str) -> Tuple[Optional[Any], Optional[str]]:
        """
        Attempt to resolve a chat by username, ID, or invite link.
        Returns: (Chat object, Error message)
        """
        try:
            # If numeric string, convert to int
            if isinstance(chat_identifier, str) and chat_identifier.lstrip("-").isdigit():
                chat_identifier = int(chat_identifier)

            chat = await client.get_chat(chat_identifier)
            return chat, None
        except FloodWait as e:
            logger.warning(f"FloodWait encountered during get_chat: {e.value}s")
            return None, f"Telegram rate limit encountered. Please try again in {e.value} seconds."
        except (UsernameInvalid, UsernameNotOccupied):
            return None, "Invalid or non-existent Telegram username/link."
        except PeerIdInvalid:
            return None, "Bot cannot access this chat. Make sure you added the bot to the chat first."
        except RPCError as e:
            logger.error(f"RPCError resolving chat {chat_identifier}: {e}")
            err_text = str(e.MESSAGE or str(e))
            if "method cannot be used by bots" in err_text.lower() or ("bot" in err_text.lower() and "invite" in err_text.lower()):
                return None, "Telegram does not permit bots to resolve private invite links (t.me/+) directly. Please simply FORWARD any message/post from your channel/group to this bot, or send its numeric chat ID (e.g. -100123456789)."
            return None, f"Could not access chat: {err_text}"
        except Exception as e:
            logger.error(f"Unexpected error resolving chat {chat_identifier}: {e}")
            return None, "An unexpected error occurred while looking up this chat."

    async def verify_bot_permissions(self, client: Client, chat_id: int) -> Dict[str, Any]:
        """
        Inspect bot's administrative privileges in the target chat.
        Returns a detailed checklist of capabilities.
        """
        try:
            me = await client.get_me()
            member = await client.get_chat_member(chat_id, me.id)

            if member.status not in (ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                return {
                    "is_admin": False,
                    "can_invite_users": False,
                    "can_manage_chat": False,
                    "missing_permissions": ["Administrator Privileges"],
                    "error": "Bot is not an administrator in this chat."
                }

            # If owner, all permissions are granted
            if member.status == ChatMemberStatus.OWNER:
                return {
                    "is_admin": True,
                    "can_invite_users": True,
                    "can_manage_chat": True,
                    "missing_permissions": [],
                    "error": None
                }

            # Check individual privileges
            privileges = member.privileges
            can_invite = bool(privileges and privileges.can_invite_users)
            can_manage = bool(privileges and privileges.can_manage_chat)

            missing: List[str] = []
            if not can_invite:
                missing.append("Invite Users via Link / Manage Join Requests")

            return {
                "is_admin": True,
                "can_invite_users": can_invite,
                "can_manage_chat": can_manage,
                "missing_permissions": missing,
                "error": None if not missing else "Missing essential admin permissions."
            }

        except FloodWait as e:
            await asyncio.sleep(e.value)
            return await self.verify_bot_permissions(client, chat_id)
        except ChatAdminRequired:
            return {
                "is_admin": False,
                "can_invite_users": False,
                "can_manage_chat": False,
                "missing_permissions": ["Administrator Privileges"],
                "error": "Bot is not an administrator in this chat."
            }
        except RPCError as e:
            logger.error(f"Error checking bot permissions for chat {chat_id}: {e}")
            return {
                "is_admin": False,
                "can_invite_users": False,
                "can_manage_chat": False,
                "missing_permissions": ["Access to Chat"],
                "error": str(e)
            }

    async def get_chat_invite_link(self, client: Client, chat_id: int) -> Optional[str]:
        """Fetch or create a valid invite link for a channel/group."""
        try:
            chat = await client.get_chat(chat_id)
            if chat.username:
                return f"https://t.me/{chat.username}"
            if chat.invite_link:
                return chat.invite_link
            
            # Export or create link
            link = await client.export_chat_invite_link(chat_id)
            return link
        except Exception as e:
            logger.warning(f"Could not generate invite link for {chat_id}: {e}")
            return None


telegram_service = TelegramService()
