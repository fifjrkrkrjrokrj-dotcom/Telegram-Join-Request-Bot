from typing import Dict, Any
from utils.helpers import format_card, escape_html
from database.statistics import statistics_repo

class StatisticsService:
    """Formats and visualizes statistical telemetry for bot dashboards."""

    async def get_formatted_owner_dashboard_stats(self, owner_id: int) -> str:
        """Render owner's global summary stats."""
        total = await statistics_repo.get_owner_total_stats(owner_id)
        today = await statistics_repo.get_owner_today_stats(owner_id)

        content = (
            f"📅 <b>TODAY'S ACTIVITY</b>\n"
            f"📥 Join Requests: <code>{today.get('requests', 0)}</code>\n"
            f"✅ Verified Users: <code>{today.get('verified', 0)}</code>\n"
            f"👥 Approved Users: <code>{today.get('approved', 0)}</code>\n"
            f"❌ Failed / Incomplete: <code>{today.get('failed', 0)}</code>\n\n"
            f"📈 <b>ALL-TIME TOTALS</b>\n"
            f"📥 Total Requests: <code>{total.get('total_requests', 0)}</code>\n"
            f"✅ Total Verified: <code>{total.get('verified', 0)}</code>\n"
            f"👥 Total Approved: <code>{total.get('approved', 0)}</code>\n"
            f"🎯 Success Rate: <code>{total.get('success_rate', 0.0)}%</code>"
        )
        return format_card("📊 PERFORMANCE METRICS", content)

    async def get_formatted_chat_stats(self, chat: Dict[str, Any]) -> str:
        """Render metrics for a specific target chat."""
        chat_id = chat["chat_id"]
        title = escape_html(chat.get("title", "Chat"))
        stats = await statistics_repo.get_chat_stats(chat_id)

        content = (
            f"💬 <b>Chat:</b> {title}\n"
            f"🆔 <b>ID:</b> <code>{chat_id}</code>\n\n"
            f"📅 <b>TODAY</b>\n"
            f"📥 Requests: <code>{stats['today_requests']}</code>\n"
            f"✅ Verified: <code>{stats['today_verified']}</code>\n"
            f"👥 Approved: <code>{stats['today_approved']}</code>\n"
            f"❌ Incomplete: <code>{stats['today_failed']}</code>\n\n"
            f"📈 <b>LIFETIME STATS</b>\n"
            f"📥 Total Requests: <code>{stats['total_requests']}</code>\n"
            f"✅ Total Verified: <code>{stats['verified']}</code>\n"
            f"👥 Total Approved: <code>{stats['approved']}</code>\n"
            f"🎯 Conversion Rate: <code>{stats['success_rate']}%</code>"
        )
        return format_card("📊 CHAT ANALYTICS", content)


statistics_service = StatisticsService()
