import os
import requests
from aiohttp import web
import threading
import time

# ------------------ تنظیمات اصلی ------------------
TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"
ADMIN_ID = 5992998183  # <--- آیدی عددی تلگرام خودتان
CARD_NUMBER = "5859831873943517"
CARD_NAME = " آذین فر"
SUPPORT_USERNAME = "@Brn_Az"

URL = f"https://api.telegram.org/bot{TOKEN}"

# دیتابیس‌های حافظه‌ای
user_sessions = {}
orders_db = {}
users_db = {}
stats_db = {
    "total_orders": 0,
    "pending_orders": 0,
    "approved_orders": 0,
    "rejected_orders": 0,
    "total_income": 0
}

# پلن‌ها (قابل تغییر از داخل ربات توسط ادمین)
PLANS = {
    "multi_10g": {"title": "مولتی لوکیشن | ۱۰ گیگ - ۳۰ روزه", "price": "60,000", "numeric_price": 60000},
    "multi_20g": {"title": "مولتی لوکیشن | ۲۰ گیگ - ۳۰ روزه", "price": "110,000", "numeric_price": 110000},
    "multi_50g": {"title": "مولتی لوکیشن | ۵۰ گیگ - ۳۰ روزه", "price": "200,000", "numeric_price": 200000},
    "melli_10g": {"title": "ملی شکن | ۱۰ گیگ - ۳۰ روزه", "price": "70,000", "numeric_price": 70000},
    "melli_30g": {"title": "ملی شکن | ۳۰ گیگ - ۳۰ روزه", "price": "120,000", "numeric_price": 120000},
    "melli_50g": {"title": "ملی شکن | ۵۰ گیگ - ۳۰ روزه", "price": "210,000", "numeric_price": 210000},
    "melli_unlim_30g": {"title": "ملی شکن تایم نامحدود | ۳۰ گیگ", "price": "170,000", "numeric_price": 170000},
    "multi_unlim_100g": {"title": "مولتی لوکیشن تایم نامحدود | ۱۰۰ گیگ", "price": "300,000", "numeric_price": 300000},
    "germany_30d": {"title": "المان نامحدود | تک کاربره - ۳۰ روزه", "price": "90,000", "numeric_price": 90000}
}

def set_bot_commands():
    commands = [
        {"command": "start", "description": "🚀 شروع و منوی اصلی"},
        {"command": "admin", "description": "⚙️ پنل مدیریت (ادمین)"},
        {"command": "help", "description": "💬 ارتباط با پشتیبانی"}
    ]
    requests.post(f"{URL}/setMyCommands", json={"commands": commands})

