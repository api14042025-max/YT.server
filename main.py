import telebot
import time
import threading
import sqlite3
from datetime import datetime, timedelta

# توکن ربات
BOT_TOKEN = "223436980:DgvOTxkcPkrDmEk6Y4qefsQ30MuitGIwvbQ"
OWNER_ID = 1828182856

# راه‌اندازی ربات
bot = telebot.TeleBot(BOT_TOKEN)

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
CREATE TABLE IF NOT EXISTS banned (
    phone TEXT PRIMARY KEY,
    ban_until TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT,
    message TEXT,
    time TEXT
)
''')

conn.commit()

# ========== دستورات ==========

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if message.chat.id == OWNER_ID:
        bot.reply_to(message, "💀 ربات مدیریت پنل فعال شد 💀\n\n📋 دستورات:\n/send [شماره] [کد] - ارسال کد\n/msg [شماره] [متن] - ارسال پیام\n/users - لیست کاربران\n/banned - لیست بن‌ها\n/ban [شماره] - بن کردن\n/unban [شماره] - رفع بن\n/stats - آمار\n/help - راهنما")

@bot.message_handler(commands=['help'])
def help_command(message):
    if message.chat.id == OWNER_ID:
        help_text = """
💀 راهنمای ربات مدیریت 💀
━━━━━━━━━━━━━━━━━━━━
/send [شماره] [کد] - ارسال کد تایید
/msg [شماره] [متن] - ارسال پیام به کاربر
/users - نمایش لیست کاربران تایید شده
/banned - نمایش لیست بن‌ها
/ban [شماره] - بن کردن کاربر
/unban [شماره] - رفع بن کاربر
/stats - آمار کلی
/clear - پاک کردن همه داده‌ها
━━━━━━━━━━━━━━━━━━━━
        """
        bot.reply_to(message, help_text)

@bot.message_handler(commands=['send'])
def send_code(message):
    if message.chat.id != OWNER_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "❌ فرمت صحیح:\n/send 09123456789 123456")
            return
        
        phone = parts[1]
        code = parts[2]
        
        if not phone.startswith('09') or len(phone) != 11:
            bot.reply_to(message, "❌ شماره نامعتبر است")
            return
        
        if len(code) != 6 or not code.isdigit():
            bot.reply_to(message, "❌ کد باید 6 رقم باشد")
            return
        
        # ذخیره کد در دیتابیس
        cursor.execute("INSERT OR REPLACE INTO users (phone, code, request_time) VALUES (?, ?, ?)", 
                       (phone, code, datetime.now().isoformat()))
        conn.commit()
        
        bot.reply_to(message, f"✅ کد {code} برای شماره {phone} ارسال شد")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.message_handler(commands=['msg'])
def send_message_to_user(message):
    if message.chat.id != OWNER_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.reply_to(message, "❌ فرمت صحیح:\n/msg 09123456789 متن پیام")
            return
        
        phone = parts[1]
        msg_text = ' '.join(parts[2:])
        
        # ذخیره پیام برای کاربر
        cursor.execute("INSERT INTO messages (phone, message, time) VALUES (?, ?, ?)",
                       (phone, msg_text, datetime.now().isoformat()))
        conn.commit()
        
        bot.reply_to(message, f"✅ پیام به {phone} ارسال شد: {msg_text}")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.message_handler(commands=['users'])
def list_users(message):
    if message.chat.id != OWNER_ID:
        return
    
    cursor.execute("SELECT phone, verified FROM users")
    users = cursor.fetchall()
    
    if not users:
        bot.reply_to(message, "📭 هیچ کاربری ثبت نشده")
        return
    
    text = "👥 لیست کاربران:\n━━━━━━━━━━━━━━━━━━━━\n"
    for user in users:
        status = "✅ تایید شده" if user[1] else "⏳ در انتظار"
        text += f"📱 {user[0]} - {status}\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['banned'])
def list_banned(message):
    if message.chat.id != OWNER_ID:
        return
    
    cursor.execute("SELECT phone, ban_until FROM banned")
    banned = cursor.fetchall()
    
    if not banned:
        bot.reply_to(message, "🚫 هیچ کاربری بن نیست")
        return
    
    text = "🚫 لیست بن‌ها:\n━━━━━━━━━━━━━━━━━━━━\n"
    for ban in banned:
        text += f"📱 {ban[0]} - تا {ban[1]}\n"
    
    bot.reply_to(message, text)

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.chat.id != OWNER_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ فرمت صحیح:\n/ban 09123456789")
            return
        
        phone = parts[1]
        ban_until = (datetime.now() + timedelta(days=30)).isoformat()
        
        cursor.execute("INSERT OR REPLACE INTO banned (phone, ban_until) VALUES (?, ?)", (phone, ban_until))
        conn.commit()
        
        bot.reply_to(message, f"✅ کاربر {phone} به مدت 30 روز بن شد")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.chat.id != OWNER_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ فرمت صحیح:\n/unban 09123456789")
            return
        
        phone = parts[1]
        
        cursor.execute("DELETE FROM banned WHERE phone = ?", (phone,))
        conn.commit()
        
        bot.reply_to(message, f"✅ بن کاربر {phone} لغو شد")
        
    except Exception as e:
        bot.reply_to(message, f"❌ خطا: {str(e)}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.chat.id != OWNER_ID:
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM banned")
    banned_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM messages")
    msg_count = cursor.fetchone()[0]
    
    text = f"""
📊 آمار ربات
━━━━━━━━━━━━━━━━━━━━
👥 کاربران: {user_count}
🚫 بن شده: {banned_count}
💬 پیام‌ها: {msg_count}
🕐 زمان: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
━━━━━━━━━━━━━━━━━━━━
    """
    bot.reply_to(message, text)

@bot.message_handler(commands=['clear'])
def clear_data(message):
    if message.chat.id != OWNER_ID:
        return
    
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM messages")
    conn.commit()
    
    bot.reply_to(message, "✅ همه داده‌ها پاک شد")

# ========== دریافت پیامک از سایت ==========
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.chat.id == OWNER_ID:
        return
    
    # ذخیره پیام کاربر
    cursor.execute("INSERT INTO messages (phone, message, time) VALUES (?, ?, ?)",
                   (str(message.chat.id), message.text, datetime.now().isoformat()))
    conn.commit()
    
    # ارسال به ادمین
    bot.send_message(OWNER_ID, f"💬 پیام از کاربر:\n📱 {message.chat.id}\n📝 {message.text}")

# ========== راه‌اندازی ==========
if __name__ == '__main__':
    print("🤖 ربات روشن شد...")
    while True:
        try:
            bot.polling(timeout=60)
        except Exception as e:
            print(f"خطا: {e}")
            time.sleep(10)