import os
import json
import requests
from flask import Flask, request, abort

TOKEN = os.environ.get('TELEGRAM_TOKEN')
APP_URL = os.environ.get('APP_URL')

if not TOKEN or not APP_URL:
    raise ValueError("❌ TELEGRAM_TOKEN and APP_URL must be set")

app = Flask(__name__)

# ========== دوال مساعدة ==========
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    requests.post(url, json=payload)
    print(f"📤 تم إرسال رسالة إلى {chat_id}: {text[:50]}...")

# ========== معالج webhook الرئيسي ==========
@app.route('/', methods=['POST'])
def webhook():
    try:
        data = request.get_json()
        print("📨 تم استلام تحديث:", data)
        
        # التحقق من وجود رسالة
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            print(f"💬 رسالة من {chat_id}: {text}")
            
            # الرد على الرسالة
            if text == "/start":
                send_message(chat_id, "✅ البوت يعمل! هذا رد على /start")
            else:
                send_message(chat_id, f"أرسلت: {text}")
        
        return "OK", 200
    except Exception as e:
        print(f"❌ خطأ: {e}")
        return "Error", 500

@app.route('/', methods=['GET'])
def index():
    return 'Bot is running with direct API'

@app.route('/setup')
def setup_webhook():
    """صفحة لإعداد webhook يدوياً"""
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={APP_URL}/"
    response = requests.get(url)
    return {
        "setup": response.json(),
        "webhook_url": f"{APP_URL}/"
    }

@app.route('/info')
def webhook_info():
    """صفحة لمعلومات webhook"""
    url = f"https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
    response = requests.get(url)
    return response.json()

# ========== إعداد webhook عند بدء التشغيل ==========
def setup():
    print("🔧 جاري إعداد webhook...")
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={APP_URL}/"
    response = requests.get(url).json()
    print("🔧 نتيجة الإعداد:", response)

setup()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
