import os
import requests
from aiohttp import web
import threading
import time

TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"
CARD_NUMBER = "5859831873943517"
CARD_NAME = "برهان آذین فر"

URL = f"https://api.telegram.org/bot{TOKEN}"

user_sessions = {}

PLANS = {
    "multi_10g": {"title": "مولتی لوکیشن | ۱۰ گیگ - ۳۰ روزه", "price": "60,000"},
    "multi_20g": {"title": "مولتی لوکیشن | ۲۰ گیگ - ۳۰ روزه", "price": "110,000"},
    "multi_50g": {"title": "مولتی لوکیشن | ۵۰ گیگ - ۳۰ روزه", "price": "200,000"},
    "melli_10g": {"title": "ملی شکن | ۱۰ گیگ - ۳۰ روزه", "price": "70,000"},
    "melli_30g": {"title": "ملی شکن | ۳۰ گیگ - ۳۰ روزه", "price": "120,000"},
    "melli_50g": {"title": "ملی شکن | ۵۰ گیگ - ۳۰ روزه", "price": "210,000"},
    "melli_unlim_30g": {"title": "ملی شکن تایم نامحدود | ۳۰ گیگ", "price": "170,000"},
    "multi_unlim_100g": {"title": "مولتی لوکیشن تایم نامحدود | ۱۰۰ گیگ", "price": "300,000"},
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
                            user_sessions[chat_id]["server_name"] = text
                            user_sessions[chat_id]["step"] = "confirm_order"
                            
                            session = user_sessions[chat_id]
                            plan_info = PLANS[session["plan_key"]]
                            count = session["count"]
                            
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

                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        chat_id = cb["message"]["chat"]["id"]
                        data_key = cb["data"]

                        requests.post(f"{URL}/answerCallbackQuery", json={"callback_query_id": cb_id})

                        if data_key == "buy_service":
                            buy_keyboard = {
                                "inline_keyboard": [
                                    [{"text": "🇩🇪 🇳🇱 🇸🇪 🇸🇬 🇹🇷 مولتی لوکیشن", "callback_data": "cat_multi"}],
                                    [{"text": "🇮🇷 ملی شکن", "callback_data": "cat_melli"}],
                                    [{"text": "🇮🇷 ملی شکن زمان نامحدود", "callback_data": "cat_melli_unlim"}],
                                    [{"text": "🇩🇪 🇳🇱 🇸🇪 🇸🇬 🇹🇷 مولتی لوکیشن زمان نامحدود", "callback_data": "cat_multi_unlim"}],
                                    [{"text": "🇩🇪 نامحدود آلمان", "callback_data": "cat_germany"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "back_home"}]
                                ]
                            }
                            send_msg(chat_id, "🛒 برای خرید سرویس لطفا یکی از دسته‌بندی‌های زیر را انتخاب کنید:", buy_keyboard)

                        elif data_key == "cat_multi":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "۱۰ گیگ (۳۰ روزه) - ۶۰,۰۰۰ تومان", "callback_data": "plan_multi_10g"}],
                                    [{"text": "۲۰ گیگ (۳۰ روزه) - ۱۱۰,۰۰۰ تومان", "callback_data": "plan_multi_20g"}],
                                    [{"text": "۵۰ گیگ (۳۰ روزه) - ۲۰۰,۰۰۰ تومان", "callback_data": "plan_multi_50g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            send_msg(chat_id, "🌐 پلن‌های مولتی لوکیشن (۳ کاربره):", kb)

                        elif data_key == "cat_melli":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "۱۰ گیگ (۳۰ روزه) - ۷۰,۰۰۰ تومان", "callback_data": "plan_melli_10g"}],
                                    [{"text": "۳۰ گیگ (۳۰ روزه) - ۱۲۰,۰۰۰ تومان", "callback_data": "plan_melli_30g"}],
                                    [{"text": "۵۰ گیگ (۳۰ روزه) - ۲۱۰,۰۰۰ تومان", "callback_data": "plan_melli_50g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            send_msg(chat_id, "🇮🇷 پلن‌های ملی شکن (۲ کاربره):", kb)

                        elif data_key == "cat_melli_unlim":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "۳۰ گیگ تایم نامحدود - ۱۷۰,۰۰۰ تومان", "callback_data": "plan_melli_unlim_30g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            send_msg(chat_id, "♾️ پلن ملی شکن بدون محدودیت زمانی:", kb)

                        elif data_key == "cat_multi_unlim":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "۱۰۰ گیگ تایم نامحدود - ۳۰۰,۰۰۰ تومان", "callback_data": "plan_multi_unlim_100g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            send_msg(chat_id, "🌐 پلن مولتی لوکیشن بدون محدودیت زمانی:", kb)

                        elif data_key == "cat_germany":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "حجم نامحدود (۳۰ روزه) - ۹۰,۰۰۰ تومان", "callback_data": "plan_germany_30d"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            send_msg(chat_id, "🇩🇪 پلن اختصاصی آلمان (تک کاربره):", kb)

                        elif data_key.startswith("plan_"):
                            plan_key = data_key.replace("plan_", "")
                            user_sessions[chat_id] = {"plan_key": plan_key}
                            plan_info = PLANS[plan_key]

                            text = (
                                f"📌 <b>مشخصات سرویس انتخاب شده:</b>\n\n"
                                f"🔹 <b>نام پلن:</b> {plan_info['title']}\n"
                                f"💰 <b>قیمت:</b> {plan_info['price']} تومان\n\n"
                                f"آیا قصد خرید این سرویس را دارید؟"
                            )
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "✅ تایید و ادامه خرید", "callback_data": "confirm_plan"}],
                                    [{"text": "🔙 انصراف و بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            send_msg(chat_id, text, kb)

                        elif data_key == "confirm_plan":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "1", "callback_data": "count_1"}, {"text": "2", "callback_data": "count_2"}, {"text": "3", "callback_data": "count_3"}],
                                    [{"text": "4", "callback_data": "count_4"}, {"text": "5", "callback_data": "count_5"}],
                                    [{"text": "🔙 انصراف", "callback_data": "buy_service"}]
                                ]
                            }
                            send_msg(chat_id, "🔢 لطفا تعداد سرویس مورد نیاز خود را انتخاب کنید:", kb)

                        elif data_key.startswith("count_"):
                            count = int(data_key.split("_")[1])
                            user_sessions[chat_id]["count"] = count
                            user_sessions[chat_id]["step"] = "wait_for_name"
                            
                            send_msg(chat_id, "✍️ لطفا یک نام برای سرویس خود ارسال کنید:\n(مثلاً: Phone-1 یا Ali-Vpn)")

                        elif data_key == "pay_card":
                            session = user_sessions.get(chat_id, {})
                            price = session.get("total_price", "0")
                            
                            pay_text = (
                                f"💳 <b>اطلاعات پرداخت کارت به کارت:</b>\n\n"
                                f"لطفاً مبلغ <b>{price} تومان</b> را به شماره کارت زیر واریز نمایید:\n\n"
                                f"👤 <b>به نام:</b> {CARD_NAME}\n"
                                f"🔢 <b>شماره کارت (برای کپی لمس کنید):</b>\n"
                                f"<code>{CARD_NUMBER}</code>\n\n"
                                f"⚠️ پس از واریز، تصویر فیش واریزی را برای پشتیبانی ارسال کنید تا سرویس شما فعال شود."
                            )
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "📞 ارسال فیش به پشتیبانی", "callback_data": "support"}],
                                    [{"text": "🏠 بازگشت به منوی اصلی", "callback_data": "back_home"}]
                                ]
                            }
                            send_msg(chat_id, pay_text, kb)

                        elif data_key == "back_home":
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
                            send_msg(chat_id, "منوی اصلی:", keyboard)

                        elif data_key == "support":
                            send_msg(chat_id, "📞 جهت ارتباط با پشتیبانی و ارسال فیش واریزی، به آیدی زیر پیام دهید:\n\n🆔 @Azin_Support")

        except Exception as e:
            print(f"Bot Error: {e}")
            time.sleep(3)

async def handle(request):
    return web.Response(text="Azin Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
