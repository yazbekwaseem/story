import os
import json
import time
import telebot
from flask import Flask, request, abort
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

# ========== الإعدادات الأساسية ==========
TOKEN = os.environ.get('TELEGRAM_TOKEN')
APP_URL = os.environ.get('APP_URL')

if not TOKEN or not APP_URL:
    raise ValueError("❌ TELEGRAM_TOKEN and APP_URL must be set in environment variables")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== تحميل القصة ==========
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

# ========== معالج عام لجميع الرسائل (للتأكد من التقاط /start) ==========
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    print(f"📨 رسالة واردة: {message.text}")
    
    # إذا كانت الرسالة هي /start نتعامل معها
    if message.text and message.text.startswith('/start'):
        print("🚀 تم اكتشاف أمر /start في المعالج العام")
        
        user_id = message.from_user.id
        # نبدأ من العقدة المحددة في "start" أو "intro" كاحتياط
        current_node = STORY.get("start", "intro")
        user_states[user_id] = current_node

        node = STORY.get(current_node)
        if not node:
            bot.send_message(message.chat.id, "❌ خطأ في القصة: العقدة الابتدائية غير موجودة!")
            return

        # تجهيز الأزرار
        markup = InlineKeyboardMarkup()
        for btn in node.get("buttons", []):
            markup.add(InlineKeyboardButton(text=btn["text"], callback_data=btn["next"]))

        text = node["text"]
        image_url = node.get("image")

        # إرسال الرد (صورة أو نص)
        try:
            if image_url:
                bot.send_photo(message.chat.id, photo=image_url, caption=text, reply_markup=markup)
            else:
                bot.send_message(message.chat.id, text, reply_markup=markup)
            print("🚀 تم إرسال رد /start بنجاح")
        except Exception as e:
            print(f"⚠️ خطأ في إرسال رد /start: {e}")
            bot.send_message(message.chat.id, f"[تعذر إرسال الصورة]\n\n{text}", reply_markup=markup)
    
    else:
        # رسالة غير معروفة
        bot.send_message(message.chat.id, "أهلاً! أرسل /start لبدء القصة.")

# ========== معالج الـ Callback (للأزرار التفاعلية) ==========
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    print("🚀 Callback من المستخدم", call.from_user.id, "البيانات:", call.data)
    
    user_id = call.from_user.id
    next_node_id = call.data

    # إذا كان المستخدم ليس لديه حالة ويحاول الوصول لعقدة غير "start"
    if user_id not in user_states and next_node_id != "start":
        bot.answer_callback_query(call.id, "ابدأ من جديد بـ /start")
        return

    # إذا طلب إعادة التشغيل
    if next_node_id == "start":
        # ننشئ رسالة وهمية ونمررها للمعالج العام (أو نستدعي start مباشرة)
        fake_message = call.message
        fake_message.from_user = call.from_user
        fake_message.text = "/start"
        handle_all_messages(fake_message)
        return

    # تحديث الحالة
    user_states[user_id] = next_node_id

    node = STORY.get(next_node_id)
    if not node:
        bot.answer_callback_query(call.id, "❌ خطأ في القصة: العقدة غير موجودة!")
        return

    # تجهيز الأزرار
    markup = InlineKeyboardMarkup()
    for btn in node.get("buttons", []):
        markup.add(InlineKeyboardButton(text=btn["text"], callback_data=btn["next"]))

    text = node["text"]
    image_url = node.get("image")

    # محاولة تعديل الرسالة الحالية (إن أمكن)
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
        print("🚀 تم تعديل الرسالة بنجاح")
    except Exception as e:
        print(f"⚠️ فشل التعديل، إرسال رسالة جديدة: {e}")
        try:
            if image_url:
                bot.send_photo(call.message.chat.id, photo=image_url, caption=text, reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, text, reply_markup=markup)
            print("🚀 تم إرسال رسالة جديدة بنجاح")
        except Exception as e2:
            print(f"⚠️ فشل إرسال الرسالة الجديدة: {e2}")
            bot.send_message(call.message.chat.id, f"[تعذر إرسال الصورة]\n\n{text}", reply_markup=markup)

    # الرد على callback
    bot.answer_callback_query(call.id)

    # إذا كانت نهاية القصة، نعرض زر إعادة
    if node.get("end"):
        replay_markup = InlineKeyboardMarkup()
        replay_markup.add(InlineKeyboardButton("🔄 العب مرة أخرى", callback_data="start"))
        bot.send_message(call.message.chat.id, "🏁 انتهت القصة!", reply_markup=replay_markup)

# ========== مسارات Flask ==========
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'Bot is running'

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') != 'application/json':
        abort(403)
    
    try:
        json_string = request.get_data().decode('utf-8')
        print("📨 تم استلام POST, طول:", len(json_string))
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    except Exception as e:
        print(f"❌ خطأ في معالجة webhook: {e}")
        return '', 500

@app.route('/debug')
def debug():
    """صفحة لعرض معلومات التشخيص"""
    try:
        webhook_info = bot.get_webhook_info()
        return {
            "story_loaded": bool(STORY),
            "story_keys": list(STORY.keys()) if STORY else [],
            "webhook": {
                "url": webhook_info.url,
                "pending_updates": webhook_info.pending_update_count,
                "last_error": webhook_info.last_error_message
            },
            "message_handlers_count": len(bot.message_handlers),
            "callback_handlers_count": len(bot.callback_query_handlers)
        }
    except Exception as e:
        return {"error": str(e)}

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
    print("🔧 جاري إزالة webhook القديم...")
    bot.remove_webhook()
    webhook_url = f"{APP_URL}/"
    print(f"🔧 تعيين webhook إلى: {webhook_url}")
    bot.set_webhook(url=webhook_url)
    time.sleep(1)  # تأخير بسيط
    info = bot.get_webhook_info()
    print("🔧 معلومات webhook بعد التعيين:", info)
    print(f"🔧 عدد معالجات الرسائل المسجلة: {len(bot.message_handlers)}")
    print(f"🔧 عدد معالجات callback المسجلة: {len(bot.callback_query_handlers)}")

# استدعاء إعداد webhook
setup_webhook()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
