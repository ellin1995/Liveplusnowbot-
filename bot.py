"""
=============================================================================
aliSTREAM Live TV Bot - Supabase Integration + Safe Player Launcher
Framework: aiogram v3
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
            f"👇 اختر القناة المطلوبة:"
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
        safe_url = html.escape(stream_url)
        
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📲 تحميل مشغل VLC من Google Play", url=PLAY_STORE_VLC_URL)],
            [InlineKeyboardButton(text="🔙 العودة لقائمة القنوات", callback_data=f"page:{return_page}")]
        ])

        detail_text = (
            f"<b>📺 القناة:</b> <code>{html.escape(matched_channel.get('name', ''))}</code>\n\n"
            f"🔗 <b>رابط البث المباشر (انسخه وافتحه في أي مشغل مثل VLC):</b>\n"
            f"<code>{safe_url}</code>\n\n"
            f"💡 <i>قم بنسخ الرابط أعلاه وضعه مباشرة في تطبيق VLC على هاتفك للاستمتاع بالمشاهدة بدون تقطيع!</i>"
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
    return web.Response(text="Bot is running!", content_type="text/plain")

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    app.router.add_get("/", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    bot = Bot(token=BOT_TOKEN)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
