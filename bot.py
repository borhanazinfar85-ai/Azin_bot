import os
import requests
from aiohttp import web
import threading
import time

# ------------------ تنظیمات اصلی ------------------
TOKEN = "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4"
ADMIN_ID = 5992998183  # <--- آیدی عددی تلگرام خودتان
CARD_NUMBER = "5859831873943517"
CARD_NAME = "برهان آذین فر"
SUPPORT_USERNAME = "@Brn_Az"

URL = f"https://api.telegram.org/bot{TOKEN}"

# دیتابیس‌های پیشرفته
user_sessions = {}
orders_db = {}     # ذخیره جزئیات سفارشات
users_db = {}      # ذخیره اطلاعات پروفایل کاربران (تاریخ عضویت، نام و...)
stats_db = {
    "total_orders": 0,
    "pending_orders": 0,
    "approved_orders": 0,
    "rejected_orders": 0,
    "total_income": 0
}

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
        {"command": "start", "description": "شروع و منوی اصلی"},
        {"command": "admin", "description": "پنل مدیریت پیشرفته (ادمین)"},
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
                        
                        # ثبت پروفایل کاربر اگر جدید باشد
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
                                send_msg(chat_id, f"⭐ به فروشگاه آذین خوش آمدید، {first_name} عزیز ⭐\n\n🌟 پشتیبانی ۲۴/۷\n🌟 پایداری و سرعت فوق العاده\n\nاز منوی زیر بخش مورد نظر خود را انتخاب کنید.", get_main_keyboard(user_id))

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
                                total_price = plan_info["numeric_price"] * count
                                session["total_price_num"] = total_price
                                session["total_price_str"] = f"{total_price:,}"
                                
                                fact_text = (
                                    f"📋 <b>فاکتور نهایی سفارش:</b>\n\n"
                                    f"🔹 <b>سرویس:</b> {plan_info['title']}\n"
                                    f"🔹 <b>تعداد:</b> {count} عدد\n"
                                    f"🔹 <b>نام سرور:</b> {text}\n"
                                    f"💰 <b>مبلغ قابل پرداخت:</b> {session['total_price_str']} تومان\n\n"
                                    f"💳 <b>اطلاعات کارت:</b>\n"
                                    f"👤 به نام: {CARD_NAME}\n"
                                    f"<code>{CARD_NUMBER}</code> (لمس برای کپی)\n\n"
                                    f"📸 <b>لطفاً عکس فیش واریزی خود را همینجا ارسال کنید.</b>"
                                )
                                send_msg(chat_id, fact_text)

                            # ادمین در حال ارسال کانفیگ به مشتری
                            elif user_sessions.get(chat_id, {}).get("step") == "admin_sending_config":
                                target_user_id = user_sessions[chat_id]["target_user"]
                                order_id = user_sessions[chat_id]["order_id"]
                                order = orders_db.get(order_id)
                                
                                if order:
                                    order["config"] = text
                                    # اضافه کردن به لیست سرویس‌های مشتری
                                    if target_user_id in users_db:
                                        users_db[target_user_id]["purchased_services"].append({
                                            "title": order["plan"],
                                            "count": order["count"],
                                            "server_name": order["server_name"],
                                            "config": text,
                                            "date": time.strftime("%Y-%m-%d %H:%M")
                                        })

                                # ارسال سرور به مشتری
                                client_msg = (
                                    f"🎉 <b>سفارش شما تایید و فعال شد!</b>\n\n"
                                    f"🔑 <b>کانفیگ/سرور اختصاصی شما:</b>\n"
                                    f"<code>{text}</code>\n\n"
                                    f"ℹ️ هم‌اکنون این سرویس در بخش «سرویس‌های من» در ربات قابل مشاهده است.\n"
                                    f"با تشکر از خرید شما - فروشگاه آذین"
                                )
                                send_msg(target_user_id, client_msg)
                                send_msg(chat_id, f"✅ سرور با موفقیت برای مشتری ارسال شد و در پروفایل او ذخیره گردید.")
                                user_sessions[chat_id] = {}

                        # دریافت فیش واریزی از مشتری
                        elif "photo" in msg and user_sessions.get(chat_id, {}).get("step") == "wait_for_receipt":
                            photo_id = msg["photo"][-1]["file_id"]
                            session = user_sessions[chat_id]
                            plan_info = PLANS[session["plan_key"]]
                            
                            order_id = str(int(time.time()))
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
                                "date": time.strftime("%Y-%m-%d %H:%M"),
                                "status": "Pending",
                                "config": "هنوز ارسال نشده"
                            }
                            stats_db["total_orders"] += 1
                            stats_db["pending_orders"] += 1

                            send_msg(chat_id, "✅ فیش شما ثبت شد و برای ادمین ارسال گردید.\nبه محض تایید، کانفیگ شما ارسال و در «سرویس‌های من» ذخیره می‌شود.")

                            admin_caption = (
                                f"📥 <b>سفارش جدید دریافت شد!</b>\n\n"
                                f"🆔 <b>آیدی عددی:</b> <code>{chat_id}</code>\n"
                                f"👤 <b>نام کاربر:</b> {first_name} (@{username})\n"
                                f"🔹 <b>سرویس:</b> {plan_info['title']}\n"
                                f"🔹 <b>تعداد:</b> {session['count']}\n"
                                f"🔹 <b>نام سرور:</b> {session['server_name']}\n"
                                f"💰 <b>مبلغ:</b> {session['total_price_str']} تومان\n"
                                f"🆔 <b>کد سفارش:</b> #{order_id}"
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

                    # ------------------ مدیریت کلیک‌ها ------------------
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

                        # بخش حساب کاربری اختصاصی
                        elif data_key == "account":
                            user_info = users_db.get(chat_id, {"first_name": "کاربر", "username": "ندارد", "join_date": "نامشخص", "purchased_services": []})
                            acc_text = (
                                f"👤 <b>اطلاعات حساب کاربری شما:</b>\n\n"
                                f"📌 <b>نام:</b> {user_info['first_name']}\n"
                                f"🆔 <b>آیدی تلگرام:</b> @{user_info['username']}\n"
                                f"🔢 <b>آیدی عددی:</b> <code>{chat_id}</code>\n"
                                f"📅 <b>تاریخ عضویت در ربات:</b> {user_info['join_date']}\n"
                                f"🛍 <b>تعداد کل خریدها:</b> {len(user_info['purchased_services'])} سرویس\n\n"
                                f"🌟 از اینکه فروشگاه آذین را انتخاب کردید متشکریم."
                            )
                            kb = {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_home"}]]}
                            send_msg(chat_id, acc_text, kb)

                        # بخش سرویس‌های من (نمایش کانفیگ‌های خریداری شده)
                        elif data_key == "my_services":
                            user_info = users_db.get(chat_id, {"purchased_services": []})
                            services = user_info["purchased_services"]
                            
                            if not services:
                                send_msg(chat_id, "💼 شما هنوز هیچ سرویس فعالی خریداری نکرده‌اید.", {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "back_home"}]]})
                            else:
                                s_text = "💼 <b>سرویس‌های فعال و خریداری شده شما:</b>\n\n"
                                for idx, s in enumerate(services, 1):
                                    s_text += (
                                        f"<b>{idx}. {s['title']}</b>\n"
                                        f"▫️ تعداد: {s['count']}\n"
                                        f"▫️ نام سرور: {s['server_name']}\n"
                                        f"▫️ تاریخ خرید: {s['date']}\n"
                                        f"🔑 <code>{s['config']}</code>\n\n"
                                    )
                                send_msg(chat_id, s_text, {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "back_home"}]]})

                        # عملیات تایید سفارش توسط ادمین
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
                                send_msg(chat_id, f"✅ سفارش #{order_id} تایید شد.\n\nلطفاً لینک یا کانفیگ سرور را ارسال کنید تا برای مشتری ارسال و در حسابش ذخیره شود:")

                        elif data_key.startswith("reject_"):
                            order_id = data_key.split("_")[1]
                            order = orders_db.get(order_id)
                            if order:
                                order["status"] = "Rejected"
                                stats_db["pending_orders"] -= 1
                                stats_db["rejected_orders"] += 1
                                
                                send_msg(order["user_id"], "❌ پرداخت شما تایید نشد. در صورت وجود مشکل با پشتیبانی در ارتباط باشید.")
                                send_msg(chat_id, f"❌ سفارش #{order_id} رد شد و به مشتری اطلاع داده شد.")

                        elif data_key == "admin_panel" and chat_id == ADMIN_ID:
                            show_admin_panel(chat_id)

                        elif data_key == "admin_sold_list" and chat_id == ADMIN_ID:
                            # نمایش لیست کامل فروش‌ها
                            if not orders_db:
                                send_msg(chat_id, "📭 هیچ سفارشی تاکنون ثبت نشده است.", {"inline_keyboard": [[{"text": "🔙 بازگشت به پنل", "callback_data": "admin_panel"}]]})
                            else:
                                list_text = "📋 <b>لیست کامل سرویس‌های فروخته شده:</b>\n\n"
                                for oid, o in orders_db.items():
                                    status_emoji = "⏳" if o['status'] == "Pending" else ("✅" if o['status'] == "Approved" else "❌")
                                    list_text += (
                                        f"{status_emoji} <b>سفارش #{oid}</b>\n"
                                        f"👤 خریدار: {o['first_name']} (@{o['username']})\n"
                                        f"🆔 آیدی: <code>{o['user_id']}</code>\n"
                                        f"🔹 سرویس: {o['plan']}\n"
                                        f"🔢 تعداد: {o['count']} | نام سرور: {o['server_name']}\n"
                                        f"💰 مبلغ: {o['price']} تومان\n"
                                        f"📅 تاریخ: {o['date']}\n"
                                        f"-----------------------------------\n"
                                    )
                                send_msg(chat_id, list_text, {"inline_keyboard": [[{"text": "🔙 بازگشت به پنل", "callback_data": "admin_panel"}]]})

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
        f"⚙️ <b>پنل مدیریت پیشرفته فروشگاه آذین</b>\n\n"
        f"📊 <b>آمار کل فروشگاه:</b>\n"
        f"▫️ کل سفارش‌های ثبت شده: {stats_db['total_orders']}\n"
        f"⏳ در انتظار بررسی و تایید: {stats_db['pending_orders']}\n"
        f"✅ تایید و واگذار شده: {stats_db['approved_orders']}\n"
        f"❌ رد شده: {stats_db['rejected_orders']}\n"
        f"💵 مجموع درآمد کل: {stats_db['total_income']:,} تومان\n"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "📋 مشاهده لیست سرویس‌های فروخته شده", "callback_data": "admin_sold_list"}],
            [{"text": "🔄 بروزرسانی آمار", "callback_data": "admin_panel"}],
            [{"text": "🏠 منوی اصلی ربات", "callback_data": "back_home"}]
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
