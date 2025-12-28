import telebot
import requests
import sqlite3
import logging
import random
import time
from datetime import datetime, timedelta

# ==========================================
# 1. KONFIGURATSIYA
# ==========================================
API_TOKEN = '8522305080:AAEVWG4LQWzOVh0hwrsOiEqBnIoD4PuFUtI'
ADMIN_ID = 8058389631

# Kanallar
ORDERS_CHANNEL = "-1003591019560"   
PAYMENTS_CHANNEL = "-1003672059498" 

# WIQ API Sozlamalari
WIQ_API_URL = "https://wiq.ru/api/v2"
WIQ_API_KEY = "CH9gunPYthHlriASaX2yU2lCtyp7A9Vd"

# To'lov ma'lumotlari
CARD_NUMBER = "9860 1201 2436 4106"
CARD_HOLDER = "Qosimov.U."

# Narx siyosati
PROFIT_MARGIN = 1.35   # 35% foyda
VIP_DISCOUNT = 0.92    # 8% chegirma
VIP_BRONZE_PRICE = 15000 
VIP_GOLD_PRICE = 25000

bot = telebot.TeleBot(API_TOKEN)
logging.basicConfig(level=logging.INFO)
user_orders = {}

# ==========================================
# 2. XIZMATLAR RO'YXATI
# ==========================================
SERVICES_DATA = {
    "Telegram 🔹": {
        "👥 Obunachilar (Mix/Real)": [411, 777, 1038, 591, 592],
        "👥 Obunachilar (O'zbek)": [949, 950, 1039],
        "👁 Ko'rishlar (Post)": [2192, 2193, 2244],
        "👍 Reaksiyalar (Emodji)": [429, 430, 431, 1016, 1017, 1018],
        "🔥 Real Active": [653, 654, 825]
    },
    "Instagram 📸": {
        "👥 Obunachilar": [4, 29, 9, 28, 547],
        "❤️ Layklar": [131, 76, 33, 104],
        "👁 Ko'rishlar/Reels": [65, 71, 141],
        "💬 Kommentariya": [55, 56]
    },
    "TikTok 🎵": {
        "👥 Obunachilar": [265, 252],
        "❤️ Layklar": [306, 253],
        "👁 Ko'rishlar": [312, 313]
    },
    "YouTube 🔴": {
        "👥 Obunachilar": [228, 229],
        "👍 Layklar": [232, 233],
        "👁 Ko'rishlar": [225, 226]
    }
}

# ==========================================
# 3. MA'LUMOTLAR BAZASI
# ==========================================
def init_db():
    conn = sqlite3.connect('nakrutka_final_v11.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, vip_until TEXT DEFAULT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels 
                      (chat_id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def get_user_data(uid):
    conn = sqlite3.connect('nakrutka_final_v11.db')
    res = conn.execute("SELECT balance, vip_until FROM users WHERE user_id = ?", (uid,)).fetchone()
    if not res:
        conn.execute("INSERT INTO users (user_id, balance) VALUES (?, 0)", (uid,))
        conn.commit()
        res = (0, None)
    conn.close()
    return res

def update_bal(uid, amt):
    conn = sqlite3.connect('nakrutka_final_v11.db')
    conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amt, uid))
    conn.commit()
    conn.close()

def is_vip(uid):
    _, until_str = get_user_data(uid)
    if until_str:
        try:
            until = datetime.strptime(until_str, "%Y-%m-%d %H:%M:%S")
            if until > datetime.now(): return until
        except: return None
    return None

def check_sub(uid):
    if uid == ADMIN_ID: return True
    conn = sqlite3.connect('nakrutka_final_v11.db')
    chans = conn.execute("SELECT chat_id FROM channels").fetchall()
    conn.close()
    if not chans: return True
    for ch in chans:
        try:
            status = bot.get_chat_member(ch[0], uid).status
            if status == 'left': return False
        except: continue
    return True

