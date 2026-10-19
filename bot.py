import os
import requests
from aiohttp import web
import threading
import time

# ------------------ تنظیمات اصلی ------------------
TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"
ADMIN_ID = 5992998183  # <--- عددیِ آیدی تلگرام خود را اینجا بگذارید (بدون کوتیشن)
CARD_NUMBER = "5859831873943517"
CARD_NAME = "برهان آذین فر"
SUPPORT_USERNAME = "@Brn_Az"

URL = f"https://api.telegram.org/bot{TOKEN}"

# دیتابیس حافظه‌ای موقت
user_sessions = {}
orders_db = {}     # ذخیره سفارش‌ها با ID اختصاصی
stats_db = {
    "total_orders": 0,
    "pending_orders": 0,
    "approved_orders": 0,
    "rejected_orders": 0
}

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

# تنظیم منوی سریع تلگرام (دستورات کنار کادر تایپ)
def set_bot_commands():
    commands = [
        {"command": "start", "description": "شروع و منوی اصلی"},
        {"command": "admin", "description": "پنل مدیریت (ویژه ادمین)"},
        {"command": "help", "description": "ارتباط با پشتیبانی"}
    ]
    requests.post(f"{URL}/setMyCommands", json={"commands": commands})

def send_msg(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if keyboard:
        payload["reply_markup"] = keyboard
    return requests.post(f"{URL}/sendMessage", json=payload)

def send_photo(chat_id, photo_id, caption, keyboard=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "photo": photo_id, "caption": caption, "parse_mode": parse_mode}
    if keyboard:
        payload["reply_markup"] = keyboard
    return requests.post(f"{URL}/sendPhoto", json=payload)

def get_main_keyboard(user_id):
    buttons = [
        [{"text": "🛒 خرید سرویس جدید", "callback_data": "buy_service"}],
        [{"text": "💼 سرویس‌های من", "callback_data": "my_services"}, {"text": "👤 حساب کاربری", "callback_data": "account"}],
        [{"text": "🎁 ثبت کارت هدیه", "callback_data": "gift_card"}],
        [{"text": "📥 دانلود و دریافت اپلیکیشن‌ها", "callback_data": "apps"}],
        [{"text": "📞 پشتیبانی", "callback_data": "support"}]
    ]
    if user_id == ADMIN_ID:
        buttons.append([{"text": "⚙️ پنل مدیریت (ادمین)", "callback_data": "admin_panel"}])
    return {"inline_keyboard": buttons}

def run_bot():
    set_bot_commands()
    offset = 0
    print("Telegram bot started...")
    while True:
        try:
            response = requests.get(f"{URL}/getUpdates", params={"offset": offset, "timeout": 30})
            data = response.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    
                    # ------------------ مدیریت پیام‌ها ------------------
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        username = msg["from"].get("username", "ندارد")
                        
                        # ۱. متن‌ها
                        if "text" in msg:
                            text = msg["text"]
                            
                            if text == "/start":
                                user_sessions[chat_id] = {}
                                send_msg(chat_id, "⭐ به فروشگاه آذین خوش آمدید ⭐\n\n🌟 پشتیبانی ۲۴/۷\n🌟 پایداری و سرعت فوق العاده\n🌟 ارائه دهنده فیلترشکن برای گیم و ترید\n\nاز منوی زیر بخش مورد نظر خود را انتخاب کنید.", get_main_keyboard(user_id))

                            elif text == "/admin" and user_id == ADMIN_ID:
                                show_admin_panel(chat_id)

                            elif text == "/help":
                                send_msg(chat_id, f"📞 جهت ارتباط با پشتیبانی به آیدی زیر پیام دهید:\n\n🆔 {SUPPORT_USERNAME}")

                            # دریافت نام سرور از مشتری
                            elif user_sessions.get(chat_id, {}).get("step") == "wait_for_name":
                                user_sessions[chat_id]["server_name"] = text
                                user_sessions[chat_id]["step"] = "wait_for_receipt"
                                
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
                                    f"💳 <b>اطلاعات کارت:</b>\n"
                                    f"👤 به نام: {CARD_NAME}\n"
                                    f"<code>{CARD_NUMBER}</code> (لمس برای کپی)\n\n"
                                    f"📸 <b>لطفاً عکس فیش واریزی خود را همینجا ارسال کنید.</b>"
                                )
                                send_msg(chat_id, fact_text)

                            # ادمین در حال ارسال کانفیگ/لینک سرویس به مشتری
                            elif user_sessions.get(chat_id, {}).get("step") == "admin_sending_config":
                                target_user_id = user_sessions[chat_id]["target_user"]
                                order_id = user_sessions[chat_id]["order_id"]
                                
                                # ارسال سرور به مشتری
                                client_msg = (
                                    f"🎉 <b>سفارش شما تایید و آماده شد!</b>\n\n"
                                    f"🔑 <b>اطلاعات سرویس شما:</b>\n\n"
                                    f"<code>{text}</code>\n\n"
                                    f"با تشکر از خرید شما - فروشگاه آذین"
                                )
                                send_msg(target_user_id, client_msg)
                                send_msg(chat_id, "✅ سرویس با موفقیت برای مشتری ارسال شد.")
                                user_sessions[chat_id] = {}

                        # ۲. دریافت عکس فیش از مشتری
                        elif "photo" in msg and user_sessions.get(chat_id, {}).get("step") == "wait_for_receipt":
                            photo_id = msg["photo"][-1]["file_id"]
                            session = user_sessions[chat_id]
                            plan_info = PLANS[session["plan_key"]]
                            
                            # ثبت سفارش در سیستم
                            order_id = str(int(time.time()))
                            orders_db[order_id] = {
                                "user_id": chat_id,
                                "username": username,
                                "plan": plan_info['title'],
                                "count": session['count'],
                                "server_name": session['server_name'],
                                "price": session['total_price'],
                                "status": "Pending"
                            }
                            stats_db["total_orders"] += 1
                            stats_db["pending_orders"] += 1

                            send_msg(chat_id, "✅ فیش واریزی شما با موفقیت ثبت شد و برای ادمین ارسال گردید.\nپس از بررسی، سرویس برای شما ارسال خواهد شد.")

                            # ارسال فیش و اطلاعات کامل به ادمین
                            admin_caption = (
                                f"📥 <b>سفارش جدید دریافت شد!</b>\n\n"
                                f"🆔 <b>آیدی عددی:</b> <code>{chat_id}</code>\n"
                                f"👤 <b>آیدی تلگرام:</b> @{username}\n"
                                f"🔹 <b>سرویس:</b> {plan_info['title']}\n"
                                f"🔹 <b>تعداد:</b> {session['count']}\n"
                                f"🔹 <b>نام سرور:</b> {session['server_name']}\n"
                                f"💰 <b>مبلغ:</b> {session['total_price']} تومان\n"
                                f"🆔 <b>شناسه سفارش:</b> #{order_id}"
                            )
                            admin_kb = {
                                "inline_keyboard": [
                                    [
                                        {"text": "✅ تایید پرداخت", "callback_data": f"approve_{order_id}"},
                                        {"text": "❌ رد پرداخت", "callback_data": f"reject_{order_id}"}
                                    ]
                                ]
                            }
                            send_photo(ADMIN_ID, photo_id, admin_caption, admin_kb)
                            user_sessions[chat_id] = {}

                    # ------------------ مدیریت کلیک دکمه‌ها ------------------
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

                        # -------------- عملیات ادمین روی سفارشات --------------
                        elif data_key.startswith("approve_"):
                            order_id = data_key.split("_")[1]
                            order = orders_db.get(order_id)
                            if order:
                                order["status"] = "Approved"
                                stats_db["pending_orders"] -= 1
                                stats_db["approved_orders"] += 1
                                
                                user_sessions[chat_id] = {
                                    "step": "admin_sending_config",
                                    "target_user": order["user_id"],
                                    "order_id": order_id
                                }
                                send_msg(chat_id, f"✅ سفارش #{order_id} تایید شد.\n\nلطفاً لینک/کانفیگ سرور را ارسال کنید تا برای مشتری فرستاده شود:")

                        elif data_key.startswith("reject_"):
                            order_id = data_key.split("_")[1]
                            order = orders_db.get(order_id)
                            if order:
                                order["status"] = "Rejected"
                                stats_db["pending_orders"] -= 1
                                stats_db["rejected_orders"] += 1
                                
                                send_msg(order["user_id"], "❌ پرداخت شما تایید نشد. در صورت وجود مشکل با پشتیبانی در ارتباط باشید.")
                                send_msg(chat_id, f"❌ سفارش #{order_id} رد شد و به اطلاع مشتری رسید.")

                        elif data_key == "admin_panel" and chat_id == ADMIN_ID:
                            show_admin_panel(chat_id)

                        elif data_key == "back_home":
                            user_sessions[chat_id] = {}
                            send_msg(chat_id, "منوی اصلی:", get_main_keyboard(chat_id))

                        elif data_key == "support":
                            send_msg(chat_id, f"📞 جهت ارتباط با پشتیبانی به آیدی زیر پیام دهید:\n\n🆔 {SUPPORT_USERNAME}")

        except Exception as e:
            print(f"Bot Error: {e}")
            time.sleep(3)

def show_admin_panel(chat_id):
    admin_text = (
        f"⚙️ <b>پنل مدیریت فروشگاه آذین</b>\n\n"
        f"📊 <b>آمار کل فروشگاه:</b>\n"
        f"▫️ کل سفارش‌ها: {stats_db['total_orders']}\n"
        f"⏳ در انتظار تایید: {stats_db['pending_orders']}\n"
        f"✅ تایید شده: {stats_db['approved_orders']}\n"
        f"❌ رد شده: {stats_db['rejected_orders']}\n"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "🔄 بروزرسانی آمار", "callback_data": "admin_panel"}],
            [{"text": "🏠 منوی اصلی", "callback_data": "back_home"}]
        ]
    }
    send_msg(chat_id, admin_text, kb)

async def handle(request):
    return web.Response(text="Azin Bot is running!")

app = web.Application()
app.router.add_get("/", handle)

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
