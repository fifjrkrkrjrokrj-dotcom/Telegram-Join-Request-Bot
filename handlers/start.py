from pyrogram import Client, filters
from pyrogram.types import Message
from database.users import user_repo
from database.chats import chat_repo
from database.statistics import statistics_repo
from keyboards.main import get_main_dashboard_keyboard
from utils.helpers import format_card, escape_html
from utils.states import state_manager
from utils.logger import logger

@Client.on_message(filters.command("start") & filters.private)
async def handle_start(client: Client, message: Message):
    """Handle /start command, register user and present main dashboard."""
    user = message.from_user
    if not user:
        return

    # Check ban status
    if await user_repo.is_banned(user.id):
        await message.reply_text("⛔ You are restricted from using this service.")
        return

    # Clear active FSM state
    state_manager.clear_state(user.id)

    # Upsert user record
    await user_repo.upsert_user(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        username=user.username
    )

    # Fetch dashboard metrics
    total_chats = await chat_repo.count_owner_chats(user.id)
    active_chats = await chat_repo.count_active_owner_chats(user.id)
    today_stats = await statistics_repo.get_owner_today_stats(user.id)

    content = (
        f"👋 Welcome, <b>{escape_html(user.first_name)}</b>!\n\n"
        f"Manage your Telegram groups, channels, and automated join verification flows.\n\n"
        f"📂 <b>Connected Chats:</b> <code>{total_chats}</code>\n"
        f"🟢 <b>Active:</b> <code>{active_chats}</code>\n"
        f"📥 <b>Requests Today:</b> <code>{today_stats.get('requests', 0)}</code>\n"
        f"✅ <b>Verified Today:</b> <code>{today_stats.get('verified', 0)}</code>"
    )

    text = format_card("✦ JOIN VERIFY ✦", content)
    await message.reply_text(
        text=text,
        reply_markup=get_main_dashboard_keyboard()
    )


@Client.on_message(filters.command("help") & filters.private)
async def handle_help_command(client: Client, message: Message):
    """Provide quick help information via /help command."""
    content = (
        "💡 <b>HOW TO USE THIS BOT</b>\n\n"
        "1️⃣ <b>Add Bot to your Group/Channel:</b>\n"
        "• Add this bot as an <b>Administrator</b> with invite/membership privileges.\n\n"
        "2️⃣ <b>Connect your Chat:</b>\n"
        "• Click <b>➕ Add Group / Channel</b> on the dashboard and send the username or link.\n\n"
        "3️⃣ <b>Configure Requirements:</b>\n"
        "• Go to <b>📂 My Chats</b> ➜ Select your chat ➜ <b>🔗 Required Chats</b>.\n"
        "• Add mandatory channels/groups that applicants must join.\n\n"
        "4️⃣ <b>Automated Verification:</b>\n"
        "• When users request to join, the bot instantly sends a verification DM.\n"
        "• Once they join the required chats and tap Verify, they get auto-approved! 🎉"
    )
    text = format_card("📖 HELP & GUIDE", content)
    await message.reply_text(text=text, reply_markup=get_main_dashboard_keyboard())
