import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
import threading, random, json
from datetime import datetime, timedelta

# ✅ Use environment variable for security
TOKEN = os.environ.get("BOT_TOKEN", "8332615999:AAFfvKCyUGvoWxBH4NVxvk4qmgMOMxwEmFk")
bot = telebot.TeleBot(TOKEN)

SEARCH_PATH = "./logs"      # Put .txt files here
OUTPUT_PATH = "./outputs"   # Render allows writing files
KEYS_FILE = "keys.json"

previous_sent_lines = {}
total_lines = []

app = Flask(__name__)

# ================================
# 🔹 KEY SYSTEM FUNCTIONS
# ================================
if not os.path.exists(KEYS_FILE):
    with open(KEYS_FILE, "w") as f:
        json.dump({}, f)

def load_keys():
    with open(KEYS_FILE, "r") as f:
        return json.load(f)

def save_keys(keys):
    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)

def load_lines():
    global total_lines
    total_lines = []
    if not os.path.exists(SEARCH_PATH):
        print("⚠️ Logs folder not found!")
        return
    for filename in os.listdir(SEARCH_PATH):
        if filename.endswith(".txt"):
            with open(os.path.join(SEARCH_PATH, filename), "r", encoding="utf-8", errors="ignore") as f:
                total_lines.extend(f.readlines())

load_lines()

def has_active_key(user_id):
    keys = load_keys()
    if str(user_id) in keys:
        exp = datetime.strptime(keys[str(user_id)]["expires"], "%Y-%m-%d %H:%M:%S")
        if datetime.now() <= exp:
            return True
        else:
            del keys[str(user_id)]
            save_keys(keys)
    return False

# ================================
# 🔹 BOT COMMANDS
# ================================

@bot.message_handler(commands=["createkey"])
def create_key(message):
    if message.from_user.id != 7011151235:
        bot.reply_to(message, "❌ Not authorized.")
        return
    try:
        _, days, count = message.text.split()
        days, count = int(days), int(count)
        keys = load_keys()
        new_keys = []
        for _ in range(count):
            key = f"KEY-{random.randint(100000, 999999)}"
            exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
            keys[key] = {"expires": exp, "redeemed_by": None}
            new_keys.append(key)
        save_keys(keys)
        bot.reply_to(message, "✅ Keys generated:\n" + "\n".join(new_keys))
    except:
        bot.reply_to(message, "⚠️ Usage: /createkey <days> <count>")

@bot.message_handler(commands=["redeem"])
def redeem_key(message):
    try:
        _, key = message.text.split()
        keys = load_keys()
        if key in keys and keys[key]["redeemed_by"] is None:
            keys[str(message.from_user.id)] = {
                "expires": keys[key]["expires"],
                "redeemed_by": message.from_user.id
            }
            del keys[key]
            save_keys(keys)
            bot.reply_to(message, "✅ Key redeemed successfully!")
        else:
            bot.reply_to(message, "❌ Invalid or already redeemed key.")
    except:
        bot.reply_to(message, "⚠️ Usage: /redeem <key>")

@bot.message_handler(commands=["start"])
def start_cmd(message):
    if not has_active_key(message.from_user.id):
        bot.send_message(
            message.chat.id,
            "❌ You need to redeem a key to access the bot.\nUse `/redeem <key>`.",
            parse_mode="Markdown"
        )
        return

    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🎮 Generate Account", callback_data="generate"),
        InlineKeyboardButton("📞 Contact Owner", url="https://t.me/OnlyJosh4"),
        InlineKeyboardButton("ℹ️ Info", callback_data="info"),
        InlineKeyboardButton("📊 Status", callback_data="status")
    )

    bot.send_message(
        message.chat.id,
        "🌟 **Welcome to the Ultimate Bot!**\n\nChoose an option below 👇",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ================================
# 🔹 INLINE BUTTON HANDLER
# ================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.data == "status":
        bot.send_message(call.message.chat.id, f"📊 Total Lines: {len(total_lines)}\n✅ Bot Online")

    elif call.data == "generate":
        choose_keyword(call.message.chat.id)

    elif call.data == "info":
        bot.send_message(call.message.chat.id, "ℹ️ Bot Info\nVersion 2.0\nMade by @OnlyJosh4")

    elif call.data in ["garena.com", "roblox.com", "facebook.com", "netflix.com"]:
        search_keyword(call.message.chat.id, call.data)

    elif call.data == "own_keyword":
        msg = bot.send_message(call.message.chat.id, "🔍 Enter your keyword:")
        bot.register_next_step_handler(msg, search_keyword_user)

def choose_keyword(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("🕹 Garena", callback_data="garena.com"),
        InlineKeyboardButton("🤖 Roblox", callback_data="roblox.com")
    )
    markup.add(
        InlineKeyboardButton("📘 Facebook", callback_data="facebook.com"),
        InlineKeyboardButton("🎬 Netflix", callback_data="netflix.com")
    )
    markup.add(InlineKeyboardButton("🔍 Own Keyword", callback_data="own_keyword"))
    bot.send_message(chat_id, "Choose a keyword:", reply_markup=markup)

def search_keyword_user(message):
    search_keyword(message.chat.id, message.text.lower())

def search_keyword(chat_id, keyword):
    load_lines()
    found = [line.strip() for line in total_lines if keyword in line.lower()]
    if not found:
        bot.send_message(chat_id, "❌ No results found.")
        return

    if not os.path.exists(OUTPUT_PATH):
        os.makedirs(OUTPUT_PATH)

    filename = f"Results_{keyword}.txt"
    filepath = os.path.join(OUTPUT_PATH, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(found[:5000]))

    with open(filepath, "rb") as f:
        bot.send_document(chat_id, f, caption=f"✅ Found {len(found)} results for '{keyword}'")

# ================================
# 🔹 FLASK SERVER FOR RENDER
# ================================

def run_bot():
    bot.polling(none_stop=True)

@app.route("/")
def home():
    return "✅ Telegram Bot Running on Render!"

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)
