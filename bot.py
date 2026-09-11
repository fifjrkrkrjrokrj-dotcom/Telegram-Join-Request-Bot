import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import asyncio
from pyrogram import Client, idle
from config import settings
from database.mongo import db
from utils.logger import logger
from utils.rate_limit import rate_limiter

def create_bot() -> Client:
    """Initialize and configure the Pyrogram Client with plugins."""
    return Client(
        name="join_verify_bot",
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        bot_token=settings.BOT_TOKEN,
        plugins=dict(root="handlers"),
        workdir="."
    )

async def periodic_cleanup():
    """Background task to periodically clean up expired memory entries."""
    while True:
        try:
            await asyncio.sleep(600)  # Every 10 minutes
            rate_limiter.cleanup(max_age_seconds=1800.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {e}")

async def main():
    """Main application lifecycle runner."""
    print("""
    ========================================================
       [+] TELEGRAM JOIN REQUEST VERIFICATION PLATFORM
    ========================================================
    """)
    logger.info("Initializing system...")

    # 1. Connect to MongoDB and verify indexes
    try:
        await db.connect()
    except Exception as e:
        logger.critical(f"Failed to connect to MongoDB: {e}")
        sys.exit(1)

    # 2. Initialize Telegram Bot Client
    app = create_bot()

    # 3. Start background cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup())

    try:
        # 4. Start Pyrogram Client
        await app.start()
        me = await app.get_me()
        logger.info(f"Bot started successfully as @{me.username} (ID: {me.id})")
        logger.info("Ready to process join requests and handle tenant management.")

        # 5. Keep running until terminated
        await idle()

    except Exception as e:
        logger.critical(f"Critical runtime exception: {e}")
    finally:
        logger.info("Initiating graceful shutdown...")
        cleanup_task.cancel()
        if app.is_connected:
            await app.stop()
        await db.close()
        logger.info("Shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot process exited.")
