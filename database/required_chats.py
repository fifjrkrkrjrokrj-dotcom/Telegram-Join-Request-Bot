from datetime import datetime
from typing import Optional, Dict, Any, List
from bson import ObjectId
from database.mongo import db

class RequiredChatRepository:
    """Manages mandatory channels/groups required for membership verification."""

    @property
    def collection(self):
        return db.db.required_chats

    async def add_required_chat(
        self,
        owner_id: int,
        target_chat_id: int,
        req_chat_id: int,
        title: str,
        chat_type: str,
        username: Optional[str] = None,
        invite_link: Optional[str] = None,
        button_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a channel/group requirement for a target chat."""
        # Find next order index
        highest = await self.collection.find_one(
            {"target_chat_id": target_chat_id},
            sort=[("order", -1)]
        )
        next_order = (highest.get("order", 0) + 1) if highest else 1
        
        prefix = "📢" if chat_type == "channel" else "👥"
        default_btn_text = button_text or f"{prefix} Join {title}"

        doc = {
            "owner_id": owner_id,
            "target_chat_id": target_chat_id,
            "req_chat_id": req_chat_id,
            "title": title,
            "username": username,
            "invite_link": invite_link,
            "button_text": default_btn_text,
            "type": chat_type,
            "order": next_order,
            "created_at": datetime.utcnow()
        }

        # Upsert based on target_chat_id and req_chat_id
        await self.collection.update_one(
            {"target_chat_id": target_chat_id, "req_chat_id": req_chat_id},
            {"$set": doc},
            upsert=True
        )
        return doc

    async def get_required_chats(self, target_chat_id: int) -> List[Dict[str, Any]]:
        """Get all required chats for a target chat, ordered for display."""
        cursor = self.collection.find({"target_chat_id": target_chat_id}).sort("order", 1)
        return await cursor.to_list(length=100)

    async def get_required_chat_by_id(self, req_id: str, owner_id: int) -> Optional[Dict[str, Any]]:
        """Fetch single required chat document by ObjectId ensuring owner authorization."""
        try:
            obj_id = ObjectId(req_id)
        except Exception:
            return None
        return await self.collection.find_one({"_id": obj_id, "owner_id": owner_id})

    async def delete_required_chat(self, req_id: str, owner_id: int) -> bool:
        """Remove a required chat rule."""
        try:
            obj_id = ObjectId(req_id)
        except Exception:
            return False
        result = await self.collection.delete_one({"_id": obj_id, "owner_id": owner_id})
        return result.deleted_count > 0

    async def delete_all_for_target_chat(self, target_chat_id: int, owner_id: int) -> int:
        """Remove all requirement rules when target chat is deleted."""
        result = await self.collection.delete_many({"target_chat_id": target_chat_id, "owner_id": owner_id})
        return result.deleted_count

    async def update_required_chat(self, req_id: str, owner_id: int, updates: Dict[str, Any]) -> bool:
        """Update button text or invite link."""
        try:
            obj_id = ObjectId(req_id)
        except Exception:
            return False
        result = await self.collection.update_one(
            {"_id": obj_id, "owner_id": owner_id},
            {"$set": updates}
        )
        return result.modified_count > 0

    async def move_order(self, req_id: str, owner_id: int, direction: str) -> bool:
        """Reorder required chats (up or down)."""
        current = await self.get_required_chat_by_id(req_id, owner_id)
        if not current:
            return False

        target_chat_id = current["target_chat_id"]
        current_order = current.get("order", 1)

        if direction == "up":
            neighbor = await self.collection.find_one(
                {"target_chat_id": target_chat_id, "order": {"$lt": current_order}},
                sort=[("order", -1)]
            )
        else:
            neighbor = await self.collection.find_one(
                {"target_chat_id": target_chat_id, "order": {"$gt": current_order}},
                sort=[("order", 1)]
            )

        if not neighbor:
            return False

        # Swap orders
        await self.collection.update_one(
            {"_id": current["_id"]},
            {"$set": {"order": neighbor["order"]}}
        )
        await self.collection.update_one(
            {"_id": neighbor["_id"]},
            {"$set": {"order": current_order}}
        )
        return True


required_chat_repo = RequiredChatRepository()
