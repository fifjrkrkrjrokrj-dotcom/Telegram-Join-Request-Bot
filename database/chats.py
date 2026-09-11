from datetime import datetime
from typing import Optional, Dict, Any, List
from database.mongo import db

class ChatRepository:
    """Manages connected Telegram target groups and channels for owners."""

    @property
    def collection(self):
        return db.db.chats

    async def add_chat(
        self,
        chat_id: int,
        owner_id: int,
        title: str,
        chat_type: str,
        username: Optional[str] = None,
        auto_approve: bool = True,
        verification_timeout: int = 30
    ) -> Dict[str, Any]:
        """Register a new group/channel for verification handling."""
        now = datetime.utcnow()
        doc = {
            "chat_id": chat_id,
            "owner_id": owner_id,
            "title": title,
            "username": username,
            "type": chat_type,
            "enabled": True,
            "auto_approve": auto_approve,
            "admin_notifications": True,
            "verification_timeout": verification_timeout,
            "max_attempts": 5,
            "welcome_text": None,
            "welcome_photo": None,
            "created_at": now,
            "updated_at": now,
        }
        await self.collection.update_one(
            {"chat_id": chat_id},
            {"$set": doc},
            upsert=True
        )
        return doc

    async def get_chat(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Fetch target chat configuration by chat ID."""
        return await self.collection.find_one({"chat_id": chat_id})

    async def get_chat_for_owner(self, chat_id: int, owner_id: int) -> Optional[Dict[str, Any]]:
        """Fetch target chat ensuring the requester is the authentic owner."""
        return await self.collection.find_one({"chat_id": chat_id, "owner_id": owner_id})

    async def get_owner_chats(self, owner_id: int, limit: int = 50, skip: int = 0) -> List[Dict[str, Any]]:
        """Retrieve all chats configured by a specific owner."""
        cursor = self.collection.find({"owner_id": owner_id}).sort("created_at", -1).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def count_owner_chats(self, owner_id: int) -> int:
        """Count total chats registered by owner."""
        return await self.collection.count_documents({"owner_id": owner_id})

    async def count_active_owner_chats(self, owner_id: int) -> int:
        """Count active/enabled chats registered by owner."""
        return await self.collection.count_documents({"owner_id": owner_id, "enabled": True})

    async def update_settings(self, chat_id: int, owner_id: int, updates: Dict[str, Any]) -> bool:
        """Update configurable settings for a chat verifying ownership."""
        updates["updated_at"] = datetime.utcnow()
        result = await self.collection.update_one(
            {"chat_id": chat_id, "owner_id": owner_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def toggle_enabled(self, chat_id: int, owner_id: int) -> Optional[bool]:
        """Toggle active/disabled status for chat."""
        chat = await self.get_chat_for_owner(chat_id, owner_id)
        if not chat:
            return None
        new_status = not chat.get("enabled", True)
        await self.collection.update_one(
            {"chat_id": chat_id, "owner_id": owner_id},
            {"$set": {"enabled": new_status, "updated_at": datetime.utcnow()}}
        )
        return new_status

    async def toggle_auto_approve(self, chat_id: int, owner_id: int) -> Optional[bool]:
        """Toggle auto-approval setting for chat."""
        chat = await self.get_chat_for_owner(chat_id, owner_id)
        if not chat:
            return None
        new_val = not chat.get("auto_approve", True)
        await self.collection.update_one(
            {"chat_id": chat_id, "owner_id": owner_id},
            {"$set": {"auto_approve": new_val, "updated_at": datetime.utcnow()}}
        )
        return new_val

    async def toggle_admin_notifications(self, chat_id: int, owner_id: int) -> Optional[bool]:
        """Toggle admin notifications for incoming/verified requests."""
        chat = await self.get_chat_for_owner(chat_id, owner_id)
        if not chat:
            return None
        new_val = not chat.get("admin_notifications", True)
        await self.collection.update_one(
            {"chat_id": chat_id, "owner_id": owner_id},
            {"$set": {"admin_notifications": new_val, "updated_at": datetime.utcnow()}}
        )
        return new_val

    async def delete_chat(self, chat_id: int, owner_id: int) -> bool:
        """Remove a target chat configuration completely."""
        result = await self.collection.delete_one({"chat_id": chat_id, "owner_id": owner_id})
        return result.deleted_count > 0


chat_repo = ChatRepository()
