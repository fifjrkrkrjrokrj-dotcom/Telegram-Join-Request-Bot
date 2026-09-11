from datetime import datetime
from typing import Dict, Any, Optional
from database.mongo import db

class StatisticsRepository:
    """Aggregates and tracks real-time and historical verification performance metrics."""

    @property
    def daily_collection(self):
        return db.db.daily_stats

    @property
    def chat_collection(self):
        return db.db.chats

    def _get_today_str(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    async def record_request(self, chat_id: int, owner_id: int) -> None:
        """Increment join request metric counters."""
        today = self._get_today_str()
        # Increment chat lifetime counter
        await self.chat_collection.update_one(
            {"chat_id": chat_id},
            {"$inc": {"stats_total_requests": 1}}
        )
        # Increment daily stat
        await self.daily_collection.update_one(
            {"chat_id": chat_id, "date": today},
            {
                "$set": {"owner_id": owner_id},
                "$inc": {"requests": 1}
            },
            upsert=True
        )

    async def record_verified(self, chat_id: int, owner_id: int) -> None:
        """Increment verified user metric counters."""
        today = self._get_today_str()
        await self.chat_collection.update_one(
            {"chat_id": chat_id},
            {"$inc": {"stats_verified": 1}}
        )
        await self.daily_collection.update_one(
            {"chat_id": chat_id, "date": today},
            {
                "$set": {"owner_id": owner_id},
                "$inc": {"verified": 1}
            },
            upsert=True
        )

    async def record_approved(self, chat_id: int, owner_id: int) -> None:
        """Increment approved requests metric counters."""
        today = self._get_today_str()
        await self.chat_collection.update_one(
            {"chat_id": chat_id},
            {"$inc": {"stats_approved": 1}}
        )
        await self.daily_collection.update_one(
            {"chat_id": chat_id, "date": today},
            {
                "$set": {"owner_id": owner_id},
                "$inc": {"approved": 1}
            },
            upsert=True
        )

    async def record_failed(self, chat_id: int, owner_id: int) -> None:
        """Increment failed / rejected verification metric counters."""
        today = self._get_today_str()
        await self.chat_collection.update_one(
            {"chat_id": chat_id},
            {"$inc": {"stats_failed": 1}}
        )
        await self.daily_collection.update_one(
            {"chat_id": chat_id, "date": today},
            {
                "$set": {"owner_id": owner_id},
                "$inc": {"failed": 1}
            },
            upsert=True
        )

    async def get_chat_stats(self, chat_id: int) -> Dict[str, Any]:
        """Fetch cumulative and today's metrics for a single target chat."""
        chat = await self.chat_collection.find_one({"chat_id": chat_id}) or {}
        today = self._get_today_str()
        today_doc = await self.daily_collection.find_one({"chat_id": chat_id, "date": today}) or {}

        total_req = chat.get("stats_total_requests", 0)
        verified = chat.get("stats_verified", 0)
        approved = chat.get("stats_approved", 0)
        failed = chat.get("stats_failed", 0)
        rate = round((verified / total_req * 100), 1) if total_req > 0 else 0.0

        return {
            "total_requests": total_req,
            "verified": verified,
            "approved": approved,
            "failed": failed,
            "success_rate": rate,
            "today_requests": today_doc.get("requests", 0),
            "today_verified": today_doc.get("verified", 0),
            "today_approved": today_doc.get("approved", 0),
            "today_failed": today_doc.get("failed", 0),
        }

    async def get_owner_today_stats(self, owner_id: int) -> Dict[str, int]:
        """Aggregate today's metrics across all chats for an owner."""
        today = self._get_today_str()
        pipeline = [
            {"$match": {"owner_id": owner_id, "date": today}},
            {
                "$group": {
                    "_id": None,
                    "requests": {"$sum": "$requests"},
                    "verified": {"$sum": "$verified"},
                    "approved": {"$sum": "$approved"},
                    "failed": {"$sum": "$failed"}
                }
            }
        ]
        results = await self.daily_collection.aggregate(pipeline).to_list(length=1)
        if results:
            return {
                "requests": results[0].get("requests", 0),
                "verified": results[0].get("verified", 0),
                "approved": results[0].get("approved", 0),
                "failed": results[0].get("failed", 0),
            }
        return {"requests": 0, "verified": 0, "approved": 0, "failed": 0}

    async def get_owner_total_stats(self, owner_id: int) -> Dict[str, Any]:
        """Aggregate lifetime metrics across all chats for an owner."""
        pipeline = [
            {"$match": {"owner_id": owner_id}},
            {
                "$group": {
                    "_id": None,
                    "total_requests": {"$sum": "$stats_total_requests"},
                    "verified": {"$sum": "$stats_verified"},
                    "approved": {"$sum": "$stats_approved"},
                    "failed": {"$sum": "$stats_failed"}
                }
            }
        ]
        results = await self.chat_collection.aggregate(pipeline).to_list(length=1)
        if results:
            r = results[0]
            total_req = r.get("total_requests", 0)
            verified = r.get("verified", 0)
            rate = round((verified / total_req * 100), 1) if total_req > 0 else 0.0
            return {
                "total_requests": total_req,
                "verified": verified,
                "approved": r.get("approved", 0),
                "failed": r.get("failed", 0),
                "success_rate": rate
            }
        return {"total_requests": 0, "verified": 0, "approved": 0, "failed": 0, "success_rate": 0.0}


statistics_repo = StatisticsRepository()
