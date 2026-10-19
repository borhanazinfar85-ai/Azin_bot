import os
import requests
from aiohttp import web
import threading
import time

# تنظیمات اصلی
TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"
CARD_NUMBER = "5859831873943517"  # شماره کارت خود را اینجا وارد کنید
CARD_NAME = "برهان آذین فر"     # نام صاحب حساب

URL = f"https://api.telegram.org/bot{TOKEN}"

# ذخیره موقت وضعیت کاربران برای مراحل چندگانه خرید
user_sessions = {}

# تعریف کامل پلن‌ها بر اساس پوستر
PLANS = {
    # مولتی لوکیشن ۳۰ روزه
    "multi_10g": {"title": "مولتی لوکیشن | ۱۰ گیگ - ۳۰ روزه", "price": "60,000"},
    "multi_20g": {"title": "مولتی لوکیشن | ۲۰ گیگ - ۳۰ روزه", "price": "110,000"},
    "multi_50g": {"title": "مولتی لوکیشن | ۵۰ گیگ - ۳۰ روزه", "price": "200,000"},
    
    # ملی شکن ۳۰ روزه
    "melli_10g": {"title": "ملی شکن | ۱۰ گیگ - ۳۰ روزه", "price": "70,000"},
    "melli_30g": {"title": "ملی شکن | ۳۰ گیگ - ۳۰ روزه", "price": "120,000"},
    "melli_50g": {"title": "ملی شکن | ۵۰ گیگ - ۳۰ روزه", "price": "210,000"},

    # ملی شکن زمان نامحدود
    "melli_unlim_30g": {"title": "ملی شکن تایم نامحدود | ۳۰ گیگ", "price": "170,000"},

    # مولتی لوکیشن زمان نامحدود
    "multi_unlim_100g": {"title": "مولتی لوکیشن تایم نامحدود | ۱۰۰ گیگ", "price": "300,000"},

    # آلمان نامحدود
    "germany_30d": {"title": "المان نامحدود | تک کاربره - ۳۰ روزه", "price": "90,000"}
}

def send_msg(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if keyboard:
        payload["reply_markup"] = keyboard
    return requests.post(f"{URL}/sendMessage", json=payload)

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
                    
                    # ۱. دریافت پیام‌های متنی (برای وارد کردن اسم سرور)
                    if "message" in update and "text" in update["message"]:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        text = msg["text"]
                        
                        if text == "/start":
                            user_sessions[chat_id] = {}
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "🛒 خرید سرویس جدید", "callback_data": "buy_service"}],
                                    [{"text": "💼 سرویس‌های من", "callback_data": "my_services"}, {"text": "👤 حساب کاربری", "callback_data": "account"}],
                                    [{"text": "🎁 ثبت کارت هدیه", "callback_data": "gift_card"}],
                                    [{"text": "📥 دانلود و دریافت اپلیکیشن‌ها", "callback_data": "apps"}],
                                    [{"text": "📞 پشتیبانی", "callback_data": "support"}]
                                ]
                            }
                            send_msg(chat_id, "⭐ به فروشگاه آذین خوش آمدید ⭐\n\n🌟 پشتیبانی ۲۴/۷\n🌟 پایداری و سرعت فوق العاده\n🌟 ارائه دهنده فیلترشکن برای گیم و ترید\n\nاز منوی زیر بخش مورد نظر خود را انتخاب کنید.", keyboard)

                        elif user_sessions.get(chat_id, {}).get("step") == "wait_for_name":
                            # کاربر نام سرور را وارد کرده است
                            user_sessions[chat_id]["server_name"] = text
                            user_sessions[chat_id]["step"] = "confirm_order"
                            
                            session = user_sessions[chat_id]
                            plan_info = PLANS[session["plan_key"]]
                            count = session["count"]
                            
                            # محاسبه قیمت کل
                            single_price = int(plan_info["price"].replace(",", ""))
                            total_price = single_price * count
                            session["total_price"] = f"{total_price:,}"
                            
                            fact_text = (
                                f"📋 <b>فاکتور نهایی سفارش:</b>\n\n"
                                f"🔹 <b>سرویس:</b> {plan_info['title']}\n"
                                f"🔹 <b>تعداد:</b> {count} عدد\n"
                                f"🔹 <b>نام سرور:</b> {text}\n"
                                f"💰 <b>مبلغ قابل پرداخت:</b> {session['total_price']} تومان\n\n"
                                f"لطفاً روش پرداخت را انتخاب کنید:"
                            )
                            keyboard = {
                                "inline_keyboard": [
                                    [{"text": "💳 پرداخت کارت به کارت", "callback_data": "pay_card"}],
                                    [{"text": "❌ انصراف", "callback_data": "back_home"}]
                                ]
                            }
                            send_msg(chat_id, fact_text, keyboard)

                    # ۲. بررسی کلیک روی دکمه‌های شیشه‌ای
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        chat_id = cb["message"]["chat"]["id"]
                        data_key = cb["data"]

                        requests.post(f"{URL}/answerCallbackQuery", json={"callback_query
