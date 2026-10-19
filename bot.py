import os
import requests
from aiohttp import web
import threading
import time

TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"
URL = f"https://api.telegram.org/bot{TOKEN}"

# ۱. بخش ربات تلگرام و مدیریت دکمه‌ها
def run_bot():
    offset = 0
    print("Telegram bot started...")
    while True:
        try:
            response = requests.get(f"{URL}/getUpdates", params={"offset": offset, "timeout": 30})
            data = response.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    # بررسی پیام‌ها (مثل /start)
                    if "message" in update and "text" in update["message"]:
                        message = update["message"]
                        chat_id = message["chat"]["id"]
                        text = message["text"]
                        
                        if text == "/start":
                            keyboard = {
                                "inline_keyboard": [
                                    [
                                        {"text": "🛒 خرید سرویس جدید", "callback_data": "buy_service"}
                                    ],
                                    [
                                        {"text": "💼 سرویس‌های من", "callback_data": "my_services"},
                                        {"text": "👤 حساب کاربری", "callback_data": "account"}
                                    ],
                                    [
                                        {"text": "🎁 ثبت کارت هدیه", "callback_data": "gift_card"}
                                    ],
                                    [
                                        {"text": "📥 دانلود و دریافت اپلیکیشن‌ها", "callback_data": "apps"}
                                    ],
                                    [
                                        {"text": "📞 پشتیبانی", "callback_data": "support"}
                                    ]
                                ]
                            }
                            payload = {
                                "chat_id": chat_id,
                                "text": "⭐ به فروشگاه آذین خوش آمدید ⭐\n\n🌟 پشتیبانی ۲۴/۷\n🌟 پایداری و سرعت فوق العاده\n🌟 ارائه دهنده فیلترشکن برای گیم و ترید\n\nاز منوی زیر بخش مورد نظر خود را انتخاب کنید.",
                                "reply_markup": keyboard
                            }
                            requests.post(f"{URL}/sendMessage", json=payload)

                    # بررسی کلیک روی دکمه‌های شیشه‌ای (Inline Keyboards)
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        callback_id = callback["id"]
                        chat_id = callback["message"]["chat"]["id"]
                        data_key = callback["data"]

                        # پاسخ به کلیک کاربر (برای اینکه چرخش لودینگ دکمه متوقف شود)
                        requests.post(f"{URL}/answerCallbackQuery", json={"callback_query_id": callback_id})

                        if data_key == "buy_service":
                            # منوی انتخاب سرویس‌ها (بدون واژه همکار) مطابق تصویر شما
                            buy_keyboard = {
                                "inline_keyboard": [
                                    [{"text": "🇩🇪 🇳🇱 🇸🇪 🇸🇬 🇹🇷 مولتی لوکیشن", "callback_data": "multi_loc"}],
                                    [{"text": "🇮🇷 ملی شکن", "callback_data": "melli_shekan"}],
                                    [{"text": "🇮🇷 ملی شکن زمان نامحدود", "callback_data": "melli_unlimited"}],
                                    [{"text": "🇩🇪 🇳🇱 🇸🇪 🇸🇬 🇹🇷 مولتی لوکیشن زمان نامحدود", "callback_data": "multi_unlimited"}],
                                    [{"text": "🇩🇪 نامحدود آلمان", "callback_data": "germany_unlimited"}],
                                    [{"text": "🚀 وایرگارد", "callback_data": "wireguard"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "back_home"}]
                                ]
                            }
                            requests.post(f"{URL}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "🛒 برای خرید سرویس لطفا یکی از دسته‌بندی‌های زیر را انتخاب کنید:",
                                "reply_markup": buy_keyboard
                            })

                        elif data_key == "back_home":
                            # بازگشت به منوی اصلی
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "🛒 خرید سرویس جدید", "callback_data": "buy_service"}],
                                    [{"text": "💼 سرویس‌های من", "callback_data": "my_services"}, {"text": "👤 حساب کاربری", "callback_data": "account"}],
                                    [{"text": "🎁 ثبت کارت هدیه", "callback_data": "gift_card"}],
                                    [{"text": "📥 دانلود و دریافت اپلیکیشن‌ها", "callback_data": "apps"}],
                                    [{"text": "📞 پشتیبانی", "callback_data": "support"}]
                                ]
                            }
                            requests.post(f"{URL}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "منوی اصلی:",
                                "reply_markup": keyboard
                            })
                        else:
                            # برای سایر بخش‌ها فعلاً یک پیام موقت
                            requests.post(f"{URL}/sendMessage", json={
                                "chat_id": chat_id,
                                "text": "این بخش به زودی فعال خواهد شد."
                            })

        except Exception as e:
            print(f"Bot Error: {e}")
            time.sleep(3)

# ۲. وب‌سرور برای رندر
async def handle(request):
    return web.Response(text="Azin Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
