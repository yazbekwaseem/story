import os
import json
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

# ========== معالج أمر /start ==========
@bot.message_handler(commands=['start'])
def start(message):
    print("🚀🚀🚀 [start] تم استدعاء معالج /start من المستخدم", message.from_user.id)
    print("🚀🚀🚀 [start] نص الرسالة:", message.text)
    
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
        print("🚀🚀🚀 [start] تم إرسال الرد بنجاح")
    except Exception as e:
        print(f"⚠️ [start] خطأ في الإرسال: {e}")
        bot.send_message(message.chat.id, f"[تعذر إرسال الصورة]\n\n{text}", reply_markup=markup)

# ========== معالج الـ Callback ==========
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    print("🚀🚀🚀 [callback] تم استدعاء معالج callback من المستخدم", call.from_user.id)
    print("🚀🚀🚀 [callback] بيانات callback:", call.data)
    
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
        print("🚀🚀🚀 [callback] تم تعديل الرسالة بنجاح")
    except Exception as e:
        print(f"⚠️ [callback] فشل التعديل، إرسال رسالة جديدة: {e}")
        try:
            if image_url:
                bot.send_photo(call.message.chat.id, photo=image_url, caption=text, reply_markup=markup)
            else:
                bot.send_message(call.message.chat.id, text, reply_markup=markup)
            print("🚀🚀🚀 [callback] تم إرسال رسالة جديدة بنجاح")
        except Exception as e2:
            print(f"⚠️ [callback] فشل إرسال الرسالة الجديدة: {e2}")
            bot.send_message(call.message.chat.id, f"[تعذر إرسال الصورة]\n\n{text}", reply_markup=markup)

    bot.answer_callback_query(call.id)

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
    print("📨 [webhook] تم استلام طلب POST جديد")
    if request.headers.get('content-type') != 'application/json':
        print("❌ [webhook] نوع المحتوى غير صحيح:", request.headers.get('content-type'))
        abort(403)
    
    try:
        json_string = request.get_data().decode('utf-8')
        print("📨 [webhook] طول البيانات:", len(json_string))
        print("📨 [webhook] أول 300 حرف من البيانات:", json_string[:300])
        
        update = Update.de_json(json_string)
        print("📨 [webhook] تم تحويل JSON إلى Update بنجاح")
        print("📨 [webhook] نوع التحديث:", type(update))
        
        if hasattr(update, 'message') and update.message:
            print("📨 [webhook] الرسالة:", update.message.text)
        
        # معالجة التحديث
        bot.process_new_updates([update])
        print("📨 [webhook] تم تمرير التحديث إلى البوت")
        return ''
    except Exception as e:
        print(f"❌ [webhook] خطأ أثناء معالجة التحديث: {e}")
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
            "handlers_count": {
                "message": len(bot.message_handlers),
                "callback": len(bot.callback_query_handlers)
            },
            "message_handlers_commands": [
                h['filters'].commands if h['filters'] and hasattr(h['filters'], 'commands') else None 
                for h in bot.message_handlers
            ]
        }
    except Exception as e:
        return {"error": str(e)}

# ========== التأكد من أن المعالجات مسجلة قبل إعداد webhook ==========
print("🔧 [init] تم تسجيل معالجات البوت")
print(f"🔧 [init] عدد معالجات الرسائل المسجلة: {len(bot.message_handlers)}")
print(f"🔧 [init] عدد معالجات callback المسجلة: {len(bot.callback_query_handlers)}")

# ========== إعداد webhook بعد تعريف جميع المعالجات ==========
def setup_webhook():
    """إزالة webhook القديم وتعيين الجديد"""
    print("🔧 [setup] جاري إزالة webhook القديم...")
    bot.remove_webhook()
    webhook_url = f"{APP_URL}/"
    print(f"🔧 [setup] تعيين webhook إلى: {webhook_url}")
    result = bot.set_webhook(url=webhook_url)
    print(f"🔧 [setup] نتيجة تعيين webhook: {result}")
    
    # تأخير بسيط ثم التحقق
    time.sleep(2)
    info = bot.get_webhook_info()
    print("🔧 [setup] معلومات webhook بعد التعيين:", info)

# استيراد time للتأخير
import time

# استدعاء إعداد webhook
setup_webhook()

# تأكيد نهائي
print("🔧 [init] ✅ تم الانتهاء من التهيئة. البوت جاهز لاستقبال الأوامر.")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
