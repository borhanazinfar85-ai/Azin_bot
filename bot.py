import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

#توکن ربات خود را اینجا وارد کنید
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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
