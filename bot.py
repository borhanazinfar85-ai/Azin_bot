import os
import psycopg2
from urllib.parse import urlparse
import requests
from aiohttp import web
import threading
import time

# ------------------ دریافت اطلاعات حساس از سرور ------------------
TOKEN = os.environ.get("BOT_TOKEN", "8799172276:AAFxRorT4KCwi4QrXHbusSrzPPaC-8fowY4")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "5992998183"))
DATABASE_URL = "postgresql://postgres.jxvnlwocfqrqjoarifty:Borhan27555@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"
DEFAULT_CARD_NUMBER = os.environ.get("CARD_NUMBER", "5859831873943517")
DEFAULT_CARD_NAME = "برهان آذین فر"
SUPPORT_USERNAME = "@Brn_Az"
RENDER_URL = os.environ.get("https://azin-bot.onrender.com")  # آدرس وب‌سرویس رندر برای پینگ خودکار

URL = f"https://api.telegram.org/bot{TOKEN}"

# ------------------ پینگر خودکار برای بیدار نگه داشتن سرور ------------------
def keep_alive():
    if not RENDER_URL:
        print("متغیر RENDER_EXTERNAL_URL تعریف نشده است؛ پینگر خودکار فعال نشد.")
        return
    while True:
        try:
            time.sleep(600)  # هر ۱۰ دقیقه (۶۰۰ ثانیه)
            response = requests.get(RENDER_URL)
            print(f"Self-ping sent to {RENDER_URL} | Status: {response.status_code}")
        except Exception as e:
            print(f"Self-ping failed: {e}")

# ------------------ اتصال به دیتابیس ابری Supabase ------------------
def get_db_connection():
    parsed_url = urlparse(DATABASE_URL)
    conn = psycopg2.connect(
        database=parsed_url.path[1:],
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port,
        sslmode='require'
    )
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # جدول کاربران
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            join_date TEXT
        )
    ''')
    
    # جدول سفارشات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            user_id BIGINT,
            first_name TEXT,
            username TEXT,
            plan TEXT,
            count INTEGER,
            server_name TEXT,
            price TEXT,
            price_num INTEGER,
            date TEXT,
            status TEXT,
            config TEXT
        )
    ''')
    
    # جدول قیمت پلن‌ها
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS plans (
            plan_key TEXT PRIMARY KEY,
            title TEXT,
            price TEXT,
            numeric_price INTEGER
        )
    ''')

    # جدول اطلاعات کارت بانکی
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS card_info (
            id INTEGER PRIMARY KEY,
            card_number TEXT,
            card_name TEXT
        )
    ''')
    
    # ثبت پیش‌فرض پلن‌ها
    default_plans = [
        ("multi_10g", "مولتی لوکیشن | ۱۰ گیگ - ۳۰ روزه", "60,000", 60000),
        ("multi_20g", "مولتی لوکیشن | ۲۰ گیگ - ۳۰ روزه", "110,000", 110000),
        ("multi_50g", "مولتی لوکیشن | ۵۰ گیگ - ۳۰ روزه", "200,000", 200000),
        ("melli_10g", "ملی شکن | ۱۰ گیگ - ۳۰ روزه", "70,000", 70000),
        ("melli_30g", "ملی شکن | ۳۰ گیگ - ۳۰ روزه", "120,000", 120000),
        ("melli_50g", "ملی شکن | ۵۰ گیگ - ۳۰ روزه", "210,000", 210000),
        ("melli_unlim_30g", "ملی شکن تایم نامحدود | ۳۰ گیگ", "170,000", 170000),
        ("multi_unlim_100g", "مولتی لوکیشن تایم نامحدود | ۱۰۰ گیگ", "300,000", 300000),
        ("germany_30d", "المان نامحدود | تک کاربره - ۳۰ روزه", "90,000", 90000)
    ]
    for pk, t, p, np in default_plans:
        cursor.execute("INSERT INTO plans (plan_key, title, price, numeric_price) VALUES (%s, %s, %s, %s) ON CONFLICT (plan_key) DO NOTHING", (pk, t, p, np))
        
    # ثبت پیش‌فرض شماره کارت
    cursor.execute("INSERT INTO card_info (id, card_number, card_name) VALUES (1, %s, %s) ON CONFLICT (id) DO NOTHING", 
                   (DEFAULT_CARD_NUMBER, DEFAULT_CARD_NAME))

    conn.commit()
    cursor.close()
    conn.close()

