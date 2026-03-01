import os
import json
import telebot
from flask import Flask, request, abort
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

TOKEN = os.environ.get('TELEGRAM_TOKEN')
APP_URL = os.environ.get('APP_URL')

if not TOKEN or not APP_URL:
    raise ValueError("❌ TELEGRAM_TOKEN and APP_URL must be set in environment variables")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تحميل القصة مع معالجة الأخطاء
try:
    with open("story.json", encoding="utf-8") as f:
        STORY = json.load(f)
    print("✅ story.json loaded successfully. Keys:", list(STORY.keys()))
except Exception as e:
    print("❌ Error loading story.json:", e)
    STORY = {
        "intro": {
            "text": "⚠️ خطأ في تحميل القصة. يرجى الاتصال بالمطور.",
            "buttons": []
        }
    }

user_states = {}

# ========== تعريف معالجات البوت أولاً ==========
@bot.message_handler(commands=['start'])
def start(message):
    print("📩 /start from user", message.from_user.id)
    user_id = message.from_user.id
    current_node = STORY.get("start", "intro")
    user_states[user_id] = current_node

    node = STORY.get(current_node)
    if not node:
        bot.send_message(message.chat.id, "❌ خطأ في القصة!")
        return

    markup = InlineKeyboardMarkup()
    for btn in node.get("buttons", []):
        markup.add(InlineKeyboardButton(text=btn["text"], callback_data=btn["next"]))

    text = node["text"]
    image_url = node.get("image")

    try:
        if image_url:
            bot.send_photo(message.chat.id, photo=image_url, caption=text, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, text, reply_markup=markup)
    except Exception as e:
        print(f"⚠️ Error sending photo in start: {e}")
        bot.send_message(message.chat.id, f"[تعذر إرسال الصورة]\n\n{text}", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    print("📞 Callback from user", call.from_user.id, "data:", call.data)
    user_id = call.from_user.id
    next_node_id = call.data

    if user_id not in user_states and next_node_id != "start":
        bot.answer_callback_query(call.id, "ابدأ من جديد بـ /start")
        return

    if next_node_id == "start":
        fake_message = call.message
        fake_message.from_user = call.from_user
        start(fake_message)
        return

    user_states[user_id] = next_node_id
    node = STORY.get(next_node_id)
    if not node:
        bot.answer_callback_query(call.id, "❌ خطأ في القصة!")
        return

    markup = InlineKeyboardMarkup()
    for btn in node.get("buttons", []):
        markup.add(InlineKeyboardButton(text=btn["text"], callback_data=btn["next"]))

    text = node["text"]
    image_url = node.get("image")

    try:
        if image_url:
            bot.edit_message_media(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                media=telebot.types.InputMediaPhoto(media=image_url, caption=text),
                reply_markup=markup
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup
            )
    except Exception as e:
        print("⚠️ Edit failed, sending new message:", e)
        try:
            if image_url:
                bot.send_photo(call.message.chat.id, photo=image_url, caption=text, reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, text, reply_markup=markup)
        except Exception as e2:
            print(f"⚠️ Also failed to send new message: {e2}")
            bot.send_message(call.message.chat.id, f"[تعذر إرسال الصورة]\n\n{text}", reply_markup=markup)

    bot.answer_callback_query(call.id)

    if node.get("end"):
        replay_markup = InlineKeyboardMarkup()
        replay_markup.add(InlineKeyboardButton("🔄 العب مرة أخرى", callback_data="start"))
        bot.send_message(call.message.chat.id, "🏁 انتهت القصة!", reply_markup=replay_markup)

# ========== تعريف مسارات Flask ==========
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'Bot is running'

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        print("📨 Received POST, length:", len(json_string))
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

@app.route('/debug')
def debug():
    return {
        "story_loaded": bool(STORY),
        "story_keys": list(STORY.keys()) if STORY else [],
        "has_intro": "intro" in STORY,
        "has_start": "start" in STORY
    }

@app.route('/check_webhook')
def check_webhook():
    try:
        info = bot.get_webhook_info()
        return {
            "webhook_url": info.url,
            "pending_updates": info.pending_update_count,
            "last_error": info.last_error_message,
            "is_working": info.url == f"{APP_URL}/"
        }
    except Exception as e:
        return {"error": str(e)}

# ========== إعداد webhook بعد تعريف جميع المعالجات ==========
def setup_webhook():
    bot.remove_webhook()
    webhook_url = f"{APP_URL}/"
    bot.set_webhook(url=webhook_url)
    info = bot.get_webhook_info()
    print("🔗 Webhook set to:", webhook_url)
    print("ℹ️ Webhook info:", info)

# تأخير إعداد webhook قليلاً للتأكد من تحميل كل شيء
import time
time.sleep(1)
setup_webhook()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
