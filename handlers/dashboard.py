from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from database.users import user_repo
from database.chats import chat_repo
from database.statistics import statistics_repo
from keyboards.main import get_main_dashboard_keyboard, get_back_to_dashboard_keyboard
from keyboards.chats import get_chats_list_keyboard
from services.statistics import statistics_service
from utils.helpers import format_card, escape_html
from utils.states import state_manager
from utils.rate_limit import rate_limiter
from config import settings

@Client.on_callback_query(filters.regex(r"^menu:dashboard$"))
async def cb_main_dashboard(client: Client, callback_query: CallbackQuery):
    """Render main dashboard view."""
    user = callback_query.from_user
    state_manager.clear_state(user.id)

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
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_main_dashboard_keyboard()
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^menu:my_chats(?::(\d+))?$"))
async def cb_my_chats(client: Client, callback_query: CallbackQuery):
    """List connected target chats with pagination."""
    user = callback_query.from_user
    state_manager.clear_state(user.id)

    # Extract page
    match = callback_query.matches[0]
    page = int(match.group(1)) if match.group(1) else 1

    chats = await chat_repo.get_owner_chats(user.id, limit=50)

    if not chats:
        content = (
            "📂 <b>No Connected Chats Yet!</b>\n\n"
            "You haven't connected any Telegram groups or channels.\n"
            "Click the button below to add your first chat."
        )
        text = format_card("📂 MY CHATS", content)
        await callback_query.message.edit_text(
            text=text,
            reply_markup=get_chats_list_keyboard([], page=1)
        )
        await callback_query.answer()
        return

    content = (
        f"📂 <b>Your Connected Chats ({len(chats)}):</b>\n\n"
        "Select a chat below to configure settings, required channels, welcome messages, and view analytics."
    )
    text = format_card("📂 MY CHATS", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_chats_list_keyboard(chats, page=page)
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^menu:stats$"))
async def cb_global_stats(client: Client, callback_query: CallbackQuery):
    """Show global statistics across all chats for the owner."""
    user = callback_query.from_user
    stats_text = await statistics_service.get_formatted_owner_dashboard_stats(user.id)
    await callback_query.message.edit_text(
        text=stats_text,
        reply_markup=get_back_to_dashboard_keyboard()
    )
    await callback_query.answer()


@Client.on_callback_query(filters.regex(r"^menu:help$"))
async def cb_help_menu(client: Client, callback_query: CallbackQuery):
    """Show detailed onboarding instructions."""
    content = (
        "💡 <b>HOW TO CONNECT & AUTOMATE</b>\n\n"
        "1️⃣ <b>Add Bot as Admin:</b>\n"
        "• Add this bot to your target Channel or Supergroup as an Administrator.\n"
        "• Grant <b>Invite Users via Link</b> permission.\n\n"
        "2️⃣ <b>Register Chat:</b>\n"
        "• Tap <b>➕ Add Group / Channel</b> and send its username or invite link.\n\n"
        "3️⃣ <b>Set Verification Requirements:</b>\n"
        "• Add sponsor/backup channels in <b>🔗 Required Chats</b>.\n"
        "• (Make sure this bot is also admin in private required channels to check members).\n\n"
        "4️⃣ <b>Customization:</b>\n"
        "• Set custom welcome text with <code>{first_name}</code>, <code>{chat_title}</code> variables.\n"
        "• Toggle Auto-Approve 🟢 ON or 🔴 OFF.\n\n"
        "⚡ <i>All join requests will now be verified automatically in private DM!</i>"
    )
    text = format_card("📖 HELP & GUIDE", content)
    await callback_query.message.edit_text(
        text=text,
        reply_markup=get_back_to_dashboard_keyboard()
    )
    await callback_query.answer()