init_db()

user_sessions = {}

def get_card_info():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT card_number, card_name FROM card_info WHERE id = 1")
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return row[0], row[1]
    return DEFAULT_CARD_NUMBER, DEFAULT_CARD_NAME

def get_plans():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT plan_key, title, price, numeric_price FROM plans")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return {r[0]: {"title": r[1], "price": r[2], "numeric_price": r[3]} for r in rows}

def set_bot_commands():
    commands = [
        {"command": "start", "description": "🚀 شروع و منوی اصلی"},
        {"command": "admin", "description": "⚙️ پنل مدیریت (ادمین)"},
        {"command": "help", "description": "💬 ارتباط با پشتیبانی"}
    ]
    requests.post(f"{URL}/setMyCommands", json={"commands": commands})

def send_msg(chat_id, text, keyboard=None, parse_mode="HTML"):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if keyboard:
        payload["reply_markup"] = keyboard
    return requests.post(f"{URL}/sendMessage", json=payload)

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
    print("Telegram bot started with Supabase cloud database...")
    while True:
        try:
            response = requests.get(f"{URL}/getUpdates", params={"offset": offset, "timeout": 30})
            data = response.json()
            if data.get("ok"):
                for update in data.get("result", []):
                    offset = update["update_id"] + 1
                    PLANS = get_plans()
                    CARD_NUMBER, CARD_NAME = get_card_info()
                    
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        first_name = msg["from"].get("first_name", "کاربر")
                        username = msg["from"].get("username", "ندارد")
                        
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO users (user_id, first_name, username, join_date) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING", 
                                       (chat_id, first_name, username, time.strftime("%Y-%m-%d %H:%M")))
                        conn.commit()
                        cursor.close()
                        conn.close()

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
                                send_msg(chat_id, f"💬 <b>پشتیبانی فروشگاه آذین:</b>\n\n🆔 {SUPPORT_USERNAME}")

                            elif user_sessions.get(chat_id, {}).get("step") == "admin_changing_card":
                                try:
                                    new_card = text.replace(" ", "").replace("-", "").strip()
                                    if not new_card.isdigit() or len(new_card) != 16:
                                        send_msg(chat_id, "⚠️ شماره کارت باید ۱۶ رقم باشد. لطفاً دوباره وارد کنید:")
                                    else:
                                        conn = get_db_connection()
                                        cursor = conn.cursor()
                                        cursor.execute("UPDATE card_info SET card_number = %s WHERE id = 1", (new_card,))
                                        conn.commit()
                                        cursor.close()
                                        conn.close()
                                        
                                        send_msg(chat_id, f"✅ <b>شماره کارت جدید با موفقیت ثبت شد:</b>\n<code>{new_card}</code>")
                                        user_sessions[chat_id] = {}
                                        show_admin_panel(chat_id)
                                except Exception as e:
                                    send_msg(chat_id, f"خطا در ثبت شماره کارت: {e}")

                            elif user_sessions.get(chat_id, {}).get("step") == "admin_changing_price":
                                p_key = user_sessions[chat_id]["target_plan"]
                                try:
                                    new_price = int(text.replace(",", "").strip())
                                    conn = get_db_connection()
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE plans SET price = %s, numeric_price = %s WHERE plan_key = %s", 
                                                   (f"{new_price:,}", new_price, p_key))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                    
                                    send_msg(chat_id, f"✅ <b>قیمت پلن با موفقیت به {new_price:,} تومان تغییر یافت.</b>")
                                    user_sessions[chat_id] = {}
                                    show_admin_panel(chat_id)
                                except ValueError:
                                    send_msg(chat_id, "⚠️ لطفاً قیمت را فقط به صورت عدد وارد کنید:")

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
                                    f"━━━━━━━━━━━━━━━━━━\n\n"
                                    f"📸 <b>لطفاً پس از واریز، تصویر فیش واریزی را همین‌جا ارسال فرمایید.</b>"
                                )
                                send_msg(chat_id, fact_text)

                            elif user_sessions.get(chat_id, {}).get("step") == "admin_sending_config":
                                target_user_id = user_sessions[chat_id]["target_user"]
                                order_id = user_sessions[chat_id]["order_id"]
                                
                                conn = get_db_connection()
                                cursor = conn.cursor()
                                cursor.execute("UPDATE orders SET status = 'Approved', config = %s WHERE order_id = %s", (text, order_id))
                                conn.commit()
                                cursor.close()
                                conn.close()

                                client_msg = (
                                    f"🎉 <b>سفارش شما با موفقیت فعال شد!</b>\n\n"
                                    f"💎 <b>اطلاعات اتصال و کانفیگ اختصاصی شما:</b>\n\n"
                                    f"<code>{text}</code>\n\n"
                                    f"✨ <i>این سرویس در بخش «💼 سرویس‌های من» ذخیره گردید.</i>\n"
                                    f"🙏 <b>از انتخاب شما سپاسگزاریم — فروشگاه آذین</b>"
                                )
                                send_msg(target_user_id, client_msg)
                                send_msg(chat_id, f"✅ سرور سفارش #{order_id} تحویل و در دیتابیس ثبت گردید.")
                                user_sessions[chat_id] = {}

                        elif "photo" in msg and user_sessions.get(chat_id, {}).get("step") == "wait_for_receipt":
                            photo_id = msg["photo"][-1]["file_id"]
                            session = user_sessions[chat_id]
                            plan_info = PLANS[session["plan_key"]]
                            
                            order_id = str(int(time.time()))
                            order_date = time.strftime("%Y-%m-%d %H:%M")
                            
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO orders VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Pending', 'در انتظار تحویل')",
                                           (order_id, chat_id, first_name, username, plan_info['title'], session['count'], 
                                            session['server_name'], session['total_price_str'], session['total_price_num'], order_date))
                            conn.commit()
                            cursor.close()
                            conn.close()

                            send_msg(chat_id, "💌 <b>فیش واریزی شما دریافت شد!</b>\n\nدرخواست شما برای ادمین ارسال گردید و پس از تایید سریعاً سرویس تحویل می‌شود.🌹")

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
                                f"برای دریافت نرم‌افزارها به مدیر پیام دهید:\n🆔 <b>ارتباط با مدیر:</b> {SUPPORT_USERNAME}"
                            )
                            kb = {"inline_keyboard": [[{"text": "💬 پیام به مدیر ربات", "url": f"https://t.me/Brn_Az"}, {"text": "🔙 بازگشت", "callback_data": "back_home"}]]}
                            edit_msg(chat_id, message_id, apps_text, kb)

                        elif data_key == "account":
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT first_name, username, join_date FROM users WHERE user_id = %s", (chat_id,))
                            u = cursor.fetchone()
                            cursor.execute("SELECT COUNT(*) FROM orders WHERE user_id = %s AND status = 'Approved'", (chat_id,))
                            order_count = cursor.fetchone()[0]
                            cursor.close()
                            conn.close()

                            if u:
                                acc_text = (
                                    f"👤 <b>پروفایل حساب کاربری شما:</b>\n\n"
                                    f"▫️ <b>نام:</b> {u[0]}\n"
                                    f"▫️ <b>نام کاربری:</b> @{u[1]}\n"
                                    f"▫️ <b>شناسه عددی:</b> <code>{chat_id}</code>\n"
                                    f"▫️ <b>تاریخ عضویت:</b> {u[2]}\n"
                                    f"🛍 <b>مجموع خریدهای موفق:</b> {order_count} عدد\n\n"
                                    f"🌹 <i>از همراهی شما سپاسگزاریم.</i>"
                                )
                                kb = {"inline_keyboard": [[{"text": "🔙 بازگشت به منوی اصلی", "callback_data": "back_home"}]]}
                                edit_msg(chat_id, message_id, acc_text, kb)

                        elif data_key == "my_services":
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT plan, server_name, date, config FROM orders WHERE user_id = %s AND status = 'Approved'", (chat_id,))
                            services = cursor.fetchall()
                            cursor.close()
                            conn.close()
                            
                            if not services:
                                edit_msg(chat_id, message_id, "💼 <b>شما هنوز هیچ سرویس فعالی خریداری نکرده‌اید.</b>", {"inline_keyboard": [[{"text": "🛒 خرید سرویس جدید", "callback_data": "buy_service"}, {"text": "🔙 بازگشت", "callback_data": "back_home"}]]})
                            else:
                                s_text = "💼 <b>سرویس‌های فعال و خریداری شده شما:</b>\n\n"
                                for idx, s in enumerate(services, 1):
                                    s_text += (
                                        f"<b>{idx}. {s[0]}</b>\n"
                                        f"🏷 نام سرور: {s[1]}\n"
                                        f"📅 تاریخ خرید: {s[2]}\n"
                                        f"🔑 <code>{s[3]}</code>\n\n"
                                    )
                                edit_msg(chat_id, message_id, s_text, {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "back_home"}]]})

                        elif data_key.startswith("approve_"):
                            order_id = data_key.split("_")[1]
                            user_sessions[chat_id] = {
                                "step": "admin_sending_config",
                                "target_user": chat_id,
                                "order_id": order_id
                            }
                            
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT user_id, first_name FROM orders WHERE order_id = %s", (order_id,))
                            ord_data = cursor.fetchone()
                            cursor.close()
                            conn.close()
                            
                            if ord_data:
                                user_sessions[chat_id]["target_user"] = ord_data[0]
                                send_msg(chat_id, f"✅ سفارش #{order_id} برای ({ord_data[1]}) تایید شد.\n\nلطفاً کانفیگ سرور را ارسال نمایید:")

                        elif data_key.startswith("reject_"):
                            order_id = data_key.split("_")[1]
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("UPDATE orders SET status = 'Rejected' WHERE order_id = %s", (order_id,))
                            cursor.execute("SELECT user_id FROM orders WHERE order_id = %s", (order_id,))
                            uid = cursor.fetchone()
                            conn.commit()
                            cursor.close()
                            conn.close()
                            
                            if uid:
                                send_msg(uid[0], "❌ <b>پرداخت شما تایید نشد.</b>\nدر صورت وجود هرگونه مشکل به پشتیبانی پیام دهید.")
                            send_msg(chat_id, f"❌ سفارش #{order_id} رد شد.")

                        elif data_key == "admin_panel" and chat_id == ADMIN_ID:
                            show_admin_panel(chat_id, message_id)

                        elif data_key == "admin_manage_card" and chat_id == ADMIN_ID:
                            user_sessions[chat_id] = {"step": "admin_changing_card"}
                            c_num, c_name = get_card_info()
                            send_msg(chat_id, f"💳 <b>اطلاعات فعلی کارت:</b>\n\n👤 به نام: {c_name}\n🔢 شماره کارت: <code>{c_num}</code>\n\nلطفاً <b>شماره کارت ۱۶ رقمی جدید</b> را ارسال کنید:")

                        elif data_key == "admin_manage_plans" and chat_id == ADMIN_ID:
                            buttons = []
                            for p_key, p_val in PLANS.items():
                                buttons.append([{"text": f"{p_val['title']} ({p_val['price']} ت)", "callback_data": f"editplan_{p_key}"}])
                            buttons.append([{"text": "🔙 بازگشت به پنل ادمین", "callback_data": "admin_panel"}])
                            
                            edit_msg(chat_id, message_id, "💰 <b>پلن مورد نظر جهت تغییر قیمت را انتخاب کنید:</b>", {"inline_keyboard": buttons})

                        elif data_key.startswith("editplan_") and chat_id == ADMIN_ID:
                            p_key = data_key.replace("editplan_", "")
                            user_sessions[chat_id] = {
                                "step": "admin_changing_price",
                                "target_plan": p_key
                            }
                            send_msg(chat_id, f"✍️ <b>قیمت جدید را برای پلن زیر به «تومان» وارد کنید:</b>\n\n🔹 {PLANS[p_key]['title']}\n💵 قیمت فعلی: {PLANS[p_key]['price']} تومان")

                        elif data_key == "admin_sold_list" and chat_id == ADMIN_ID:
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            cursor.execute("SELECT order_id, first_name, username, user_id, date, plan, count, server_name, price, status FROM orders")
                            orders = cursor.fetchall()
                            cursor.close()
                            conn.close()

                            if not orders:
                                edit_msg(chat_id, message_id, "📭 هیچ سفارشی تاکنون ثبت نشده است.", {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]]})
                            else:
                                list_text = "📋 <b>لیست جامع تمام سفارشات ثبت شده:</b>\n\n"
                                for o in orders:
                                    status_str = "⏳ در انتظار بررسی" if o[9] == "Pending" else ("✅ تایید و تحویل شده" if o[9] == "Approved" else "❌ رد شده")
                                    list_text += (
                                        f"📌 <b>سفارش #{o[0]}</b>\n"
                                        f"👤 خریدار: {o[1]} (@{o[2]})\n"
                                        f"🆔 شناسه: <code>{o[3]}</code>\n"
                                        f"📅 تاریخ ثبت: {o[4]}\n"
                                        f"🔹 سرویس: {o[5]}\n"
                                        f"🔢 تعداد: {o[6]} عدد | نام سرور: {o[7]}\n"
                                        f"💰 مبلغ پرداختی: {o[8]} تومان\n"
                                        f"⚙️ وضعیت: {status_str}\n"
                                        f"──────────────────────────\n"
                                    )
                                edit_msg(chat_id, message_id, list_text, {"inline_keyboard": [[{"text": "🔙 بازگشت", "callback_data": "admin_panel"}]]})

                        elif data_key == "back_home":
                            user_sessions[chat_id] = {}
                            edit_msg(chat_id, message_id, "🏠 <b>منوی اصلی:</b>", get_main_keyboard(chat_id))

                        elif data_key == "support":
                            send_msg(chat_id, f"💬 <b>پشتیبانی فروشگاه آذین:</b>\n\n🆔 {SUPPORT_USERNAME}")

        except Exception as e:
            print(f"Bot Error: {e}")
            time.sleep(3)

