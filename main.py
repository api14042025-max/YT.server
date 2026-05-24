from flask import Flask, request, jsonify
from threading import Thread
import requests
import json
import time
import sqlite3
from datetime import datetime, timedelta

# تنظیمات ربات بله
BOT_TOKEN = "223436980:DgvOTxkcPkrDmEk6Y4qefsQ30MuitGIwvbQ"
OWNER_ID = 1828182856
API_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

app = Flask(__name__)

# راه‌اندازی دیتابیس
conn = sqlite3.connect('bot_data.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    phone TEXT PRIMARY KEY,
    code TEXT,
    verified INTEGER DEFAULT 0,
    request_time TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS pending_codes (
    phone TEXT PRIMARY KEY,
    code TEXT,
    time TEXT
)
''')

conn.commit()

def send_message(chat_id, text):
    """ارسال پیام به کاربر در بله"""
    try:
        url = f"{API_URL}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"خطا در ارسال پیام: {e}")
        return None

def send_callback(chat_id, text, callback_data):
    """ارسال پیام با دکمه شیشه‌ای"""
    try:
        url = f"{API_URL}/sendMessage"
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": text, "callback_data": callback_data}
                ]
            ]
        }
        payload = {
            "chat_id": chat_id,
            "text": "لطفاً انتخاب کنید:",
            "reply_markup": keyboard
        }
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        print(f"خطا: {e}")
        return None

def get_updates(offset=None):
    """دریافت پیام‌های جدید"""
    try:
        url = f"{API_URL}/getUpdates"
        params = {}
        if offset:
            params["offset"] = offset
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        print(f"خطا در دریافت آپدیت: {e}")
        return None

def save_pending_code(phone, code):
    """ذخیره کد در انتظار برای کاربر"""
    cursor.execute("INSERT OR REPLACE INTO pending_codes (phone, code, time) VALUES (?, ?, ?)",
                   (phone, code, datetime.now().isoformat()))
    conn.commit()

def get_pending_code(phone):
    """دریافت کد ذخیره شده برای کاربر"""
    cursor.execute("SELECT code FROM pending_codes WHERE phone = ?", (phone,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None

def delete_pending_code(phone):
    """حذف کد بعد از استفاده"""
    cursor.execute("DELETE FROM pending_codes WHERE phone = ?", (phone,))
    conn.commit()

# ========== پردازش دستورات ==========

def process_command(chat_id, text):
    if chat_id != OWNER_ID:
        # پیام از کاربر عادی
        send_message(OWNER_ID, f"💬 پیام از کاربر {chat_id}:\n{text}")
        send_message(chat_id, "✅ پیام شما به پشتیبان ارسال شد")
        return
    
    # دستورات ادمین
    if text == "/start":
        help_text = """
💀 ربات مدیریت پنل فعال شد 💀

📋 دستورات:
/send [شماره] [کد] - ارسال کد تایید
/users - لیست کاربران
/help - راهنما
        """
        send_message(chat_id, help_text)
    
    elif text.startswith("/send"):
        try:
            parts = text.split()
            if len(parts) < 3:
                send_message(chat_id, "❌ فرمت صحیح:\n/send 09123456789 123456")
                return
            
            phone = parts[1]
            code = parts[2]
            
            # ذخیره کد
            save_pending_code(phone, code)
            send_message(chat_id, f"✅ کد {code} برای شماره {phone} ذخیره شد")
            
        except Exception as e:
            send_message(chat_id, f"❌ خطا: {str(e)}")
    
    elif text == "/users":
        cursor.execute("SELECT phone, verified FROM users")
        users = cursor.fetchall()
        if not users:
            send_message(chat_id, "📭 هیچ کاربری ثبت نشده")
            return
        msg = "👥 لیست کاربران:\n━━━━━━━━━━━━━━━━━━━━\n"
        for user in users:
            status = "✅ تایید" if user[1] else "⏳ در انتظار"
            msg += f"📱 {user[0]} - {status}\n"
        send_message(chat_id, msg)
    
    elif text == "/help":
        help_text = """
📟 راهنمای ربات مدیریت

/send [شماره] [کد] - ارسال کد تایید
/users - نمایش کاربران
/clear - پاک کردن همه داده‌ها
        """
        send_message(chat_id, help_text)
    
    elif text == "/clear":
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM pending_codes")
        conn.commit()
        send_message(chat_id, "✅ همه داده‌ها پاک شد")

def process_callback(chat_id, data):
    """پردازش کلیک روی دکمه شیشه‌ای"""
    if data.startswith("verify_"):
        phone = data.replace("verify_", "")
        code = get_pending_code(phone)
        if code:
            # در اینجا میتونی کد رو به کاربر نمایش بدی
            send_message(chat_id, f"🔑 کد تایید برای {phone}: {code}")
        else:
            send_message(chat_id, f"❌ کدی برای {phone} یافت نشد")

def run_bot():
    """حلقه اصلی ربات"""
    last_update_id = 0
    print("🤖 ربات بله روشن شد...")
    
    while True:
        try:
            response = get_updates(last_update_id + 1)
            
            if response and response.get("ok"):
                for update in response.get("result", []):
                    update_id = update.get("update_id")
                    if update_id:
                        last_update_id = update_id
                    
                    # پیام متنی
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        if "text" in msg:
                            process_command(chat_id, msg["text"])
                    
                    # کلیک روی دکمه
                    if "callback_query" in update:
                        cb = update["callback_query"]
                        chat_id = cb["message"]["chat"]["id"]
                        data = cb.get("data", "")
                        process_callback(chat_id, data)
                        
                        # پاسخ به callback
                        try:
                            answer_url = f"{API_URL}/answerCallbackQuery"
                            requests.post(answer_url, json={"callback_query_id": cb["id"]})
                        except:
                            pass
            
            time.sleep(1)
            
        except Exception as e:
            print(f"خطا در حلقه اصلی: {e}")
            time.sleep(5)

# ========== روت Flask برای نگه داشتن ربات در Render ==========
@app.route('/')
def home():
    return "ربات بله فعال است!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if data:
        if "message" in data:
            chat_id = data["message"]["chat"]["id"]
            if "text" in data["message"]:
                process_command(chat_id, data["message"]["text"])
        if "callback_query" in data:
            chat_id = data["callback_query"]["message"]["chat"]["id"]
            data_cb = data["callback_query"].get("data", "")
            process_callback(chat_id, data_cb)
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    # اجرای ربات در یک ترد جداگانه
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    # اجرای فلاسک برای جلوگیری از خاموش شدن
    port = 5000
    app.run(host='0.0.0.0', port=port)
