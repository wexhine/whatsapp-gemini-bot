from flask import Flask, request, jsonify
import requests
import os
from google import generativeai as genai

app = Flask(__name__)

# Configuration - Set these in Render environment variables
WHATSAPP_TOKEN = os.getenv('WHATSAPP_TOKEN')
PHONE_NUMBER_ID = os.getenv('PHONE_NUMBER_ID')
WEBHOOK_VERIFY_TOKEN = os.getenv('WEBHOOK_VERIFY_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def send_whatsapp_message(phone_number, message):
    """Send a message via WhatsApp Business API"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "text": {"body": message}
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()

def get_gemini_response(user_message):
    """Get response from Gemini AI"""
    try:
        response = model.generate_content(user_message)
        return response.text
    except Exception as e:
        return f"Sorry, I couldn't process that. Error: {str(e)}"

@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """Verify webhook for WhatsApp"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    if mode == 'subscribe' and token == WEBHOOK_VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
    else:
        return 'Forbidden', 403

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming WhatsApp messages"""
    try:
        data = request.get_json()
        
        # Check if it's a message event
        if data.get('object') == 'whatsapp_business_account':
            entries = data.get('entry', [])
            
            for entry in entries:
                changes = entry.get('changes', [])
                
                for change in changes:
                    value = change.get('value', {})
                    messages = value.get('messages', [])
                    
                    for message in messages:
                        # Get sender's phone number and message text
                        from_number = message.get('from')
                        message_body = message.get('text', {}).get('body')
                        
                        if message_body:
                            print(f"Received message from {from_number}: {message_body}")
                            
                            # Get AI response
                            ai_response = get_gemini_response(message_body)
                            
                            # Send response back
                            send_whatsapp_message(from_number, ai_response)
        
        return jsonify({"status": "success"}), 200
    
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/')
def home():
    return "WhatsApp Gemini Bot is running! 🤖", 200

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
