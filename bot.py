import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# توکن ربات خود را اینجا وارد کنید
TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# منوی اصلی فروشگاه آذین
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 خرید سرویس جدید", callback_data="buy_service"),
            InlineKeyboardButton(text="💼 سرویس‌های من", callback_data="my_services")
        ],
        [
            InlineKeyboardButton(text="👤 حساب کاربری", callback_data="account"),
            InlineKeyboardButton(text="🎁 ثبت کارت هدیه", callback_data="gift_card")
        ],
        [
            InlineKeyboardButton(text="📥 دانلود و دریافت اپلیکیشن‌ها", callback_data="apps")
        ],
        [
            InlineKeyboardButton(text="📞 پشتیبانی", callback_data="support")
        ]
    ])

@dp.message(Command("start"))
async def start_command(message: Message):
    welcome_text = (
        "⭐ به فروشگاه آذین خوش آمدید ⭐\n\n"
        "🌟 پشتیبانی ۲۴/۷\n"
        "🌟 پایداری و سرعت فوق العاده\n"
        "🌟 ارائه دهنده فیلترشکن برای گیم و ترید\n\n"
        "از منوی زیر بخش مورد نظر خود را انتخاب کنید."
    )
    await message.answer(welcome_text, reply_markup=get_main_menu())

# یک وب‌سرور کوچک برای راضی کردن رندر روی پورت دلخواه
async def handle(request):
    return web.Response(text="Azin Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    # اجرای همزمان ربات و وب‌سرور
    await asyncio.gather(
        web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
