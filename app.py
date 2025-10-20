"""
Flask Backend API - Sesli AI Chatbot
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from elevenlabs.client import ElevenLabs
import openai
import os
import base64

# Flask app
app = Flask(__name__, static_folder='static')
CORS(app)

# API Clients (Environment variables'dan okuyacak)
ELEVENLABS_KEY = os.getenv('ELEVENLABS_API_KEY')
OPENAI_KEY = os.getenv('OPENAI_API_KEY')

if ELEVENLABS_KEY:
    elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_KEY)
else:
    elevenlabs_client = None

if OPENAI_KEY:
    openai.api_key = OPENAI_KEY

# Config
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel
MODEL_ID = "eleven_monolingual_v1"

@app.route('/')
def index():
    """Ana sayfa"""
    return send_from_directory('static', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Chatbot endpoint
    Request: {"message": "user message"}
    Response: {"text": "bot response", "audio": "base64_audio_data"}
    """
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'Mesaj boş olamaz'}), 400
        
        # 1. OpenAI'dan metin yanıt al
        bot_response = get_chatgpt_response(user_message)
        
        # 2. ElevenLabs ile sese çevir
        audio_data = text_to_speech(bot_response)
        
        # 3. Base64'e çevir (frontend için)
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        audio_url = f"data:audio/mpeg;base64,{audio_base64}"
        
        return jsonify({
            'success': True,
            'text': bot_response,
            'audio': audio_url
        })
        
    except Exception as e:
        print(f"Hata: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_chatgpt_response(message):
    """OpenAI ChatGPT'den yanıt al"""
    try:
        if not OPENAI_KEY:
            return "OpenAI API anahtarı yapılandırılmamış."
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Sen yardımcı ve samimi bir Türkçe AI asistanısın. Kısa ve net yanıtlar ver."},
                {"role": "user", "content": message}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"OpenAI Hatası: {e}")
        return "Üzgünüm, şu anda yanıt üretemiyorum. Lütfen tekrar deneyin."

def text_to_speech(text):
    """ElevenLabs ile metni sese çevir"""
    try:
        if not elevenlabs_client:
            raise Exception("ElevenLabs API anahtarı yapılandırılmamış")
        
        # Yeni API syntax
        audio_generator = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id=MODEL_ID
        )
        
        # Generator'dan bytes'a çevir
        audio_bytes = b''.join(audio_generator)
        return audio_bytes
        
    except Exception as e:
        print(f"ElevenLabs Hatası: {e}")
        raise

@app.route('/api/voices', methods=['GET'])
def get_voices():
    """Mevcut sesleri listele"""
    try:
        if not elevenlabs_client:
            return jsonify({'error': 'ElevenLabs API anahtarı yapılandırılmamış'}), 500
        
        voices = elevenlabs_client.voices.get_all()
        voice_list = [
            {
                'name': voice.name,
                'voice_id': voice.voice_id
            }
            for voice in voices.voices
        ]
        return jsonify({'voices': voice_list})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'elevenlabs': 'connected' if ELEVENLABS_KEY else 'not configured',
        'openai': 'connected' if OPENAI_KEY else 'not configured'
    })

if __name__ == '__main__':
    # Production için
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)