import os
import json
import telebot
from flask import Flask, request, abort
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update

# تحميل التوكن و URL من البيئة (ضعها في Render Environment Variables)
TOKEN = os.environ.get('TELEGRAM_TOKEN')
APP_URL = os.environ.get('APP_URL')  # مثل https://your-app.onrender.com

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# تحميل القصة
with open("story.json", encoding="utf-8") as f:
    STORY = json.load(f)

# تخزين حالة كل مستخدم
user_states = {}

# الـ Start handler
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    current_node = STORY.get("start", "intro")  # افتراضيًا "intro" من القصة السابقة
    user_states[user_id] = current_node
    
    node = STORY.get(current_node)
    if not node:
        bot.send_message(message.chat.id, "خطأ في القصة!")
        return
    
    markup = InlineKeyboardMarkup()
    for btn in node.get("buttons", []):
        markup.add(InlineKeyboardButton(
            text=btn["text"],
            callback_data=btn["next"]
        ))
    
    text = node["text"]
    image_url = node.get("image")  # إذا كان هناك صورة من ImgBB
    
    if image_url:
        bot.send_photo(message.chat.id, photo=image_url, caption=text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text, reply_markup=markup)

# الـ Callback handler
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    user_id = call.from_user.id
    next_node_id = call.data
    
    if user_id not in user_states and next_node_id != "start":
        bot.answer_callback_query(call.id, "ابدأ من جديد بـ /start")
        return
    
    # إذا كان "start"، أعد التشغيل
    if next_node_id == "start":
        start(call.message)
        return
    
    # تحديث الحالة
    user_states[user_id] = next_node_id
    
    node = STORY.get(next_node_id)
    if not node:
        bot.answer_callback_query(call.id, "خطأ في القصة!")
        return
    
    markup = InlineKeyboardMarkup()
    for btn in node.get("buttons", []):
        markup.add(InlineKeyboardButton(
            text=btn["text"],
            callback_data=btn["next"]
        ))
    
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
        # لو فشل التعديل، أرسل جديد
        if image_url:
            bot.send_photo(call.message.chat.id, photo=image_url, caption=text, reply_markup=markup)
        else:
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
    
    bot.answer_callback_query(call.id)
    
    # إذا نهاية، أضف زر إعادة
    if node.get("end"):
        replay_markup = InlineKeyboardMarkup()
        replay_markup.add(InlineKeyboardButton("العب مرة أخرى", callback_data="start"))
        bot.send_message(call.message.chat.id, "هل تريد اللعب من جديد؟", reply_markup=replay_markup)

# Flask للـ Webhook
@app.route('/', methods=['GET', 'HEAD'])
def index():
    return ''

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)

if __name__ == '__main__':
    # إزالة webhook قديم إن وجد
    bot.remove_webhook()
    # إعداد webhook جديد
    bot.set_webhook(url=f"{APP_URL}/")
    
    # تشغيل Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
