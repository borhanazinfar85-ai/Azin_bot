import os
import requests
from aiohttp import web
import threading
import time

TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"
URL = f"https://api.telegram.org/bot{TOKEN}"

# ۱. بخش ربات تلگرام که به صورت پس‌زمینه و مستقل کار می‌کند
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
                    message = update.get("message")
                    if message and "text" in message:
                        chat_id = message["chat"]["id"]
                        text = message["text"]
                        
                        if text == "/start":
                            keyboard = {
                                "inline_keyboard": [
                                    [
                                        {"text": "🛒 خرید سرویس جدید", "callback_data": "buy_service"},
                                        {"text": "💼 سرویس‌های من", "callback_data": "my_services"}
                                    ],
                                    [
                                        {"text": "👤 حساب کاربری", "callback_data": "account"},
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
        except Exception as e:
            print(f"Bot Error: {e}")
            time.sleep(3)

# ۲. بخش وب‌سرور برای راضی نگه داشتن رندر
async def handle(request):
    return web.Response(text="Azin Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

if __name__ == "__main__":
    # اجرای ربات در ترد جداگانه تا با وب‌سرور تداخل نداشته باشد
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # اجرای وب‌سرور روی پورت رندر
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
