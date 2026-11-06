"""
=============================================================================
liveplusnowbot Bot - Modern Telegram Streaming Bot
Framework: aiogram v3 (Asynchronous Telegram Bot Framework)
Database: Supabase Cloud Database + Built-in Full Channels Fallback
Player: Direct Android VLC Intent Launcher with Google Play Store Fallback
Watermark: #Alistreamlivebot
Platform: Render.com / Koyeb / VPS / Local / Android Termux
=============================================================================
"""

import asyncio
import html
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

from aiohttp import web
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramConflictError,
    TelegramNetworkError,
    TelegramUnauthorizedError,
)
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# 1. CONFIGURATION & CREDENTIALS
# ---------------------------------------------------------------------------
DEFAULT_BOT_TOKEN = "8792889859:AAFuY7i-UFR-WVLQrlj4hMPx8FQBy4UddnA"
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip() or DEFAULT_BOT_TOKEN

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://ddywqmupodubrwlaflem.supabase.co").strip().rstrip("/")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "sb_publishable_r1wS_YGGkexuVtRvvBy40Q_Qm-i672h").strip()

PORT: int = int(os.getenv("PORT", "10000"))

WATERMARK: str = "#Alistreamlivebot"
BOT_BRAND: str = "⚡ aliSTREAM Live TV"
PLAY_STORE_VLC_URL: str = "https://play.google.com/store/apps/details?id=org.videolan.vlc"
ITEMS_PER_PAGE: int = 8
CACHE_TTL_SECONDS: int = 120

REQUIRED_CHANNEL_USERNAME: str = "@alifootball95"
REQUIRED_CHANNEL_URL: str = "https://t.me/alifootball95"

DEFAULT_CHANNELS_MAP: Dict[str, str] = {
    "FR | BEIN SPORTS 1 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14160.ts",
    "FR | BEIN SPORTS 1 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14170.ts",
    "AR | BEIN SPORTS 1 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13608.ts",
    "AR | BEIN SPORTS 2 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13607.ts",
    "AR | BEIN SPORTS 3 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13606.ts",
}

DEFAULT_FALLBACK_CHANNELS: List[Dict[str, Any]] = [
    {"id": i + 1, "name": name, "stream_url": url}
    for i, (name, url) in enumerate(DEFAULT_CHANNELS_MAP.items())
]

# ---------------------------------------------------------------------------
# 2. SUPABASE CHANNELS MANAGER
# ---------------------------------------------------------------------------
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
                logging.info("✅ تم تهيئة عميل Supabase بنجاح.")
            except Exception as exc:
                logging.error("❌ فشل الاتصال بـ Supabase: %s", exc)

    def is_configured(self) -> bool:
        return self.client is not None

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

        if not self.is_configured():
            return DEFAULT_FALLBACK_CHANNELS

        try:
            data = await asyncio.to_thread(self._sync_fetch)
            if data and len(data) > 0:
                self._cache = data
                self._last_fetch_time = now
                logging.info("📡 تم جلب %d قناة من Supabase بنجاح.", len(data))
                return self._cache
            else:
                return DEFAULT_FALLBACK_CHANNELS
        except Exception as exc:
            logging.error("❌ خطأ أثناء استعلام Supabase: %s", exc)
            return DEFAULT_FALLBACK_CHANNELS

    def clear_cache(self) -> None:
        self._cache = []
        self._last_fetch_time = 0.0

channel_manager = SupabaseChannelManager(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# 3. MEMBERSHIP & VLC INTENT
# ---------------------------------------------------------------------------
async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception as exc:
        logging.warning("⚠️ تعذر التحقق من اشتراك المستخدم %s: %s", user_id, exc)
        return True

def get_subscription_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشتراك في القناة الرسمية", url=REQUIRED_CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ لقد اشتركت، تحقق الآن", callback_data="check_sub")]
        ]
    )

def build_vlc_intent_url(stream_url: str) -> str:
    fallback_encoded = "https%3A%2F%2Fplay.google.com%2Fstore%2Fapps%2Fdetails%3Fid%3Dorg.videolan.vlc"
    return (
        f"intent:{stream_url}#Intent;"
        f"action=android.intent.action.VIEW;"
        f"type=video/*;"
        f"package=org.videolan.vlc;"
        f"S.browser_fallback_url={fallback_encoded};"
        f"end"
    )