# ارسال پیام جدید (برای شروع یا فیش)
def send_msg(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if keyboard:
        payload["reply_markup"] = keyboard
    return requests.post(f"{URL}/sendMessage", json=payload)

# ویرایش پیام قبلی (برای منوها و کلیک‌ها بدون ارسال پیام جدید)
def edit_msg(chat_id, message_id, text, keyboard=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": parse_mode}
    if keyboard:
        payload["reply_markup"] = keyboard
    return requests.post(f"{URL}/editMessageText", json=payload)

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
        [{"text": "📲 دانلود و دریافت اپلیکیشن‌ها", "callback_data": "apps"}],
        [{"text": "💬 پشتیبانی و ارتباط با ما", "callback_data": "support"}]
    ]
    if user_id == ADMIN_ID:
        buttons.append([{"text": "⚙️ پنل مدیریت پیشرفته", "callback_data": "admin_panel"}])
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
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        first_name = msg["from"].get("first_name", "کاربر")
                        username = msg["from"].get("username", "ندارد")
                        
                        if chat_id not in users_db:
                            users_db[chat_id] = {
                                "first_name": first_name,
                                "username": username,
                                "join_date": time.strftime("%Y-%m-%d %H:%M"),
                                "purchased_services": []
                            }

                        if "text" in msg:
                            text = msg["text"]
                            
                            if text == "/start":
                                user_sessions[chat_id] = {}
                                welcome_text = (
                                    f"✨ <b>درود و احترام {first_name} عزیز، به فروشگاه آذین خوش آمدید!</b> ✨\n\n"
                                    f"🚀 <b>ارائه‌دهنده سرویس‌های اختصاصی و فوق‌سریع</b>\n"
                                    f"⚡️ پایداری عالی | مناسب گیم، ترید و وب‌گردی\n"
                                    f"🔰 پشتیبانی ۲۴ ساعته و همیشگی\n\n"
                                    f"👇 <i>از منوی زیر بخش مورد نظر خود را انتخاب کنید:</i>"
                                )
                                send_msg(chat_id, welcome_text, get_main_keyboard(user_id))

                            elif text == "/admin" and user_id == ADMIN_ID:
                                show_admin_panel(chat_id, msg.get("message_id"))

                            elif text == "/help":
                                send_msg(chat_id, f"💬 <b>پشتیبانی فروشگاه آذین:</b>\n\nهمکاران ما آماده پاسخگویی به سوالات شما هستند:\n🆔 {SUPPORT_USERNAME}")

                            elif user_sessions.get(chat_id, {}).get("step") == "admin_changing_price":
                                p_key = user_sessions[chat_id]["target_plan"]
                                try:
                                    new_price = int(text.replace(",", "").strip())
                                    PLANS[p_key]["numeric_price"] = new_price
                                    PLANS[p_key]["price"] = f"{new_price:,}"
                                    
                                    send_msg(chat_id, f"✅ <b>قیمت پلن «{PLANS[p_key]['title']}» با موفقیت به {new_price:,} تومان تغییر یافت.</b>")
                                    user_sessions[chat_id] = {}
                                    show_admin_panel(chat_id)
                                except ValueError:
                                    send_msg(chat_id, "⚠️ لطفاً قیمت را فقط به صورت عدد (مثلاً 80000) وارد کنید:")

                            elif user_sessions.get(chat_id, {}).get("step") == "wait_for_name":
                                user_sessions[chat_id]["server_name"] = text
                                user_sessions[chat_id]["step"] = "wait_for_receipt"
                                
                                session = user_sessions[chat_id]
                                plan_info = PLANS[session["plan_key"]]
                                count = session["count"]
                                total_price = plan_info["numeric_price"] * count
                                session["total_price_num"] = total_price
                                session["total_price_str"] = f"{total_price:,}"
                                
                                fact_text = (
                                    f"📝 <b>پیش‌فاکتور و اطلاعات پرداخت:</b>\n\n"
                                    f"🔹 <b>سرویس:</b> {plan_info['title']}\n"
                                    f"🔹 <b>تعداد:</b> {count} عدد\n"
                                    f"🏷 <b>نام دلخواه سرور:</b> {text}\n"
                                    f"💳 <b>مبلغ قابل پرداخت:</b> {session['total_price_str']} تومان\n\n"
                                    f"━━━━━━━━━━━━━━━━━━\n"
                                    f"👤 <b>نام صاحب حساب:</b> {CARD_NAME}\n"
                                    f"🔢 <b>شماره کارت:</b>\n<code>{CARD_NUMBER}</code>\n"
                                    f"<i>(روی شماره کارت بزنید تا کپی شود)</i>\n"
                                    f"━━━━━━━━━━━━━━━━━━\n\n"
                                    f"📸 <b>لطفاً پس از واریز، تصویر فیش واریزی را همین‌جا ارسال فرمایید.</b>"
                                )
                                send_msg(chat_id, fact_text)

                            elif user_sessions.get(chat_id, {}).get("step") == "admin_sending_config":
                                target_user_id = user_sessions[chat_id]["target_user"]
                                order_id = user_sessions[chat_id]["order_id"]
                                order = orders_db.get(order_id)
                                
                                if order:
                                    order["config"] = text
                                    if target_user_id in users_db:
                                        users_db[target_user_id]["purchased_services"].append({
                                            "title": order["plan"],
                                            "count": order["count"],
                                            "server_name": order["server_name"],
                                            "config": text,
                                            "date": order["date"]
                                        })

                                client_msg = (
                                    f"🎉 <b>سفارش شما با موفقیت فعال شد!</b>\n\n"
                                    f"💎 <b>اطلاعات اتصال و کانفیگ اختصاصی شما:</b>\n\n"
                                    f"<code>{text}</code>\n\n"
                                    f"✨ <i>این سرویس در بخش «💼 سرویس‌های من» ذخیره گردید.</i>\n"
                                    f"🙏 <b>از اعتماد و انتخاب شما صمیمانه سپاسگزاریم — فروشگاه آذین</b>"
                                )
                                send_msg(target_user_id, client_msg)
                                send_msg(chat_id, f"✅ سرور سفارش #{order_id} با موفقیت تحویل داده شد و در پرونده مشتری ثبت گردید.")
                                user_sessions[chat_id] = {}

                        elif "photo" in msg and user_sessions.get(chat_id, {}).get("step") == "wait_for_receipt":
                            photo_id = msg["photo"][-1]["file_id"]
                            session = user_sessions[chat_id]
                            plan_info = PLANS[session["plan_key"]]
                            
                            order_id = str(int(time.time()))
                            order_date = time.strftime("%Y-%m-%d %H:%M")
                            
                            # ثبت مجزای سفارش در دیتابیس جامع
                            orders_db[order_id] = {
                                "order_id": order_id,
                                "user_id": chat_id,
                                "first_name": first_name,
                                "username": username,
                                "plan": plan_info['title'],
                                "count": session['count'],
                                "server_name": session['server_name'],
                                "price": session['total_price_str'],
                                "price_num": session['total_price_num'],
                                "date": order_date,
                                "status": "Pending",
                                "config": "در انتظار تحویل"
                            }
                            stats_db["total_orders"] += 1
                            stats_db["pending_orders"] += 1

                            send_msg(chat_id, "💌 <b>فیش واریزی شما دریافت شد!</b>\n\nدرخواست شما برای ادمین ارسال گردید و پس از تایید سریعاً سرویس تحویل شما می‌شود. از شکیبایی شما سپاسگزاریم.🌹")

                            admin_caption = (
                                f"📥 <b>ثبت سفارش جدید (کد: #{order_id})</b>\n\n"
                                f"👤 <b>مشتری:</b> {first_name} (@{username})\n"
                                f"🆔 <b>آیدی عددی:</b> <code>{chat_id}</code>\n"
                                f"📅 <b>تاریخ ثبت:</b> {order_date}\n"
                                f"🔹 <b>سرویس:</b> {plan_info['title']}\n"
                                f"🔢 <b>تعداد:</b> {session['count']} عدد\n"
                                f"🏷 <b>نام سرور:</b> {session['server_name']}\n"
                                f"💰 <b>مبلغ:</b> {session['total_price_str']} تومان"
                            )
                            admin_kb = {
                                "inline_keyboard": [
                                    [
                                        {"text": "✅ تایید پرداخت و ارسال", "callback_data": f"approve_{order_id}"},
                                        {"text": "❌ رد پرداخت", "callback_data": f"reject_{order_id}"}
                                    ]
                                ]
                            }
                            send_photo(ADMIN_ID, photo_id, admin_caption, admin_kb)
                            user_sessions[chat_id] = {}

                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        cb_id = cb["id"]
                        chat_id = cb["message"]["chat"]["id"]
                        message_id = cb["message"]["message_id"]
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
                                    [{"text": "🔙 بازگشت به منو", "callback_data": "back_home"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, "🛒 <b>لطفاً دسته‌بندی سرویس مورد نظر خود را انتخاب کنید:</b>", buy_keyboard)

                        elif data_key == "cat_multi":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": f"۱۰ گیگ (۳۰ روزه) - {PLANS['multi_10g']['price']} تومان", "callback_data": "plan_multi_10g"}],
                                    [{"text": f"۲۰ گیگ (۳۰ روزه) - {PLANS['multi_20g']['price']} تومان", "callback_data": "plan_multi_20g"}],
                                    [{"text": f"۵۰ گیگ (۳۰ روزه) - {PLANS['multi_50g']['price']} تومان", "callback_data": "plan_multi_50g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, "🌐 <b>پلن‌های مولتی لوکیشن (۳ کاربره):</b>", kb)

                        elif data_key == "cat_melli":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": f"۱۰ گیگ (۳۰ روزه) - {PLANS['melli_10g']['price']} تومان", "callback_data": "plan_melli_10g"}],
                                    [{"text": f"۳۰ گیگ (۳۰ روزه) - {PLANS['melli_30g']['price']} تومان", "callback_data": "plan_melli_30g"}],
                                    [{"text": f"۵۰ گیگ (۳۰ روزه) - {PLANS['melli_50g']['price']} تومان", "callback_data": "plan_melli_50g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, "🇮🇷 <b>پلن‌های ملی شکن (۲ کاربره):</b>", kb)

                        elif data_key == "cat_melli_unlim":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": f"۳۰ گیگ تایم نامحدود - {PLANS['melli_unlim_30g']['price']} تومان", "callback_data": "plan_melli_unlim_30g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, "♾️ <b>پلن ملی شکن بدون محدودیت زمانی:</b>", kb)

                        elif data_key == "cat_multi_unlim":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": f"۱۰۰ گیگ تایم نامحدود - {PLANS['multi_unlim_100g']['price']} تومان", "callback_data": "plan_multi_unlim_100g"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, "🌐 <b>پلن مولتی لوکیشن بدون محدودیت زمانی:</b>", kb)

                        elif data_key == "cat_germany":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": f"حجم نامحدود (۳۰ روزه) - {PLANS['germany_30d']['price']} تومان", "callback_data": "plan_germany_30d"}],
                                    [{"text": "🔙 بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, "🇩🇪 <b>پلن اختصاصی آلمان (تک کاربره):</b>", kb)

                        elif data_key.startswith("plan_"):
                            plan_key = data_key.replace("plan_", "")
                            user_sessions[chat_id] = {"plan_key": plan_key}
                            plan_info = PLANS[plan_key]

                            text = (
                                f"📌 <b>مشخصات سرویس انتخاب شده:</b>\n\n"
                                f"💎 <b>پلن:</b> {plan_info['title']}\n"
                                f"💰 <b>قیمت:</b> {plan_info['price']} تومان\n\n"
                                f"❓ <i>آیا قصد تایید و ادامه فرآیند خرید را دارید؟</i>"
                            )
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "✅ تایید و ادامه خرید", "callback_data": "confirm_plan"}],
                                    [{"text": "🔙 انصراف و بازگشت", "callback_data": "buy_service"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, text, kb)

                        elif data_key == "confirm_plan":
                            kb = {
                                "inline_keyboard": [
                                    [{"text": "1️⃣", "callback_data": "count_1"}, {"text": "2️⃣", "callback_data": "count_2"}, {"text": "3️⃣", "callback_data": "count_3"}],
                                    [{"text": "4️⃣", "callback_data": "count_4"}, {"text": "5️⃣", "callback_data": "count_5"}],
                                    [{"text": "🔙 انصراف", "callback_data": "buy_service"}]
                                ]
                            }
                            edit_msg(chat_id, message_id, "🔢 <b>لطفاً تعداد سرویس مورد نیاز خود را انتخاب کنید:</b>", kb)

                        elif data_key.startswith("count_"):
                            count = int(data_key.split("_")[1])
                            user_sessions[chat_id]["count"] = count
                            user_sessions[chat_id]["step"] = "wait_for_name"
                            
                            send_msg(chat_id, "✍️ <b>لطفاً یک نام دلخواه برای سرور خود ارسال کنید:</b>\n<i>(مثال: Phone-Ali یا Vpn-1)</i>")

                        elif data_key == "apps":
                            apps_text = (
                                f"📲 <b>دانلود و دریافت نرم‌افزارهای اتصال:</b>\n\n"
                                f"برای دریافت جدیدترین نسخه نرم‌افزارهای اتصال (مخصوص اندروید، آیفون، ویندوز و مک) لطفاً به مدیر ربات پیام دهید:\n\n"
                                f"🆔 <b>ارتباط با مدیر:</b> {SUPPORT_USERNAME}"
                            )
                            kb = {"inline_keyboard": [[{"text": "💬 پیام به مدیر ربات", "url": f"https://t.me/Brn_Az"}, {"text": "🔙 بازگشت", "callback_data": "back_home"}]]}
                            edit_msg(chat_id, message_id, apps_text, kb)

                        elif data_key == "account":
                            user_info = users_db.get(chat_id, {"first_name": "کاربر", "username": "ندارد", "join_date": "نامشخص", "purchased_services": []})
                            acc_text = (
                                f"👤 <b>پروفایل حساب کاربری شما:</b>\n\n"
                                f"▫️ <b>نام:</b> {user_info['first_name']}\n"
                                f"▫️ <b>نام کاربری:</b> @{user_info['username']}\n"
                                f"▫️ <b>شناسه عددی:</b> <code>{chat_id}</code>\n"
                                f"▫️ <b>تاریخ عضویت:</b> {user_info['join_date']}\n"
                                f"🛍 <b>مجموع خریدهای موفق:</b> {len(user_info['purchased_services'])} عدد\n\n"
                                f"🌹 <i>از همراهی و اعتماد شما سپاسگزاریم.</i>"
                            )
                            kb = {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_home"}]]}
                            edit_msg(chat_id, message_id, acc_text, kb)

                        elif data_key == "my_services":
                            user_info = users_db.get(chat_id, {"purchased_services": []})
                            services = user_info["purchased_services"]
                            
                            if not services:
                                edit_msg(chat_id, message_id, "💼 <b>شما هنوز هیچ سرویس فعالی خریداری نکرده‌اید.</b>", {"inline_keyboard": [[{"text": "🛒 خرید سرویس جدید", "callback_data": "buy_service"}, {"text": "🔙 بازگشت", "callback_data": "back_home"}]]})
                            else:
                                s_text = "💼 <b>سرویس‌های فعال و خریداری شده شما:</b>\n\n"
                                for idx, s in enumerate(services, 1):
                                    s_text += (
                                        f"<b>{idx}. {s['title']}</b>\n"
                                        f"🏷 نام سرور: {s['server_name']}\n"
                                        f"📅 تاریخ خرید: {s['date']}\n"
                                        f"🔑 <code>{s['config']}</code>\n\n"
                                    )
                                edit_msg(chat_id, message_id, s_text, {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "back_home"}]]})

                        elif data_key.startswith("approve_"):
                            order_id = data_key.split("_")[1]
                            order = orders_db.get(order_id)
                            if order:
                                order["status"] = "Approved"
                                stats_db["pending_orders"] -= 1
                                stats_db["approved_orders"] += 1
                                stats_db["total_income"] += order["price_num"]
                                
                                user_sessions[chat_id] = {
                                    "step": "admin_sending_config",
                                    "target_user": order["user_id"],
                                    "order_id": order_id
                                }
                                send_msg(chat_id, f"✅ سفارش #{order_id} برای خریدار ({order['first_name']}) تایید شد.\n\nلطفاً کانفیگ سرور را ارسال نمایید تا به دستش برسد:")

                        elif data_key.startswith("reject_"):
                            order_id = data_key.split("_")[1]
                            order = orders_db.get(order_id)
                            if order:
                                order["status"] = "Rejected"
                                stats_db["pending_orders"] -= 1
                                stats_db["rejected_orders"] += 1
                                
                                send_msg(order["user_id"], "❌ <b>پرداخت شما تایید نشد.</b>\nدر صورت وجود هرگونه خطا یا ابهام لطفاً به پشتیبانی پیام دهید.")
                                send_msg(chat_id, f"❌ سفارش #{order_id} رد شد.")

                        elif data_key == "admin_panel" and chat_id == ADMIN_ID:
                            show_admin_panel(chat_id, message_id)

                        elif data_key == "admin_manage_plans" and chat_id == ADMIN_ID:
                            buttons = []
                            for p_key, p_val in PLANS.items():
                                buttons.append([{"text": f"{p_val['title']} ({p_val['price']} ت)", "callback_data": f"editplan_{p_key}"}])
                            buttons.append([{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}])
                            
                            edit_msg(chat_id, message_id, "💰 <b>لطفاً پلنی که قصد تغییر قیمت آن را دارید انتخاب کنید:</b>", {"inline_keyboard": buttons})

                        elif data_key.startswith("editplan_") and chat_id == ADMIN_ID:
                            p_key = data_key.replace("editplan_", "")
                            user_sessions[chat_id] = {
                                "step": "admin_changing_price",
                                "target_plan": p_key
                            }
                            send_msg(chat_id, f"✍️ <b>قیمت جدید را برای پلن زیر به «تومان» وارد کنید:</b>\n\n🔹 {PLANS[p_key]['title']}\n💵 قیمت فعلی: {PLANS[p_key]['price']} تومان")

                        elif data_key == "admin_sold_list" and chat_id == ADMIN_ID:
                            if not orders_db:
                                edit_msg(chat_id, message_id, "📭 هیچ سفارشی تاکنون در سیستم ثبت نشده است.", {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]]})
                            else:
                                list_text = "📋 <b>لیست تفکیک‌شده تمامی سفارشات ثبت شده:</b>\n\n"
                                for oid, o in orders_db.items():
                                    status_str = "⏳ در انتظار بررسی" if o['status'] == "Pending" else ("✅ تایید و تحویل شده" if o['status'] == "Approved" else "❌ رد شده")
                                    list_text += (
                                        f"📌 <b>سفارش شماره #{oid}</b>\n"
                                        f"👤 خریدار: {o['first_name']} (@{o['username']})\n"
                                        f"🆔 شناسه: <code>{o['user_id']}</code>\n"
                                        f"📅 تاریخ ثبت: {o['date']}\n"
                                        f"🔹 نوع سرویس: {o['plan']}\n"
                                        f"🔢 تعداد: {o['count']} عدد | نام سرور: {o['server_name']}\n"
                                        f"💰 مبلغ پرداختی: {o['price']} تومان\n"
                                        f"⚙️ وضعیت: {status_str}\n"
                                        f"──────────────────────────\n"
                                    )
                                edit_msg(chat_id, message_id, list_text, {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]]})

                        elif data_key == "back_home":
                            user_sessions[chat_id] = {}
                            edit_msg(chat_id, message_id, "🏠 <b>منوی اصلی:</b>", get_main_keyboard(chat_id))

                        elif data_key == "support":
                            send_msg(chat_id, f"💬 <b>پشتیبانی فروشگاه آذین:</b>\n\nآیدی ارتباط مستقیم با مدیر:\n🆔 {SUPPORT_USERNAME}")

        except Exception as e:
            print(f"Bot Error: {e}")
            time.sleep(3)

def show_admin_panel(chat_id, message_id=None):
    admin_text = (
        f"⚙️ <b>پنل مدیریت پیشرفته فروشگاه آذین</b>\n\n"
        f"📊 <b>آمار کل فروشگاه:</b>\n"
        f"▫️ کل سفارشات ثبت‌شده: {stats_db['total_orders']}\n"
        f"⏳ در انتظار بررسی: {stats_db['pending_orders']}\n"
        f"✅ موفق و تحویل شده: {stats_db['approved_orders']}\n"
        f"❌ رد شده: {stats_db['rejected_orders']}\n"
        f"💵 مجموع درآمد کل: {stats_db['total_income']:,} تومان\n"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "💰 مدیریت و تغییر قیمت پلن‌ها", "callback_data": "admin_manage_plans"}],
            [{"text": "📋 لیست جزئیات تمامی سفارشات", "callback_data": "admin_sold_list"}],
            [{"text": "🔄 بروزرسانی آمار", "callback_data": "admin_panel"}],
            [{"text": "🏠 منوی اصلی ربات", "callback_data": "back_home"}]
        ]
    }
    if message_id:
        edit_msg(chat_id, message_id, admin_text, kb)
    else:
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
