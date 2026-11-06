"""
=============================================================================
live plus Now Bot - Modern Telegram Streaming Bot
Framework: aiogram v3 (Asynchronous Telegram Bot Framework)
Database: Supabase Cloud Database + Built-in Full 50+ Channels Fallback
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

# Load environment variables from .env if present
load_dotenv()

# Ensure utf-8 encoding for standard output and logging
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
# 1. CONFIGURATION & CREDENTIALS (AUTOMATIC FALLBACKS FOR RENDER)
# ---------------------------------------------------------------------------
DEFAULT_BOT_TOKEN = "8792889859:AAFuY7i-UFR-WVLQrlj4hMPx8FQBy4UddnA"
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip() or DEFAULT_BOT_TOKEN

SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://ddywqmupodubrwlaflem.supabase.co").strip().rstrip("/")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "sb_publishable_r1wS_YGGkexuVtRvvBy40Q_Qm-i672h").strip()

# Port for Render.com / Cloud Web Services (Render sets PORT=10000 by default)
PORT: int = int(os.getenv("PORT", "10000"))

# Constants & Force Subscription Channel
WATERMARK: str = "#Alistreamlivebot"
BOT_BRAND: str = "⚡ aliSTREAM Live TV"
PLAY_STORE_VLC_URL: str = "https://play.google.com/store/apps/details?id=org.videolan.vlc"
ITEMS_PER_PAGE: int = 8
CACHE_TTL_SECONDS: int = 120  # In-memory cache TTL for channels

# إعدادات قناة الاشتراك الإجباري المطلوبة
REQUIRED_CHANNEL_USERNAME: str = "@alifootball95"
REQUIRED_CHANNEL_URL: str = "https://t.me/alifootball95"

# ---------------------------------------------------------------------------
# COMPLETE 50+ CHANNELS DATA (AUTOMATICALLY ACTIVE IF SUPABASE IS EMPTY)
# ---------------------------------------------------------------------------
DEFAULT_CHANNELS_MAP: Dict[str, str] = {
    "FR | BEIN SPORTS 1 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14160.ts",
    "FR | BEIN SPORTS 1 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14170.ts",
    "FR | BEIN SPORTS 1 SD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/92.ts",
    "FR | BEIN SPORTS 2 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14153.ts",
    "FR | BEIN SPORTS 2 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14169.ts",
    "FR | BEIN SPORTS 2 SD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/93.ts",
    "FR | BEIN SPORTS 3 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14152.ts",
    "FR | BEIN SPORTS 3 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/14163.ts",
    "FR | BEIN SPORTS 3 SD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/94.ts",
    "FR | BEIN SPORTS MAX 4 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/151958.ts",
    "FR | BEIN SPORTS MAX 4 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/95.ts",
    "FR | BEIN SPORTS MAX 5 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/151961.ts",
    "FR | BEIN SPORTS MAX 5 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/39882.ts",
    "FR | BEIN SPORTS MAX 6 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/151964.ts",
    "FR | BEIN SPORTS MAX 6 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/1089.ts",
    "FR | BEIN SPORTS MAX 7 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/151967.ts",
    "FR | BEIN SPORTS MAX 7 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/1113.ts",
    "FR | BEIN SPORTS MAX 8 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/151970.ts",
    "FR | BEIN SPORTS MAX 8 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/1468.ts",
    "FR | BEIN SPORTS MAX 9 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/151973.ts",
    "FR | BEIN SPORTS MAX 9 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/1469.ts",
    "FR | BEIN SPORTS MAX 10 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/151976.ts",
    "FR | BEIN SPORTS MAX 10 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/1470.ts",
    "FR | BEIN SPORTS 1 |HEVC|": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/47499.ts",
    "FR | BEIN SPORTS 2 |HEVC|": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/47500.ts",
    "C+ RÉU| BEIN SPORTS 1 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/359681.ts",
    "C+ RÉU| BEIN SPORTS 2 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/359680.ts",
    "C+ RÉU| BEIN SPORTS 3 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/359679.ts",
    "C+ RÉU| BEIN SPORTS MAX 4": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/359678.ts",
    "C+ RÉU| BEIN SPORTS MAX 5": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/359677.ts",
    "AR | BEIN SPORTS ARABIC": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/24983.ts",
    "AR | BEIN SPORTS NEWS FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/24979.ts",
    "AR | BEIN SPORTS NEWS HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/78372.ts",
    "AR | BEIN SPORTS GLOBAL FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/24980.ts",
    "AR | BEIN SPORTS GLOBAL HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/409586.ts",
    "AR | BEIN SPORTS 4K": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/164973.ts",
    "AR | BEIN SPORTS 1 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13608.ts",
    "AR | BEIN SPORTS 1 FHD BKP": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/368730.ts",
    "AR | BEIN SPORTS 1 HD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13682.ts",
    "AR | BEIN SPORTS 2 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13607.ts",
    "AR | BEIN SPORTS 3 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13606.ts",
    "AR | BEIN SPORTS 4 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13605.ts",
    "AR | BEIN SPORTS 5 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13604.ts",
    "AR | BEIN SPORTS 6 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13603.ts",
    "AR | BEIN SPORTS 7 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13602.ts",
    "AR | BEIN SPORTS 8 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13611.ts",
    "AR | BEIN SPORTS 9 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/13610.ts",
    "AR | BEIN SPORTS NBA FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/21197.ts",
    "TR | BEIN SPORTS 1 FHD": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/79457.ts",
    "US | BEIN SPORTS US": "http://tv.gold-pro.xyz:80/live/yqKy0YRZ/f6dUahs/328821.ts",
}

DEFAULT_FALLBACK_CHANNELS: List[Dict[str, Any]] = [
    {"id": i + 1, "name": name, "stream_url": url}
    for i, (name, url) in enumerate(DEFAULT_CHANNELS_MAP.items())
]

# ---------------------------------------------------------------------------
# 2. SUPABASE CHANNELS MANAGER (ASYNC WITH IN-MEMORY CACHE)
# ---------------------------------------------------------------------------
class SupabaseChannelManager:
    """Manages Supabase channel retrieval with smart caching and auto fallback."""
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
                logging.info("ℹ️ جدول Supabase لم يعد بيانات بعد، تم تفعيل القنوات المدمجة (%d قناة).", len(DEFAULT_FALLBACK_CHANNELS))
                return DEFAULT_FALLBACK_CHANNELS
        except Exception as exc:
            logging.error("❌ خطأ أثناء استعلام Supabase: %s. يتم استخدام القنوات المدمجة.", exc)
            return DEFAULT_FALLBACK_CHANNELS

    def clear_cache(self) -> None:
        self._cache = []
        self._last_fetch_time = 0.0

channel_manager = SupabaseChannelManager(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------------------------
# 3. CHECK MEMBERSHIP (FORCE SUBSCRIPTION)
# ---------------------------------------------------------------------------
async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم مشتركاً في القناة الإجبارية @alifootball95"""
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        return False
    except Exception as exc:
        logging.warning("⚠️ تعذر التحقق من اشتراك المستخدم %s: %s", user_id, exc)
        return True