def show_admin_panel(chat_id, message_id=None):
    c_num, c_name = get_card_info()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM orders")
    total_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Pending'")
    pending_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Approved'")
    approved_orders = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM orders WHERE status = 'Rejected'")
    rejected_orders = cursor.fetchone()[0]
    cursor.execute("SELECT SUM(price_num) FROM orders WHERE status = 'Approved'")
    total_income = cursor.fetchone()[0] or 0
    cursor.close()
    conn.close()

    admin_text = (
        f"⚙️ <b>پنل مدیریت پیشرفته فروشگاه آذین (Supabase)</b>\n\n"
        f"💳 <b>شماره کارت فعال:</b> <code>{c_num}</code> ({c_name})\n\n"
        f"📊 <b>آمار کل فروشگاه:</b>\n"
        f"▫️ کل سفارشات: {total_orders}\n"
        f"⏳ در انتظار بررسی: {pending_orders}\n"
        f"✅ تحویل داده شده: {approved_orders}\n"
        f"❌ رد شده: {rejected_orders}\n"
        f"💵 درآمد کل فروشگاه: {total_income:,} تومان\n"
    )
    kb = {
        "inline_keyboard": [
            [{"text": "💳 تغییر شماره کارت", "callback_data": "admin_manage_card"}],
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
    # شروع ترد اصلی ربات
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    # شروع ترد پینگر خودکار جهت بیدار نگه داشتن سرور
    ping_thread = threading.Thread(target=keep_alive, daemon=True)
    ping_thread.start()

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)
import psycopg2
# (فرض بر این است که متصل‌کننده دیتابیس و کتابخانه تلگرام پایتون از قبل تنظیم شده‌اند)

# اتصال به دیتابیس Supabase شما
DATABASE_URL = "postgresql://postgres.jxvnlwocfqrqjoarifty:Borhan27555@aws-0-eu-west-1.pooler.supabase.com:6543/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# ۱. تابع بررسی اینکه آیا کاربر بن شده است یا خیر
TGBOT_ADMIN_ID = 123456789  # آیدی تلگرامی خودت رو اینجا بزار تا فقط ادمین بتونه بن کنه

def is_user_banned(user_id: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM banned_users WHERE user_id = %s", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

# ۲. تابع دستور بن کردن (مثلا: /ban 12345678 یا ریپلای روی پیام کاربر)
# این بخش بسته به ساختار کتابخانه‌ای که استفاده می‌کنید (مثل pyTelegramBotAPI یا aiogram) پیاده می‌شود:
