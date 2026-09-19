from datetime import datetime
from typing import Optional, Dict, Any
from database.mongo import db

class UserRepository:
    """Handles persistence and lookups for Telegram Bot users/tenants."""

    @property
    def collection(self):
        return db.db.users

    async def upsert_user(
        self,
        user_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """Insert or update user record upon bot interaction."""
        now = datetime.utcnow()
        update_data = {
            "$set": {
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "last_active": now,
            },
            "$setOnInsert": {
                "user_id": user_id,
                "created_at": now,
                "is_banned": False,
            }
        }
        await self.collection.update_one({"user_id": user_id}, update_data, upsert=True)
        return await self.get_user(user_id)

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Fetch user by Telegram user ID."""
        return await self.collection.find_one({"user_id": user_id})

    async def is_banned(self, user_id: int) -> bool:
        """Check if user is banned from using the platform."""
        user = await self.get_user(user_id)
        return bool(user and user.get("is_banned", False))

    async def set_ban_status(self, user_id: int, is_banned: bool) -> bool:
        """Update ban status for a user."""
        result = await self.collection.update_one(
            {"user_id": user_id},
            {"$set": {"is_banned": is_banned, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def get_total_users_count(self) -> int:
        """Return total registered bot users."""
        return await self.collection.count_documents({})

    async def get_all_users(self):
        """Yield all user documents for background tasks like broadcasting."""
        cursor = self.collection.find({})
        async for document in cursor:
            yield document

user_repo = UserRepository()
