import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from config import settings
from database.users import user_repo
from utils.logger import logger
from pyrogram.errors import FloodWait

@Client.on_message(filters.command("broadcast") & filters.private)
async def handle_broadcast(client: Client, message: Message):
    """Handle /broadcast command for super admins."""
    if message.from_user.id not in settings.admin_id_list:
        await message.reply_text("⛔ You are not authorized to use this command.")
        return

    if not message.reply_to_message:
        await message.reply_text("⚠️ Please reply to a message you want to broadcast.")
        return

    broadcast_msg = message.reply_to_message
    
    status_msg = await message.reply_text("🚀 <b>Broadcast started!</b>\n\nCalculating total users...")
    
    total_users = await user_repo.get_total_users_count()
    await status_msg.edit_text(f"🚀 <b>Broadcasting to {total_users} users...</b>")
    
    success_count = 0
    fail_count = 0
    
    async for user_data in user_repo.get_all_users():
        user_id = user_data.get("user_id")
        if not user_id:
            continue
            
        try:
            await broadcast_msg.copy(chat_id=user_id)
            success_count += 1
            await asyncio.sleep(0.05) # Prevent flood waits
        except FloodWait as e:
            await asyncio.sleep(e.value + 1)
            try:
                await broadcast_msg.copy(chat_id=user_id)
                success_count += 1
            except Exception:
                fail_count += 1
        except Exception as e:
            logger.debug(f"Failed to broadcast to {user_id}: {e}")
            fail_count += 1
            
    await status_msg.edit_text(
        f"✅ <b>Broadcast Completed!</b>\n\n"
        f"🎯 <b>Total Targets:</b> <code>{total_users}</code>\n"
        f"✅ <b>Success:</b> <code>{success_count}</code>\n"
        f"❌ <b>Failed:</b> <code>{fail_count}</code>"
    )
