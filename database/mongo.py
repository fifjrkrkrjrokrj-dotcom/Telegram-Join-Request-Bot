import motor.motor_asyncio
from config import settings
from utils.logger import logger

class MongoDB:
    """Async MongoDB client wrapper with index initialization."""

    def __init__(self):
        self.client: motor.motor_asyncio.AsyncIOMotorClient = None
        self.db: motor.motor_asyncio.AsyncIOMotorDatabase = None

    async def connect(self) -> None:
        """Establish connection to MongoDB and ensure indexes exist."""
        logger.info(f"Connecting to MongoDB at {settings.MONGO_URI}...")
        self.client = motor.motor_asyncio.AsyncIOMotorClient(settings.MONGO_URI)
        self.db = self.client[settings.DATABASE_NAME]

        # Ensure indexes
        await self._init_indexes()
        logger.info("MongoDB connection established and indexes verified.")

    async def _init_indexes(self) -> None:
        """Create necessary indexes for high performance and integrity."""
        # 1. Users collection
        await self.db.users.create_index("user_id", unique=True)
        await self.db.users.create_index("created_at")

        # 2. Chats collection
        await self.db.chats.create_index("chat_id", unique=True)
        await self.db.chats.create_index("owner_id")
        await self.db.chats.create_index([("owner_id", 1), ("enabled", 1)])

        # 3. Required Chats collection
        await self.db.required_chats.create_index([("target_chat_id", 1), ("req_chat_id", 1)], unique=True)
        await self.db.required_chats.create_index([("target_chat_id", 1), ("order", 1)])
        await self.db.required_chats.create_index("owner_id")

        # 4. Verification Sessions collection
        await self.db.verification_sessions.create_index("session_id", unique=True)
        await self.db.verification_sessions.create_index([("user_id", 1), ("target_chat_id", 1)])
        await self.db.verification_sessions.create_index("expires_at")
        await self.db.verification_sessions.create_index("status")

        # 5. Verification Logs collection
        await self.db.verification_logs.create_index([("target_chat_id", 1), ("timestamp", -1)])
        await self.db.verification_logs.create_index([("owner_id", 1), ("timestamp", -1)])
        await self.db.verification_logs.create_index("user_id")

        # 6. Daily Statistics collection
        await self.db.daily_stats.create_index([("chat_id", 1), ("date", 1)], unique=True)
        await self.db.daily_stats.create_index([("owner_id", 1), ("date", 1)])

    async def close(self) -> None:
        """Gracefully close MongoDB client."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed.")


# Singleton MongoDB instance
db = MongoDB()
