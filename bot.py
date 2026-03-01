import os
import json
import telebot
from flask import Flask, request, abort
from telebot.types import Update

TOKEN = os.environ.get('TELEGRAM_TOKEN')
APP_URL = os.environ.get('APP_URL')

if not TOKEN or not APP_URL:
    raise ValueError("❌ TELEGRAM_TOKEN and APP_URL must be set")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== معالج بسيط جداً ==========
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    print(f"🔥🔥🔥 تم استلام رسالة: {message.text}")
    bot.send_message(message.chat.id, f"تم استلام: {message.text}")

# ========== مسار webhook ==========
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        print("📨 تم استلام POST")
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    abort(403)

@app.route('/', methods=['GET'])
def index():
    return 'Test Bot Running'

@app.route('/debug')
def debug():
    return {
        "handlers": len(bot.message_handlers),
        "webhook": bot.get_webhook_info().url
    }

# ========== إعداد webhook ==========
print("🔧 إعداد webhook...")
bot.remove_webhook()
bot.set_webhook(url=f"{APP_URL}/")
print("🔧 Webhook set to:", APP_URL)
print("🔧 Handlers:", len(bot.message_handlers))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
