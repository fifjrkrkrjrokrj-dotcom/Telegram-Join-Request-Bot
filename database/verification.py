import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from database.mongo import db

class VerificationRepository:
    """Manages join request verification sessions and audit logs."""

    @property
    def sessions(self):
        return db.db.verification_sessions

    @property
    def logs(self):
        return db.db.verification_logs

    async def create_session(
        self,
        user_id: int,
        target_chat_id: int,
        owner_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        timeout_minutes: int = 30
    ) -> Dict[str, Any]:
        """Create a new verification session document."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=timeout_minutes)

        doc = {
            "session_id": session_id,
            "user_id": user_id,
            "target_chat_id": target_chat_id,
            "owner_id": owner_id,
            "first_name": first_name,
            "last_name": last_name,
            "username": username,
            "status": "pending",  # pending | verified | approved | expired | failed
            "attempts": 0,
            "created_at": now,
            "expires_at": expires_at,
            "verified_at": None,
            "approved_at": None
        }

        # Expire any previous pending sessions for this user in this target chat
        await self.sessions.update_many(
            {"user_id": user_id, "target_chat_id": target_chat_id, "status": "pending"},
            {"$set": {"status": "expired"}}
        )

        await self.sessions.insert_one(doc)
        return doc

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve verification session by unique ID."""
        return await self.sessions.find_one({"session_id": session_id})

    async def get_active_session(self, user_id: int, target_chat_id: int) -> Optional[Dict[str, Any]]:
        """Find currently active pending session for user in target chat."""
        now = datetime.utcnow()
        return await self.sessions.find_one({
            "user_id": user_id,
            "target_chat_id": target_chat_id,
            "status": "pending",
            "expires_at": {"$gt": now}
        })

    async def increment_attempts(self, session_id: str) -> int:
        """Increment verification attempt counter."""
        res = await self.sessions.find_one_and_update(
            {"session_id": session_id},
            {"$inc": {"attempts": 1}},
            return_document=True
        )
        return res.get("attempts", 0) if res else 0

    async def mark_verified(self, session_id: str) -> bool:
        """Mark session as successfully verified."""
        res = await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "verified", "verified_at": datetime.utcnow()}}
        )
        return res.modified_count > 0

    async def mark_approved(self, session_id: str) -> bool:
        """Mark session as approved."""
        res = await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "approved", "approved_at": datetime.utcnow()}}
        )
        return res.modified_count > 0

    async def mark_failed(self, session_id: str, reason: str = "") -> bool:
        """Mark session as failed or exhausted."""
        res = await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "failed", "failure_reason": reason, "failed_at": datetime.utcnow()}}
        )
        return res.modified_count > 0

    async def mark_expired(self, session_id: str) -> bool:
        """Mark session as expired."""
        res = await self.sessions.update_one(
            {"session_id": session_id},
            {"$set": {"status": "expired"}}
        )
        return res.modified_count > 0

    async def log_event(
        self,
        user_id: int,
        target_chat_id: int,
        owner_id: int,
        action: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an audit trail log entry for verification lifecycle events."""
        log_doc = {
            "log_id": str(uuid.uuid4()),
            "user_id": user_id,
            "target_chat_id": target_chat_id,
            "owner_id": owner_id,
            "action": action,  # JOIN_REQUEST, VERIFY_ATTEMPT, VERIFIED, APPROVED, FAILED, EXPIRED
            "details": details or {},
            "timestamp": datetime.utcnow()
        }
        await self.logs.insert_one(log_doc)

    async def get_recent_logs(self, owner_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent verification events for owner dashboard."""
        cursor = self.logs.find({"owner_id": owner_id}).sort("timestamp", -1).limit(limit)
        return await cursor.to_list(length=limit)


verification_repo = VerificationRepository()
