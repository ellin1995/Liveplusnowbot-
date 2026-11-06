"""
=============================================================================
aliSTREAM Live TV Bot - Supabase + Web Redirect VLC Intent (Telegram Compatible)
=============================================================================
"""

import asyncio
import html
import logging
import os
import sys
import time
from typing import Any, Dict, List, Tuple

from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.filters import Command, CommandStart

BOT_TOKEN = "8792889859:AAFuY7i-UFR-WVLQrlj4hMPx8FQBy4UddnA"
PORT = int(os.getenv("PORT", "10000"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://ddywqmupodubrwlaflem.supabase.co").strip().rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "sb_publishable_r1wS_YGGkexuVtRvvBy40Q_Qm-i672h").strip()

PLAY_STORE_VLC_URL = "https://play.google.com/store/apps/details?id=org.videolan.vlc"
ITEMS_PER_PAGE = 8
CACHE_TTL_SECONDS = 120

class SupabaseChannelManager:
    def __init__(self, url: str, key: str):
        self.url = url
        self.key = key
        self.client = None
        self._cache: List[Dict[str, Any]] = []
        self._last_fetch_time: float = 0.0

        if self.url and self.key:
            try:
                from supabase import create_client
                self.client = create_client(self.url, self.key)
                logging.info("✅ تم الاتصال بقاعدة بيانات Supabase بنجاح.")
            except Exception as exc:
                logging.error("❌ فشل الاتصال بـ Supabase: %s", exc)

    def _sync_fetch(self) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        response = (
            self.client.table("channels")
            .select("id, name, stream_url")
            .order("id")
            .execute()
        )
        return response.data or []

    async def get_channels(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        now = time.time()
        if not force_refresh and self._cache and (now - self._last_fetch_time < CACHE_TTL_SECONDS):
            return self._cache

        if not self.client:
            return []

        try:
            data = await asyncio.to_thread(self._sync_fetch)
            if data:
                self._cache = data
                self._last_fetch_time = now
                return self._cache
        except Exception as exc:
            logging.error("❌ خطأ أثناء جلب القنوات من Supabase: %s", exc)
        return []

    def clear_cache(self) -> None:
        self._cache = []
        self._last_fetch_time = 0.0

channel_manager = SupabaseChannelManager(SUPABASE_URL, SUPABASE_KEY)

def build_channels_page_markup(channels: List[Dict[str, Any]], page: int = 0) -> Tuple[InlineKeyboardMarkup, int, int]:
    total_channels = len(channels)
    total_pages = max(1, (total_channels + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * ITEMS_PER_PAGE
    end_idx = min(start_idx + ITEMS_PER_PAGE, total_channels)
    
    keyboard: List[List[InlineKeyboardButton]] = []
    for idx in range(start_idx, end_idx):
        ch = channels[idx]
        ch_id = ch.get("id", idx)
        ch_name = ch.get("name", f"قناة #{idx + 1}")
        keyboard.append([
            InlineKeyboardButton(text=f"📺 {ch_name}", callback_data=f"ch:{ch_id}:{page}")
        ])
    
    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ➡️", callback_data=f"page:{page + 1}"))
    
    keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="🔄 تحديث القنوات", callback_data=f"refresh:{page}")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard), total_pages, total_channels

dp = Dispatcher()

async def show_menu(target: Message | CallbackQuery, page: int = 0, force_refresh: bool = False) -> None:
    channels = await channel_manager.get_channels(force_refresh=force_refresh)
    if not channels:
        text = "⚠️ عذراً، لا توجد قنوات متاحة حالياً في قاعدة البيانات."
        markup = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔄 إعادة المحاولة", callback_data="refresh:0")]])
    else:
        markup, total_pages, total_channels = build_channels_page_markup(channels, page=page)
        text = (
            f"<b>⚡ أهلاً بك في بوت البث المباشر</b>\n\n"
            f"📡 <b>إجمالي القنوات المتاحة:</b> <code>{total_channels}</code> قناة\n"
            f"📄 <b>الصفحة:</b> <code>{page + 1} / {total_pages}</code>\n\n"
            f"👇 اختر القناة المطلوبة للتشغيل الفوري:"
        )

    if isinstance(target, Message):
        await target.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    elif isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=markup, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        await target.answer()

@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await show_menu(message, page=0)

@dp.callback_query(F.data.startswith("page:"))
async def pagination_handler(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[1])
    await show_menu(callback, page=page)

@dp.callback_query(F.data.startswith("refresh:"))
async def refresh_handler(callback: CallbackQuery) -> None:
    page = int(callback.data.split(":")[1])
    channel_manager.clear_cache()
    await callback.answer("🔄 يتم تحديث القنوات...")
    await show_menu(callback, page=page, force_refresh=True)

@dp.callback_query(F.data.startswith("ch:"))
async def channel_selection_handler(callback: CallbackQuery) -> None:
    try:
        parts = callback.data.split(":")
        target_id = str(parts[1])
        return_page = int(parts[2]) if len(parts) > 2 else 0
        
        channels = await channel_manager.get_channels()
        matched_channel = next((ch for ch in channels if str(ch.get("id")) == target_id), None)
        
        if not matched_channel:
            await callback.answer("⚠️ لم يتم العثور على القناة", show_alert=True)
            return

        stream_url = matched_channel.get("stream_url", "")
        
        # ترميز رابط البث ليكون آمناً في الـ URL
        import urllib.parse
        encoded_url = urllib.parse.quote(stream_url, safe="")
        
        # استخدام رابط الويب العام على Render (يقبله تيليجرام 100%)
        web_redirect_url = f"https://liveplusnowbot.onrender.com/play?url={encoded_url}"
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎬 تشغيل مباشر في مشغل VLC", url=web_redirect_url)],
            [InlineKeyboardButton(text="📲 تحميل تطبيق VLC من Google Play", url=PLAY_STORE_VLC_URL)],
            [InlineKeyboardButton(text="🔙 العودة لقائمة القنوات", callback_data=f"page:{return_page}")]
        ])

        detail_text = (
            f"<b>📺 القناة:</b> <code>{html.escape(matched_channel.get('name', ''))}</code>\n\n"
            f"▶️ اضغط على زر <b>'تشغيل مباشر في مشغل VLC'</b> بالأعلى لفتح البث فوراً على هاتفك!"
        )

        await callback.message.edit_text(
            text=detail_text,
            reply_markup=markup,
            parse_mode=ParseMode.HTML
        )
        await callback.answer()
    except Exception as exc:
        logging.error("Error: %s", exc)
        await callback.answer("⚠️ حدث خطأ", show_alert=True)

@dp.callback_query(F.data == "noop")
async def noop_handler(callback: CallbackQuery) -> None:
    await callback.answer()

async def health_check(request: web.Request) -> web.Response:
    return web.Response(text="Bot is running live!", content_type="text/plain")

async def play_redirect_handler(request: web.Request) -> web.Response:
    stream_url = request.query.get("url", "")
    if not stream_url:
        return web.Response(text="Stream URL not provided.", status=400)
    
    html_content = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تشغيل البث المباشر - aliSTREAM</title>
    <style>
        body {{ font-family: Tahoma, sans-serif; background: #121212; color: #fff; text-align: center; padding-top: 50px; }}
        .btn {{ background: #ff5722; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-size: 18px; display: inline-block; margin-top: 20px; }}
        .playstore {{ background: #2196F3; }}
    </style>
    <script>
        window.onload = function() {{
            var streamUrl = "{stream_url}";
            var fallbackUrl = "{PLAY_STORE_VLC_URL}";
            var intentUrl = "intent:" + streamUrl + "#Intent;action=android.intent.action.VIEW;type=video/*;package=org.videolan.vlc;S.browser_fallback_url=" + encodeURIComponent(fallbackUrl) + ";end;";
            window.location.href = intentUrl;
        }};
    </script>
</head>
<body>
    <h2>⚡ جاري فتح البث في مشغل VLC...</h2>
    <p>إذا لم يفتح المشغل تلقائياً، اضغط على الزر أدناه:</p>
    <br>
    <a id="vlcLink" href="#" class="btn">🎬 اضغط هنا للتشغيل الفوري</a>
    <br><br>
    <a href="{PLAY_STORE_VLC_URL}" class="btn playstore">📲 تحميل مشغل VLC من Google Play</a>

    <script>
        var streamUrl = "{stream_url}";
        var fallbackUrl = "{PLAY_STORE_VLC_URL}";
        var intentUrl = "intent:" + streamUrl + "#Intent;action=android.intent.action.VIEW;type=video/*;package=org.videolan.vlc;S.browser_fallback_url=" + encodeURIComponent(fallbackUrl) + ";end;";
        document.getElementById("vlcLink").href = intentUrl;
    </script>
</body>
</html>
"""
    return web.Response(text=html_content, content_type="text/html", charset="utf-8")

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_get("/play", play_redirect_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