def get_subscription_markup() -> InlineKeyboardMarkup:
    """لوحة أزرار الاشتراك الإجباري"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 اشتراك في القناة الرسمية", url=REQUIRED_CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ لقد اشتركت، تحقق الآن", callback_data="check_sub")]
        ]
    )

# ---------------------------------------------------------------------------
# 4. DIRECT VLC INTENT BUILDER
# ---------------------------------------------------------------------------
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
# 5. KEYBOARD BUILDERS (PAGINATION & INTENT PLAYBACK)
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
        ch_name = ch.get("name", f"قناة #{idx + 1}")
        keyboard.append([
            InlineKeyboardButton(
                text=f"📺 {ch_name}",
                callback_data=f"ch:{idx}:{page}",
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

def build_channel_playback_markup(channel_idx: int, channel: Dict[str, Any], return_page: int) -> InlineKeyboardMarkup:
    stream_url = channel.get("stream_url", "")
    vlc_intent = build_vlc_intent_url(stream_url)
    keyboard: List[List[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="🎬 تشغيل مباشر في مشغل VLC", url=vlc_intent)],
        [InlineKeyboardButton(text="📲 تثبيت تطبيق VLC (Google Play)", url=PLAY_STORE_VLC_URL)],
        [InlineKeyboardButton(text="🔙 العودة لقائمة القنوات", callback_data=f"page:{return_page}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ---------------------------------------------------------------------------
# 6. UI TEXT TEMPLATES WITH BRANDING & WATERMARK
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
        f"📲 <i>إذا لم يكن تطبيق VLC مثبتاً لديك، سيوجهك الرابط تلقائياً لمتجر Google Play لتثبيته فوراً.</i>\n\n"
        f"🔗 <b>رابط البث المباشر (نسخ يدوي):</b>\n"
        f"<code>{safe_stream}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ <code>{WATERMARK}</code>"
    )

def get_help_text() -> str:
    return (
        f"<b>{BOT_BRAND} - دليل الاستخدام السريع</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"1️⃣ <b>تثبيت مشغل VLC:</b>\n"
        f"تأكد من وجود تطبيق <b>VLC for Android</b> على هاتفك لتشغيل البث بأعلى جودة وبدون تقطيع.\n\n"
        f"2️⃣ <b>التشغيل الفوري:</b>\n"
        f"عند اختيار أي قناة، اضغط على زر <b>'تشغيل مباشر في مشغل VLC'</b> وسيتم إطلاق البث تلقائياً داخل المشغل.\n\n"
        f"3️⃣ <b>التنقل بين القنوات:</b>\n"
        f"استخدم أزرار (السابق / التالي) للتنقل بين الصفحات بسهولة.\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷️ <code>{WATERMARK}</code>"
    )

# ---------------------------------------------------------------------------
# 7. DISPATCHER & BOT EVENT HANDLERS
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

@dp.message(Command("channels"))
async def cmd_channels_handler(message: Message) -> None:
    await render_channels_menu(message, page=0)

@dp.message(Command("refresh"))
async def cmd_refresh_handler(message: Message) -> None:
    channel_manager.clear_cache()
    await message.answer("🔄 جاري تحديث قائمة القنوات...")
    await render_channels_menu(message, page=0, force_refresh=True)

@dp.message(F.text.lower().in_(["start", "star", "ابدأ", "ابدا", "قنوات", "القنوات", "menu", "قائمة", "تحديث"]))
async def text_trigger_handler(message: Message) -> None:
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
        channel_idx = int(parts[1])
        return_page = int(parts[2]) if len(parts) > 2 else 0
        channels = await channel_manager.get_channels()
        if 0 <= channel_idx < len(channels):
            channel = channels[channel_idx]
            detail_text = get_channel_detail_text(channel)
            markup = build_channel_playback_markup(channel_idx, channel, return_page)
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
            text=get_help_text(),
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )
        await callback.answer()
    except Exception as exc:
        logging.error("Help callback error: %s", exc)
        await callback.answer()

@dp.callback_query(F.data == "noop")
async def noop_callback_handler(callback: CallbackQuery) -> None:
    channels = await channel_manager.get_channels()
    total_pages = max(1, (len(channels) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    await callback.answer(f"📄 إجمالي الصفحات: {total_pages} صفحة")

# ---------------------------------------------------------------------------
# 8. RESILIENT CLOUD HEALTH CHECK & WEB PLAYER SERVER (FOR RENDER.COM)
# ---------------------------------------------------------------------------
async def health_check_handler(request: web.Request) -> web.Response:
    status_msg = (
        f"🟢 {BOT_BRAND} is LIVE and healthy on Render!\n"
        f"🏷️ Watermark: {WATERMARK}\n"
        f"📢 Required Channel: {REQUIRED_CHANNEL_USERNAME}\n"
        f"🗄️ Supabase: {'Connected' if channel_manager.is_configured() else 'Active with built-in channels'}\n"
        f"🤖 Telegram Bot: Configured and Running\n"
    )
    return web.Response(text=status_msg, content_type="text/plain", charset="utf-8")

async def web_player_handler(request: web.Request) -> web.Response:
    possible_paths = [
        os.path.join(os.path.dirname(__file__), "web_player", "index.html"),
        os.path.join(os.path.dirname(__file__), "index.html"),
        "web_player/index.html",
        "index.html",
    ]
    for p in possible_paths:
        if os.path.isfile(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read()
                return web.Response(text=content, content_type="text/html", charset="utf-8")
            except Exception as exc:
                logging.error("Error reading web player HTML: %s", exc)
    return web.Response(text="Web Player HTML file not found.", status=404)

async def start_health_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)
    app.router.add_get("/player", web_player_handler)
    app.router.add_get("/web_player", web_player_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info("✅ Healthcheck & Web Player server listening on 0.0.0.0:%d (Render Ready 🟢)", port)
    return runner

# ---------------------------------------------------------------------------
# 9. APPLICATION ENTRYPOINT (FAIL-SAFE FOR CLOUD HOSTING)
# ---------------------------------------------------------------------------
async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logger = logging.getLogger("aliSTREAM.bot")
    
    print("\n" + "=" * 65)
    print(f"🚀 {BOT_BRAND} - تشغيل النظام السحابي")
    print(f"🏷️ Watermark: {WATERMARK}")
    print(f"📢 قناة الاشتراك الإجباري: {REQUIRED_CHANNEL_USERNAME}")
    print(f"🌐 Cloud Port: {PORT}")
    print(f"📡 القنوات الجاهزة للتشغيل: {len(DEFAULT_FALLBACK_CHANNELS)} قناة مدمجة")
    print(f"🗄️ Supabase: {'✅ متصل ومفعل' if channel_manager.is_configured() else 'ℹ️ القنوات المدمجة نشطة'}")
    print("=" * 65 + "\n")

    http_runner = None
    try:
        http_runner = await start_health_server(PORT)
    except Exception as exc:
        logger.error("❌ Could not bind health check server on port %d: %s", PORT, exc)

    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    retry_delay = 5
    while True:
        try:
            bot_info = await bot.get_me()
            logger.info("✅ تم الاتصال بنجاح بخوادم تيليجرام: @%s (ID: %s)", bot_info.username, bot_info.id)
            logger.info("🟢 البوت يستقبل الرسائل والتحديثات الآن...")
            await bot.delete_webhook(drop_pending_updates=False)
            await dp.start_polling(bot)
            break
        except TelegramUnauthorizedError:
            logger.error("❌ التوكن BOT_TOKEN غير مصرح به (401 Unauthorized)! يرجى التحقق من توكن البوت.")
            await asyncio.sleep(60)
        except TelegramConflictError:
            logger.warning("⚠️ يوجد تضارب: هناك نسخة أخرى تعمل بنفس التوكن. إعادة المحاولة بعد %d ثوانٍ...", retry_delay)
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)
        except TelegramNetworkError as net_err:
            logger.warning("⚠️ انقطاع مؤقت في الاتصال بـ Telegram (%s). إعادة المحاولة بعد 10 ثوانٍ...", net_err)
            await asyncio.sleep(10)
        except Exception as exc:
            logger.error("⚠️ حدث خطأ أثناء تشغيل البوت: %s. إعادة المحاولة بعد 10 ثوانٍ...", exc)
            await asyncio.sleep(10)

    if http_runner:
        await http_runner.cleanup()
    await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 تم إيقاف البوت بنجاح.")
