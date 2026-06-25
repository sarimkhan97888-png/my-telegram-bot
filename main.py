from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Bot is Live!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()
    
import telebot
from telebot import types
import sqlite3
import time

# 1. SETUP CONFIGURATION
BOT_TOKEN = "8948036037:AAFRIDJMSnse_I98-bGrAM7p0j6IRbErowQ"
ADMIN_ID = 8113992853  # Aapki numeric Telegram ID

bot = telebot.TeleBot(BOT_TOKEN)

REQUIRED_CHANNELS = ["@profitix11", "@profitix00", "@profitx77"]
PAYMENT_CHANNEL = "@profitx77" # Jis channel me approval request jayegi

# 2. DATABASE SETUP
def init_db():
    conn = sqlite3.connect("referral_bot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            referrals_count INTEGER DEFAULT 0,
            referred_by INTEGER,
            last_bonus_time INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            address TEXT,
            status TEXT DEFAULT 'PENDING'
        )
    """)
    conn.commit()
    conn.close()

init_db()

# 3. MEMBERSHIP CHECK FUNCTION
def is_user_joined(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except Exception:
            return False
    return True

def send_join_request(chat_id):
    markup = types.InlineKeyboardMarkup()
    for channel in REQUIRED_CHANNELS:
        btn = types.InlineKeyboardButton(text=f"Join {channel}", url=f"https://t.me/{channel.replace('@', '')}")
        markup.add(btn)
    btn_check = types.InlineKeyboardButton(text="Check ✅", callback_data="check_join")
    markup.add(btn_check)
    
    text = "❌ *Aapne hamare saare channels join nahi kiye hain!*\n\nBot use karne ke liye niche diye gaye channels join karein aur 'Check ✅' dabayein."
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup)

def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("💰 Balance", "🔗 Referral")
    markup.row("🎁 Daily Bonus", "💳 Withdraw")
    return markup

# 4. /START WITH REFERRAL TRACKING
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    
    args = message.text.split()
    referrer_id = None
    if len(args) > 1 and args[1].isdigit():
        referrer_id = int(args[1])
        if referrer_id == user_id:
            referrer_id = None

    conn = sqlite3.connect("referral_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    user_exists = cursor.fetchone()
    
    if not user_exists:
        cursor.execute("INSERT INTO users (user_id, username, referred_by) VALUES (?, ?, ?)", (user_id, username, referrer_id))
        conn.commit()
        
        if referrer_id and is_user_joined(user_id):
            cursor.execute("UPDATE users SET balance = balance + 1.0, referrals_count = referrals_count + 1 WHERE user_id = ?", (referrer_id,))
            conn.commit()
            try:
                bot.send_message(referrer_id, f"🔔 *Naya Referral!*\nKisi ne aapke link se join kiya hai. Aapko +$1 mile!")
            except Exception:
                pass
    conn.close()

    if not is_user_joined(user_id):
        send_join_request(message.chat.id)
        return

    bot.send_message(message.chat.id, "🎉 Welcome! Aapka account active hai.", reply_markup=get_main_menu())

# 5. BUTTONS AND WORKFLOW LOGIC
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    user_id = message.from_user.id
    
    if not is_user_joined(user_id):
        send_join_request(message.chat.id)
        return

    conn = sqlite3.connect("referral_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT balance, referrals_count, last_bonus_time FROM users WHERE user_id = ?", (user_id,))
    user_data = cursor.fetchone()
    
    if not user_data:
        conn.close()
        return
        
    balance, referrals_count, last_bonus_time = user_data

    if message.text == "💰 Balance":
        text = f"📋 *Aapka Wallet Status:*\n\n💰 Balance: `${balance}`\n👥 Total Referrals: `{referrals_count}`"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "🔗 Referral":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_id}"
        text = f"🔗 *Aapka Referral Link:*\n`{ref_link}`\n\nPer referral aapko $1 milega."
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    elif message.text == "🎁 Daily Bonus":
        if referrals_count < 1:
            bot.send_message(message.chat.id, "❌ *Daily Bonus Locked!*\nBonus lene ke liye kam se kam 1 referral karna zaroori hai.", parse_mode="Markdown")
        else:
            current_time = int(time.time())
            if current_time - last_bonus_time < 86400:
                remaining_time = 86400 - (current_time - last_bonus_time)
                hours = remaining_time // 3600
                bot.send_message(message.chat.id, f"⏳ Aap pehle hi bonus le chuke hain. Agla bonus {hours} ghante baad milega.")
            else:
                cursor.execute("UPDATE users SET balance = balance + 0.5, last_bonus_time = ? WHERE user_id = ?", (current_time, user_id))
                conn.commit()
                bot.send_message(message.chat.id, "🎁 🎉 Mubarak ho! Aapko daily bonus ke *$0.5* mil gaye hain.", parse_mode="Markdown")

    elif message.text == "💳 Withdraw":
        if referrals_count < 10:
            bot.send_message(message.chat.id, f"❌ *Withdraw Error!*\nAapke paas kam se kam 10 referrals hone chahiye. (Abhi: {referrals_count}/10)")
        elif balance < 20.0:
            bot.send_message(message.chat.id, f"❌ *Withdraw Error!*\nMinimum withdrawal amount $20 hai. (Aapka balance: ${balance})")
        else:
            msg = bot.send_message(message.chat.id, "📝 Kripya apna Payment Address type karke bhejein:")
            bot.register_next_step_handler(msg, process_withdrawal_address, balance)
            
    conn.close()

# 6. WITHDRAW PROCESS & ADMIN PANEL TRIGGER
def process_withdrawal_address(message, balance):
    user_id = message.from_user.id
    address = message.text
    
    if message.text.startswith('/'):
        bot.send_message(message.chat.id, "❌ Invalid address. Request cancelled.")
        return

    conn = sqlite3.connect("referral_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (balance, user_id))
    cursor.execute("INSERT INTO withdrawals (user_id, amount, address) VALUES (?, ?, ?)", (user_id, balance, address))
    request_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Aapki withdraw request Admin ke paas bhej di gayi hai.")
    
    markup = types.InlineKeyboardMarkup()
    btn_approve = types.InlineKeyboardButton("Approve ✅", callback_data=f"app_{request_id}")
    btn_reject = types.InlineKeyboardButton("Reject ❌", callback_data=f"rej_{request_id}")
    markup.add(btn_approve, btn_reject)
    
    admin_msg = (f"🆔 *New Withdrawal Request (#{request_id})*\n\n"
                 f"👤 User ID: `{user_id}`\n"
                 f"💰 Amount: `${balance}`\n"
                 f"💳 Address: `{address}`")
                 
    bot.send_message(PAYMENT_CHANNEL, admin_msg, parse_mode="Markdown", reply_markup=markup)

# 7. CALLBACK QUERY HANDLERS
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.from_user.id
    
    if call.data == "check_join":
        if is_user_joined(user_id):
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(call.message.chat.id, "✅ Verified! Ab aap bot use kar sakte hain.", reply_markup=get_main_menu())
        else:
            bot.answer_callback_query(call.id, "❌ Aapne abhi bhi saare channels join nahi kiye hain!", show_alert=True)
            
    elif call.data.startswith("app_") or call.data.startswith("rej_"):
        if user_id != ADMIN_ID:
            bot.answer_callback_query(call.id, "🔒 Yeh buttons sirf Admin ke liye hain!", show_alert=True)
            return
            
        action, req_id = call.data.split("_")
        conn = sqlite3.connect("referral_bot.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT user_id, amount, status FROM withdrawals WHERE id = ?", (req_id,))
        req_data = cursor.fetchone()
        
        if not req_data or req_data[2] != 'PENDING':
            bot.answer_callback_query(call.id, "⚠️ Yeh request pehle hi process ho chuki hai.", show_alert=True)
            conn.close()
            return
            
        target_user, amount, _ = req_data
        
        if action == "app":
            cursor.execute("UPDATE withdrawals SET status = 'APPROVED' WHERE id = ?", (req_id,))
            conn.commit()
            bot.edit_message_text(f"✅ *Request #{req_id} APPROVED*\nAmount: ${amount} sent to User `{target_user}`.", PAYMENT_CHANNEL, call.message.message_id, parse_mode="Markdown")
            try:
                bot.send_message(target_user, f"🎉 *Withdrawal Approved!*\nAdmin ne aapki `${amount}` ki request approve kar di hai.")
            except Exception: pass
            
        elif action == "rej":
            cursor.execute("UPDATE withdrawals SET status = 'REJECTED' WHERE id = ?", (req_id,))
            cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_user))
            conn.commit()
            bot.edit_message_text(f"❌ *Request #{req_id} REJECTED*\nAmount: ${amount} refunded to User `{target_user}`.", PAYMENT_CHANNEL, call.message.message_id, parse_mode="Markdown")
            try:
                bot.send_message(target_user, f"❌ *Withdrawal Rejected!*\nAdmin ne aapki `${amount}` ki request reject kar di hai. Balance refund ho gaya hai.")
            except Exception: pass
            
        conn.close()

if __name__ == "__main__":
   keep_alive()
    bot.infinity_polling()
  
