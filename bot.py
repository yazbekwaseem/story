import os
import json
import requests
from flask import Flask, request

TOKEN = os.environ.get('TELEGRAM_TOKEN')
APP_URL = os.environ.get('APP_URL')

if not TOKEN or not APP_URL:
    raise ValueError("❌ TELEGRAM_TOKEN and APP_URL must be set")

app = Flask(__name__)

# تحميل القصة
try:
    with open("story.json", encoding="utf-8") as f:
        STORY = json.load(f)
    print("✅ story.json loaded successfully")
except Exception as e:
    print("❌ Error loading story.json:", e)
    STORY = {"intro": {"text": "⚠️ خطأ في تحميل القصة", "buttons": []}}

user_states = {}

# ========== دوال مساعدة ==========
def send_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if buttons:
        keyboard = {
            "inline_keyboard": [[{"text": btn["text"], "callback_data": btn["next"]}] 
                               for btn in buttons]
        }
        payload["reply_markup"] = keyboard
    
    response = requests.post(url, json=payload)
    print(f"📤 تم إرسال رسالة إلى {chat_id}")
    return response.json()

def send_photo(chat_id, photo_url, caption, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
    payload = {
        "chat_id": chat_id,
        "photo": photo_url,
        "caption": caption,
        "parse_mode": "HTML"
    }
    
    if buttons:
        keyboard = {
            "inline_keyboard": [[{"text": btn["text"], "callback_data": btn["next"]}] 
                               for btn in buttons]
        }
        payload["reply_markup"] = keyboard
    
    response = requests.post(url, json=payload)
    print(f"📤 تم إرسال صورة إلى {chat_id}")
    return response.json()

def edit_message(chat_id, message_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }
    
    if buttons:
        keyboard = {
            "inline_keyboard": [[{"text": btn["text"], "callback_data": btn["next"]}] 
                               for btn in buttons]
        }
        payload["reply_markup"] = keyboard
    
    response = requests.post(url, json=payload)
    return response.json()

def answer_callback(callback_id, text=""):
    url = f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery"
    payload = {
        "callback_query_id": callback_id,
        "text": text
    }
    requests.post(url, json=payload)

# ========== معالج webhook ==========
@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print("📨 تحديث:", data.get("update_id"))
        
        # معالجة الرسائل
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            if text == "/start":
                node_id = STORY.get("start", "intro")
                node = STORY.get(node_id, {})
                user_states[chat_id] = node_id
                
                if node.get("image"):
                    send_photo(chat_id, node["image"], node["text"], node.get("buttons", []))
                else:
                    send_message(chat_id, node["text"], node.get("buttons", []))
        
        # معالجة الـ Callback Queries
        elif "callback_query" in data:
            callback = data["callback_query"]
            callback_id = callback["id"]
            chat_id = callback["message"]["chat"]["id"]
            message_id = callback["message"]["message_id"]
            data = callback["data"]
            
            print(f"📞 Callback: {data} from {chat_id}")
            
            if data == "start":
                # إعادة تشغيل القصة
                node_id = STORY.get("start", "intro")
                node = STORY.get(node_id, {})
                user_states[chat_id] = node_id
                
                if node.get("image"):
                    send_photo(chat_id, node["image"], node["text"], node.get("buttons", []))
                else:
                    send_message(chat_id, node["text"], node.get("buttons", []))
            else:
                # الانتقال إلى العقدة التالية
                node = STORY.get(data, {})
                if node:
                    user_states[chat_id] = data
                    
                    # محاولة تعديل الرسالة الحالية
                    if node.get("image"):
                        # لا يمكن تعديل الصورة بسهولة، نرسل رسالة جديدة
                        send_photo(chat_id, node["image"], node["text"], node.get("buttons", []))
                    else:
                        edit_message(chat_id, message_id, node["text"], node.get("buttons", []))
                    
                    if node.get("end"):
                        # نهاية القصة
                        keyboard = {
                            "inline_keyboard": [[{"text": "🔄 العب مرة أخرى", "callback_data": "start"}]]
                        }
                        send_message(chat_id, "🏁 انتهت القصة!", keyboard)
                
                answer_callback(callback_id)
        
        return "OK", 200
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return "Error", 500

@app.route('/', methods=['GET'])
def index():
    return 'Story Bot is running'

@app.route('/setup')
def setup_webhook():
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={APP_URL}/"
    response = requests.get(url)
    return {"setup": response.json()}

# ========== إعداد webhook ==========
print("🔧 جاري إعداد webhook...")
response = requests.get(f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={APP_URL}/")
print("🔧 نتيجة:", response.json())

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