# ---------------------------------------------------------------------------
# 4. KEYBOARD BUILDERS
# ---------------------------------------------------------------------------
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
            InlineKeyboardButton(
                text=f"📺 {ch_name}",
                callback_data=f"ch:{ch_id}:{page}",
            )
        ])
    
    nav_row: List[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ السابق", callback_data=f"page:{page - 1}"))
    nav_row.append(InlineKeyboardButton(text=f"📄 {page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="التالي ➡️", callback_data=f"page:{page + 1}"))
    
    keyboard.append(nav_row)
    keyboard.append([
        InlineKeyboardButton(text="🔄 تحديث القنوات", callback_data=f"refresh:{page}"),
        InlineKeyboardButton(text="ℹ️ تعليمات التشغيل", callback_data="help_info"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard), total_pages, total_channels

def build_channel_playback_markup(ch_id: Any, stream_url: str, return_page: int) -> InlineKeyboardMarkup:
    vlc_intent = build_vlc_intent_url(stream_url)
    keyboard: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🎬 تشغيل مباشر في مشغل VLC", url=vlc_intent)],
        [InlineKeyboardButton(text="📲 تثبيت تطبيق VLC (Google Play)", url=PLAY_STORE_VLC_URL)],
        [InlineKeyboardButton(text="🔙 العودة لقائمة القنوات", callback_data=f"page:{return_page}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ---------------------------------------------------------------------------
# 5. UI TEXT TEMPLATES
# ---------------------------------------------------------------------------
def get_welcome_text(total_channels: int, page: int, total_pages: int) -> str:
    return (
        f"<b>{BOT_BRAND}</b>\n"
        f"<i>البث المباشر الفوري للقنوات بجودة فائقة</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 <b>إجمالي القنوات المتاحة:</b> <code>{total_channels}</code> قناة\n"
        f"📄 <b>الصفحة الحالية:</b> <code>{page + 1} / {total_pages}</code>\n"
        f"⚡ <b>المشغل المدعوم:</b> مشغل <b>VLC Player</b> (تشغيل فوري)\n\n"
        f"👇 <i>اختر القناة المطلوبة من القائمة أدناه للمشاهدة:</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ <code>{WATERMARK}</code>"
    )

def get_channel_detail_text(channel: Dict[str, Any]) -> str:
    ch_name = html.escape(channel.get("name", "قناة غير معروفة"))
    stream_url = channel.get("stream_url", "").strip()
    safe_stream = html.escape(stream_url)
    return (
        f"<b>{BOT_BRAND}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📺 <b>القناة المختارة:</b> <code>{ch_name}</code>\n"
        f"🟢 <b>الحالة:</b> بث حي ومباشر (LIVE)\n"
        f"🎬 <b>طريقة التشغيل:</b> إطلاق فوري عبر مشغل <b>VLC Player</b>\n\n"
        f"🚀 <b>طريقة المشاهدة بنقرة واحدة:</b>\n"
        f"اضغط على زر <b>'🎬 تشغيل مباشر في مشغل VLC'</b> بالأسفل ليفتح البث فوراً داخل تطبيق VLC على هاتفك.\n\n"
        f"🔗 <b>رابط البث المباشر (نسخ يدوي):</b>\n"
        f"<code>{safe_stream}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ <code>{WATERMARK}</code>"
    )

# ---------------------------------------------------------------------------
# 6. DISPATCHER & HANDLERS
# ---------------------------------------------------------------------------
dp = Dispatcher()

async def render_channels_menu(target: Message | CallbackQuery, page: int = 0, force_refresh: bool = False) -> None:
    bot_obj = target.bot if isinstance(target, CallbackQuery) else target.bot
    user_id = target.from_user.id

    is_subscribed = await check_user_subscription(bot_obj, user_id)
    if not is_subscribed:
        sub_text = (
            f"🚨 <b>عذراً، يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه!</b>\n\n"
            f"📢 قناة البوت الرسمية: <a href='{REQUIRED_CHANNEL_URL}'>@alifootball95</a>\n\n"
            f"👇 اشترك في القناة ثم اضغط على زر <b>'تحقق الآن'</b> بالأسفل:"
        )
        if isinstance(target, Message):
            await target.answer(text=sub_text, reply_markup=get_subscription_markup(), disable_web_page_preview=True)
        elif isinstance(target, CallbackQuery):
            await target.message.edit_text(text=sub_text, reply_markup=get_subscription_markup(), disable_web_page_preview=True)
            await target.answer("⚠️ يرجى الاشتراك في القناة أولاً!", show_alert=True)
        return

    channels = await channel_manager.get_channels(force_refresh=force_refresh)
    markup, total_pages, total_channels = build_channels_page_markup(channels, page=page)
    text = get_welcome_text(total_channels, page, total_pages)

    if isinstance(target, Message):
        await target.answer(text=text, reply_markup=markup, disable_web_page_preview=True)
    elif isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text=text, reply_markup=markup, disable_web_page_preview=True)
        except TelegramBadRequest as exc:
            if "message is not modified" not in str(exc).lower():
                logging.error("Telegram edit error: %s", exc)
        await target.answer()

@dp.message(CommandStart())
async def cmd_start_handler(message: Message) -> None:
    await render_channels_menu(message, page=0)

@dp.callback_query(F.data == "check_sub")
async def check_subscription_callback(callback: CallbackQuery) -> None:
    bot_obj = callback.bot
    user_id = callback.from_user.id
    is_subscribed = await check_user_subscription(bot_obj, user_id)
    if is_subscribed:
        await callback.answer("✅ شكراً لك! تم التحقق من اشتراكك بنجاح.", show_alert=True)
        await render_channels_menu(callback, page=0)
    else:
        await callback.answer("❌ لم تقم بالاشتراك في القناة بعد! يرجى الاشتراك أولاً.", show_alert=True)

@dp.callback_query(F.data.startswith("page:"))
async def pagination_callback_handler(callback: CallbackQuery) -> None:
    try:
        page = int(callback.data.split(":")[1])
        await render_channels_menu(callback, page=page)
    except Exception as exc:
        logging.error("Pagination callback error: %s", exc)
        await callback.answer("⚠️ تعذر تحميل الصفحة")

@dp.callback_query(F.data.startswith("refresh:"))
async def refresh_callback_handler(callback: CallbackQuery) -> None:
    try:
        page = int(callback.data.split(":")[1])
        channel_manager.clear_cache()
        await callback.answer("🔄 تم تحديث قائمة القنوات!")
        await render_channels_menu(callback, page=page, force_refresh=True)
    except Exception as exc:
        logging.error("Refresh callback error: %s", exc)
        await callback.answer("⚠️ حدث خطأ أثناء التحديث")

@dp.callback_query(F.data.startswith("ch:"))
async def channel_selection_handler(callback: CallbackQuery) -> None:
    try:
        parts = callback.data.split(":")
        target_id = str(parts[1])
        return_page = int(parts[2]) if len(parts) > 2 else 0
        
        channels = await channel_manager.get_channels()
        matched_channel = None
        for ch in channels:
            if str(ch.get("id")) == target_id:
                matched_channel = ch
                break
        
        if matched_channel:
            detail_text = get_channel_detail_text(matched_channel)
            markup = build_channel_playback_markup(target_id, matched_channel.get("stream_url", ""), return_page)
            await callback.message.edit_text(
                text=detail_text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            await callback.answer()
        else:
            await callback.answer("⚠️ لم يتم العثور على القناة، يرجى تحديث القائمة.")
    except Exception as exc:
        logging.error("Channel selection error: %s", exc)
        await callback.answer("⚠️ تعذر عرض تفاصيل القناة")

@dp.callback_query(F.data == "help_info")
async def help_callback_handler(callback: CallbackQuery) -> None:
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 العودة لقائمة القنوات", callback_data="page:0")]]
    )
    try:
        await callback.message.edit_text(
            text="<b>⚡ دليل الاستخدام:</b>\nاختر أي قناة واضغط على زر التشغيل لتفتح مباشرة في تطبيق VLC.",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
        await callback.answer()
    except Exception as exc:
        await callback.answer()

# ---------------------------------------------------------------------------
# 7. HEALTH CHECK SERVER FOR RENDER
# ---------------------------------------------------------------------------
async def health_check_handler(request: web.Request) -> web.Response:
    return web.Response(text="Bot is running live!", content_type="text/plain")

async def start_health_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    return runner

async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    http_runner = await start_health_server(PORT)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=False)
            await dp.start_polling(bot)
            break
        except Exception as exc:
            logging.error("Polling error: %s", exc)
            await asyncio.sleep(10)

    if http_runner:
        await http_runner.cleanup()
    await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