def get_usd_rate():
    try:
        res = requests.get("https://nbu.uz/uz/exchange-rates/json/", timeout=5).json()
        for i in res:
            if i['code'] == 'USD': return float(i['cb_price'])
    except: return 12950.0

# ==========================================
# 4. KLAVIATURALAR
# ==========================================
def main_kb(uid):
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("🚀 Buyurtma berish", "💰 Balans")
    m.add("💳 Hisobni to'ldirish", "💎 VIP Status")
    m.add("💵 Dollar kursi")
    if uid == ADMIN_ID: m.add("⚙️ Admin Panel")
    return m

def admin_kb():
    m = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    m.add("📊 Statistika", "🌐 API Balans")
    m.add("💸 Pul qo'shish", "⬅️ Chiqish")
    return m

# ==========================================
# 5. HANDLERLAR (TUZATILDI)
# ==========================================
@bot.message_handler(commands=['start'])
def start_handler(message):
    init_db()
    uid = message.chat.id
    if not check_sub(uid):
        conn = sqlite3.connect('nakrutka_final_v11.db')
        chans = conn.execute("SELECT url FROM channels").fetchall()
        conn.close()
        mk = telebot.types.InlineKeyboardMarkup()
        if not chans:
            bot.send_message(uid, "Xush kelibsiz!", reply_markup=main_kb(uid))
            return
        for i, c in enumerate(chans):
            mk.add(telebot.types.InlineKeyboardButton(f"➕ Kanal {i+1}", url=c[0]))
        mk.add(telebot.types.InlineKeyboardButton("✅ Tasdiqlash", callback_data="check_sub_now"))
        bot.send_message(uid, "👋 Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=mk)
        return
    bot.send_message(uid, f"Xush kelibsiz!", reply_markup=main_kb(uid))

@bot.callback_query_handler(func=lambda c: c.data == "check_sub_now")
def sub_callback(call):
    if check_sub(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ Tasdiqlandi!", reply_markup=main_kb(call.from_user.id))
    else:
        bot.answer_callback_query(call.id, "❌ Obuna bo'lmadingiz!", show_alert=True)

@bot.message_handler(func=lambda m: m.text == "🚀 Buyurtma berish")
def order_start(message):
    if not check_sub(message.chat.id): return
    mk = telebot.types.InlineKeyboardMarkup(row_width=2)
    for p in SERVICES_DATA.keys():
        mk.add(telebot.types.InlineKeyboardButton(p, callback_data=f"plat_{p}"))
    bot.send_message(message.chat.id, "📱 Ijtimoiy tarmoqni tanlang:", reply_markup=mk)

# --- BUYURTMA QISMLARI ---
@bot.callback_query_handler(func=lambda c: c.data.startswith('plat_'))
def order_cat(call):
    p = call.data[5:]
    mk = telebot.types.InlineKeyboardMarkup(row_width=1)
    for cat in SERVICES_DATA[p].keys():
        mk.add(telebot.types.InlineKeyboardButton(cat, callback_data=f"cat_{p}|{cat}"))
    bot.edit_message_text(f"📂 {p} kategoriyasini tanlang:", call.message.chat.id, call.message.message_id, reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data.startswith('cat_'))
def order_serv(call):
    p, c = call.data[4:].split('|')
    ids = SERVICES_DATA[p][c]
    try:
        api_res = requests.post(WIQ_API_URL, data={'key': WIQ_API_KEY, 'action': 'services'}).json()
        rate = get_usd_rate()
        mk = telebot.types.InlineKeyboardMarkup(row_width=1)
        for s in api_res:
            if int(s['service']) in ids:
                price = float(s['rate']) * rate * PROFIT_MARGIN
                mk.add(telebot.types.InlineKeyboardButton(f"{s['name'][:25]} | {price:,.0f}s", callback_data=f"ser_{s['service']}"))
        bot.edit_message_text(f"⬇️ {c} turini tanlang:", call.message.chat.id, call.message.message_id, reply_markup=mk)
    except: bot.answer_callback_query(call.id, "API xatosi!")

@bot.callback_query_handler(func=lambda c: c.data.startswith('ser_'))
def order_link(call):
    user_orders[call.from_user.id] = {'sid': call.data[4:]}
    msg = bot.send_message(call.message.chat.id, "🔗 Havola (Link) yuboring:")
    bot.register_next_step_handler(msg, order_qty)

def order_qty(message):
    user_orders[message.chat.id]['link'] = message.text
    msg = bot.send_message(message.chat.id, "🔢 Miqdorni kiriting:")
    bot.register_next_step_handler(msg, order_final)

def order_final(message):
    uid = message.chat.id
    try:
        qty = int(message.text)
        data = user_orders[uid]
        api_res = requests.post(WIQ_API_URL, data={'key': WIQ_API_KEY, 'action': 'services'}).json()
        s = next(x for x in api_res if str(x['service']) == data['sid'])
        cost = (float(s['rate']) * get_usd_rate() * PROFIT_MARGIN / 1000) * qty
        if is_vip(uid): cost *= VIP_DISCOUNT
        bal, _ = get_user_data(uid)
        if bal >= cost:
            res = requests.post(WIQ_API_URL, data={'key': WIQ_API_KEY, 'action': 'add', 'service': data['sid'], 'link': data['link'], 'quantity': qty}).json()
            if 'order' in res:
                update_bal(uid, -cost)
                bot.send_message(uid, f"✅ Buyurtma qabul qilindi!\n💰 Narx: {cost:,.0f} so'm")
                bot.send_message(ORDERS_CHANNEL, f"🛒 **Yangi Buyurtma**\nID: {res['order']}\nSumma: {cost:,.0f}s")
            else: bot.send_message(uid, f"Xato: {res.get('error')}")
        else: bot.send_message(uid, "❌ Mablag' yetarli emas!")
    except: bot.send_message(uid, "❌ Xatolik!")

# --- ADMIN FUNKSIYALARI ---
@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_dash(message):
    bot.send_message(ADMIN_ID, "Admin Panel:", reply_markup=admin_kb())

@bot.message_handler(func=lambda m: m.text == "📊 Statistika" and m.from_user.id == ADMIN_ID)
def admin_stats(message):
    conn = sqlite3.connect('nakrutka_final_v11.db')
    cnt = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    bot.send_message(ADMIN_ID, f"👥 Jami foydalanuvchilar: {cnt} ta")

@bot.message_handler(func=lambda m: m.text == "🌐 API Balans" and m.from_user.id == ADMIN_ID)
def check_api_bal(message):
    try:
        res = requests.post(WIQ_API_URL, data={'key': WIQ_API_KEY, 'action': 'balance'}).json()
        usd_bal = float(res['balance'])
        uzs_bal = usd_bal * get_usd_rate()
        bot.send_message(ADMIN_ID, f"🌐 WIQ.ru Balansi:\n💵 {usd_bal} USD\n💰 {uzs_bal:,.0f} so'm")
    except: bot.send_message(ADMIN_ID, "API balansini olib bo'lmadi!")

@bot.message_handler(func=lambda m: m.text == "💰 Balans")
def show_bal(message):
    bal, _ = get_user_data(message.chat.id)
    bot.send_message(message.chat.id, f"💰 Sizning balansingiz: {bal:,.0f} so'm")

@bot.message_handler(func=lambda m: m.text == "💵 Dollar kursi")
def dollar_rate(message):
    bot.send_message(message.chat.id, f"💵 1 USD = {get_usd_rate():,.0f} so'm")

@bot.message_handler(func=lambda m: m.text == "⬅️ Chiqish")
def exit_admin(message):
    bot.send_message(message.chat.id, "Bosh menyu:", reply_markup=main_kb(message.chat.id))

# --- ASOSIY ---
if __name__ == "__main__":
    init_db()
    print("Bot Render-da muvaffaqiyatli ishlamoqda!")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)

