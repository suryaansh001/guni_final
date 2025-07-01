#!/usr/bin/env python3
"""
Voice Assistant Server - Handles STT (with customized Whisper for 3 languages) and emotion analysis only
All other processing (LLM, TTS, database) is done client-side
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from transformers import pipeline
import tempfile
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from datetime import datetime
import whisper

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Voice Assistant Server API", version="2.0.0")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class VoiceAssistantServer:
    def __init__(self):
        # Initialize customized Whisper model for 3 languages
        try:
            logger.info("Loading customized Whisper model...")
            self.whisper_model = whisper.load_model("small")
            logger.info("Whisper model loaded successfully")
            
            # Define allowed languages (only 3 languages as per requirement)
            self.allowed_languages = {
                "en": "English",
                "hi": "Hindi", 
                "gu": "Gujarati"
            }
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model: {e}")
            self.whisper_model = None
        
        # Initialize Emotion Analysis
        try:
            self.emotion_analyzer = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                device=-1
            )
        except Exception as e:
            logger.error(f"Failed to load emotion model: {e}")
            self.emotion_analyzer = None

    def speech_to_text(self, audio_file_path: str) -> dict:
        """Convert speech to text using customized Whisper, restricted to English, Hindi, and Gujarati"""
        if not self.whisper_model:
            raise HTTPException(status_code=500, detail="Whisper model not initialized")
        
        try:
            logger.info(f"Processing audio for transcription: {audio_file_path}")
            
            # Load and process audio
            audio = whisper.load_audio(audio_file_path)
            audio = whisper.pad_or_trim(audio)
            mel = whisper.log_mel_spectrogram(audio).to(self.whisper_model.device)
            
            # Detect language (restricted to allowed languages)
            _, probs = self.whisper_model.detect_language(mel)
            filtered_probs = {lang: probs[lang] for lang in self.allowed_languages}
            detected_lang = max(filtered_probs, key=filtered_probs.get)
            lang_confidence = filtered_probs[detected_lang]
            
            logger.info(f"Detected language: {detected_lang} ({self.allowed_languages[detected_lang]}) with confidence {lang_confidence:.4f}")
            
            # Transcribe with detected language
            result = self.whisper_model.transcribe(
                audio_file_path, 
                language=detected_lang,
                fp16=False  # Ensure compatibility with CPU
            )
            
            transcribed_text = result["text"].strip()
            logger.info(f"Transcription result: '{transcribed_text}'")
            
            return {
                'text': transcribed_text,
                'language': detected_lang,
                'language_name': self.allowed_languages[detected_lang],
                'language_confidence': float(lang_confidence),
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Whisper transcription error: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                'text': '',
                'language': 'unknown',
                'success': False,
                'error': str(e)
            }
    
    def analyze_emotion(self, text: str) -> dict:
        """Analyze emotion from text"""
        if not self.emotion_analyzer:
            return {"emotion": "neutral", "confidence": 1.0}
        
        try:
            result = self.emotion_analyzer(text)
            emotion = result[0]['label'].lower()
            confidence = result[0]['score']
            
            logger.info(f"Emotion Analysis: {emotion} (confidence: {confidence:.2f})")
            return {"emotion": emotion, "confidence": confidence}
        except Exception as e:
            logger.error(f"Emotion analysis error: {e}")
            return {"emotion": "neutral", "confidence": 1.0}

# Initialize the voice assistant server
voice_assistant = VoiceAssistantServer()

@app.post("/transcribe_audio")
async def transcribe_audio(
    audio: UploadFile = File(...),
    user_name: str = Form(...)
):
    """Transcribe audio to text using customized Whisper for 3 languages"""
    temp_audio_path = None
    
    try:
        # Save uploaded audio file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            temp_audio_path = temp_audio.name
            content = await audio.read()
            temp_audio.write(content)
        
        # Speech to Text using customized Whisper
        logger.info(f"Transcribing audio for user: {user_name}")
        transcription_result = voice_assistant.speech_to_text(temp_audio_path)
        
        if not transcription_result['success']:
            return {
                "success": False,
                "error": transcription_result.get('error', 'Unknown transcription error'),
                "text": "",
                "language": "unknown",
                "language_name": "Unknown",
                "language_confidence": 0.0,
                "user_name": user_name,
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "success": True,
            "text": transcription_result['text'],
            "language": transcription_result['language'],
            "language_name": transcription_result['language_name'],
            "language_confidence": transcription_result['language_confidence'],
            "user_name": user_name,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return {
            "success": False,
            "error": str(e),
            "text": "",
            "language": "unknown",
            "language_name": "Unknown",
            "language_confidence": 0.0,
            "user_name": user_name,
            "timestamp": datetime.now().isoformat()
        }
    
    finally:
        # Clean up temporary file
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except Exception as cleanup_e:
                logger.error(f"Error cleaning up temp file: {cleanup_e}")

@app.post("/analyze_emotion")
async def analyze_emotion_endpoint(text_data: dict):
    """Analyze emotion from text"""
    try:
        text = text_data.get("text", "")
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text provided")
        
        result = voice_assistant.analyze_emotion(text)
        
        return {
            "success": True,
            "emotion": result["emotion"],
            "confidence": result["confidence"],
            "text": text,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error analyzing emotion: {e}")
        return {
            "success": False,
            "error": str(e),
            "emotion": "neutral",
            "confidence": 1.0,
            "timestamp": datetime.now().isoformat()
        }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "whisper_stt": voice_assistant.whisper_model is not None,
            "emotion_analyzer": voice_assistant.emotion_analyzer is not None
        },
        "supported_languages": voice_assistant.allowed_languages if voice_assistant.whisper_model else {},
        "note": "Server handles STT (Whisper) and emotion analysis only. LLM, TTS, and database operations are client-side."
    }

@app.get("/supported_languages")
async def get_supported_languages():
    """Get list of supported languages"""
    if not voice_assistant.whisper_model:
        return {"error": "Whisper model not available"}
    
    return {
        "supported_languages": voice_assistant.allowed_languages,
        "total_languages": len(voice_assistant.allowed_languages)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)