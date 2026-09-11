import asyncio
from typing import List, Dict, Any
from pyrogram import Client
from pyrogram.enums import ChatMemberStatus
from pyrogram.errors import (
    UserNotParticipant,
    FloodWait,
    ChatAdminRequired,
    PeerIdInvalid,
    RPCError
)
from utils.logger import logger
from database.required_chats import required_chat_repo

class MembershipService:
    """Strictly checks Telegram channel/group membership via official API without scraping."""

    async def verify_all_requirements(
        self,
        client: Client,
        user_id: int,
        target_chat_id: int
    ) -> Dict[str, Any]:
        """
        Check if user is a member of all required channels/groups configured for target_chat_id.
        Returns: {
            "is_valid": bool,
            "total_required": int,
            "joined_count": int,
            "missing_chats": List[Dict[str, Any]]
        }
        """
        required_chats = await required_chat_repo.get_required_chats(target_chat_id)
        
        # If no required chats are set, verification succeeds immediately
        if not required_chats:
            return {
                "is_valid": True,
                "total_required": 0,
                "joined_count": 0,
                "missing_chats": []
            }

        missing_chats: List[Dict[str, Any]] = []
        joined_count = 0

        for req in required_chats:
            req_chat_id = req["req_chat_id"]
            title = req["title"]
            button_text = req.get("button_text") or f"📢 Join {title}"
            invite_link = req.get("invite_link") or (f"https://t.me/{req['username']}" if req.get("username") else None)

            is_member, status_reason = await self._check_single_chat_membership(
                client=client,
                chat_id=req_chat_id,
                user_id=user_id
            )

            if is_member:
                joined_count += 1
            else:
                missing_chats.append({
                    "req_chat_id": req_chat_id,
                    "title": title,
                    "button_text": button_text,
                    "invite_link": invite_link,
                    "type": req.get("type", "channel"),
                    "status_reason": status_reason
                })

        is_valid = (len(missing_chats) == 0)
        return {
            "is_valid": is_valid,
            "total_required": len(required_chats),
            "joined_count": joined_count,
            "missing_chats": missing_chats
        }

    async def _check_single_chat_membership(
        self,
        client: Client,
        chat_id: int,
        user_id: int,
        retry_count: int = 0
    ) -> (bool, str):
        """Query Pyrogram get_chat_member for user status."""
        try:
            member = await client.get_chat_member(chat_id, user_id)
            
            # Status evaluation
            if member.status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER):
                return True, "member"
            elif member.status == ChatMemberStatus.RESTRICTED:
                # If restricted but still in the chat
                if getattr(member, "is_member", True):
                    return True, "restricted_member"
                return False, "restricted_non_member"
            elif member.status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                return False, member.status.value
            else:
                return False, "unknown_status"

        except UserNotParticipant:
            return False, "not_participant"
        except FloodWait as e:
            if retry_count < 2:
                logger.warning(f"FloodWait in membership check ({e.value}s). Retrying...")
                await asyncio.sleep(min(e.value, 5.0))
                return await self._check_single_chat_membership(client, chat_id, user_id, retry_count + 1)
            return False, "flood_wait"
        except ChatAdminRequired:
            logger.error(f"Bot lacks admin permissions to check member in required chat {chat_id}")
            # If bot cannot check, we fail safe
            return False, "bot_admin_required"
        except PeerIdInvalid:
            logger.error(f"PeerIdInvalid for required chat {chat_id}")
            return False, "invalid_peer"
        except RPCError as e:
            logger.warning(f"RPCError checking membership for user {user_id} in {chat_id}: {e}")
            return False, "rpc_error"
        except Exception as e:
            logger.error(f"Unexpected error in membership check: {e}")
            return False, "error"


membership_service = MembershipService()
