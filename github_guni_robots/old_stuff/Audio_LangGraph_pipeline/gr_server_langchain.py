#!/usr/bin/env python3
"""
FastAPI Audio Processing Server with Face Recognition, AssemblyAI STT, Groq LLM, and LangGraph
Handles Face Recognition -> STT -> Emotion Analysis -> LLM (Groq) -> TTS pipeline with conversation history
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import StreamingResponse
from transformers import pipeline
import tempfile
import os
import io
import logging
from typing import Optional, Dict, List, TypedDict
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from contextlib import contextmanager
from groq import Groq
import assemblyai as aai
from langgraph.graph import StateGraph

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure AssemblyAI
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

app = FastAPI(title="Voice Assistant with Face Recognition API", version="1.0.0")

class DatabaseManager:
    def __init__(self, db_path: str = "voice_assistant.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table for face recognition data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    face_encoding BLOB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Chat sessions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    session_date DATE NOT NULL,
                    summary TEXT,
                    raw_conversations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_name) REFERENCES users (name)
                )
            ''')
            
            # Individual conversations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    emotion TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                )
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get_user_summary(self, user_name: str) -> Optional[str]:
        """Get the latest chat summary for a user"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT summary FROM chat_sessions 
                WHERE user_name = ? AND summary IS NOT NULL
                ORDER BY updated_at DESC LIMIT 1
            ''', (user_name,))
            result = cursor.fetchone()
            return result['summary'] if result else None
    
    def get_or_create_session(self, user_name: str) -> int:
        """Get today's session or create a new one"""
        today = datetime.now().date()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if session exists for today
            cursor.execute('''
                SELECT id FROM chat_sessions 
                WHERE user_name = ? AND session_date = ?
            ''', (user_name, today))
            result = cursor.fetchone()
            
            if result:
                return result['id']
            
            # Create new session
            cursor.execute('''
                INSERT INTO chat_sessions (user_name, session_date, raw_conversations)
                VALUES (?, ?, ?)
            ''', (user_name, today, '[]'))
            conn.commit()
            return cursor.lastrowid
    
    def add_conversation(self, session_id: int, user_input: str, ai_response: str, emotion: str):
        """Add a conversation to the session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Insert conversation
            cursor.execute('''
                INSERT INTO conversations (session_id, user_input, ai_response, emotion)
                VALUES (?, ?, ?, ?)
            ''', (session_id, user_input, ai_response, emotion))
            
            # Update raw conversations in session
            cursor.execute('SELECT raw_conversations FROM chat_sessions WHERE id = ?', (session_id,))
            current_conversations = json.loads(cursor.fetchone()['raw_conversations'])
            
            current_conversations.append({
                'timestamp': datetime.now().isoformat(),
                'user_input': user_input,
                'ai_response': ai_response,
                'emotion': emotion
            })
            
            cursor.execute('''
                UPDATE chat_sessions SET raw_conversations = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (json.dumps(current_conversations), session_id))
            
            conn.commit()
    
    def get_session_conversations(self, session_id: int) -> List[Dict]:
        """Get all conversations for a session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT raw_conversations FROM chat_sessions WHERE id = ?', (session_id,))
            result = cursor.fetchone()
            return json.loads(result['raw_conversations']) if result else []
    
    def update_session_summary(self, session_id: int, summary: str):
        """Update the summary for a session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_sessions SET summary = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (summary, session_id))
            conn.commit()

class VoiceAssistant:
    def __init__(self):
        # API Keys
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        # Initialize Groq client for LLM and TTS
        if self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)
        else:
            self.groq_client = None
            logger.warning("GROQ_API_KEY not found. LLM and TTS functionality will be limited.")
        
        # Check AssemblyAI API key
        if not self.assemblyai_api_key:
            logger.warning("ASSEMBLYAI_API_KEY not found. STT functionality will be limited.")
        
        # Initialize Emotion Analysis Pipeline
        try:
            self.emotion_analyzer = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                device=-1
            )
        except Exception as e:
            logger.error(f"Failed to load emotion model: {e}")
            self.emotion_analyzer = None
        
        # TTS Configuration
        self.tts_voice_name = "Fritz-PlayAI"
        self.tts_model = "playai-tts"
        
        # LLM Configuration
        self.llm_model = "llama-3.3-70b-versatile"
        
        # Database Manager
        self.db = DatabaseManager()

    def speech_to_text(self, audio_file_path: str) -> str:
        """Convert speech to text using AssemblyAI"""
        if not self.assemblyai_api_key:
            raise HTTPException(status_code=500, detail="AssemblyAI API key not configured")
        
        try:
            config = aai.TranscriptionConfig(speech_model=aai.SpeechModel.best)
            transcript = aai.Transcriber(config=config).transcribe(audio_file_path)
            
            if transcript.status == "error":
                logger.error(f"AssemblyAI Transcription Error: {transcript.error}")
                raise HTTPException(status_code=500, detail=f"Speech recognition failed: {transcript.error}")
            
            logger.info(f"STT Result: {transcript.text}")
            return transcript.text
        
        except Exception as e:
            logger.error(f"AssemblyAI STT Error: {e}")
            raise HTTPException(status_code=500, detail=f"Speech recognition service error: {str(e)}")
    
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
    
    def text_to_speech(self, text: str, emotion: str) -> bytes:
        """Convert text to speech using Groq's PlayAI TTS"""
        if not self.groq_client:
            raise HTTPException(status_code=500, detail="Groq client not initialized (API key missing?)")
        
        try:
            speech_response = self.groq_client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice_name,
                input=text,
                response_format="mp3"
            )
            
            audio_content = speech_response.read()
            
            if audio_content:
                logger.info(f"TTS Success for emotion: {emotion}")
                return audio_content
            else:
                logger.error("TTS returned no audio content.")
                raise HTTPException(status_code=500, detail="Text-to-speech generation failed")
                
        except Exception as e:
            logger.error(f"TTS Error: {e}")
            raise HTTPException(status_code=500, detail=f"Text-to-speech service error: {str(e)}")
    
    def summarize_conversations(self, conversations: List[Dict]) -> str:
        """Summarize a list of conversations using Groq"""
        if not self.groq_client or not conversations:
            return "No conversations to summarize."
        
        try:
            # Prepare conversation text
            conversation_text = ""
            for conv in conversations:
                conversation_text += f"User: {conv['user_input']}\nAssistant: {conv['ai_response']}\n\n"
            
            system_prompt = """You are tasked with creating a concise summary of a conversation session. 
            
            Create a summary that captures:
            1. Main topics discussed
            2. User's emotional state and concerns
            3. Key information or decisions made
            4. Any ongoing issues or follow-ups needed
            
            Keep the summary concise but informative (max 3-4 sentences).
            
            Conversation to summarize:"""
            
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_text}
                ],
                model=self.llm_model,
                temperature=0.3,
                max_tokens=200
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Summarization Error: {e}")
            return "Error generating conversation summary."

# Initialize the voice assistant
voice_assistant = VoiceAssistant()

# Define PipelineState for LangGraph
class PipelineState(TypedDict):
    audio_path: Optional[str]
    transcribed_text: Optional[str]
    emotion: Optional[str]
    ai_response: Optional[str]
    messages: List[dict]
    user_name: str
    session_id: int

# Define nodes for LangGraph
def stt_node(state: PipelineState) -> PipelineState:
    state["transcribed_text"] = voice_assistant.speech_to_text(state["audio_path"])
    return state

def analyze_emotion_node(state: PipelineState) -> PipelineState:
    emotion_result = voice_assistant.analyze_emotion(state["transcribed_text"])
    state["emotion"] = emotion_result["emotion"]
    return state

def response_node(state: PipelineState) -> PipelineState:
    system_prompt = f"""You are a helpful and emotionally intelligent voice assistant talking to {state['user_name']}.

EMOTIONAL CONTEXT: {state['emotion']}

INSTRUCTIONS:
- Keep responses conversational and concise (2-3 sentences max)
- Address the user by name when appropriate
- Match the user's emotional tone while being helpful and supportive
- Reference previous conversation context when relevant
- Respond as if you're having a natural voice conversation"""

    messages = [{"role": "system", "content": system_prompt}] + state["messages"] + [{"role": "user", "content": state["transcribed_text"]}]
    response = voice_assistant.groq_client.chat.completions.create(
        messages=messages,
        model=voice_assistant.llm_model,
        temperature=0.7,
        max_tokens=150
    )
    ai_response = response.choices[0].message.content.strip()
    state["ai_response"] = ai_response
    state["messages"].append({"role": "user", "content": state["transcribed_text"]})
    state["messages"].append({"role": "assistant", "content": ai_response})
    return state

# Build the graph
graph = StateGraph(PipelineState)
graph.add_node("stt", stt_node)
graph.add_node("analyze_emotion", analyze_emotion_node)
graph.add_node("response", response_node)
graph.add_edge("stt", "analyze_emotion")
graph.add_edge("analyze_emotion", "response")
graph.set_entry_point("stt")
graph.set_finish_point("response")
pipeline_app = graph.compile()

@app.get("/")
async def root():
    return {"message": "Voice Assistant with Face Recognition API is running!"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "stt": "available" if voice_assistant.assemblyai_api_key else "unavailable",
            "emotion_analysis": "available" if voice_assistant.emotion_analyzer else "unavailable",
            "llm_groq": "available" if voice_assistant.groq_client else "unavailable",
            "tts_groq": "available" if voice_assistant.groq_client else "unavailable",
            "database": "available"
        }
    }

@app.post("/process-audio")
async def process_audio(
    audio: UploadFile = File(...),
    user_name: str = Form(...)
):
    """Main pipeline: STT -> Emotion Analysis -> LLM -> TTS with LangGraph for conversation history"""
    
    if not audio.filename.endswith(('.wav', '.mp3', '.m4a', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    try:
        # Save uploaded audio to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            content = await audio.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        logger.info(f"Processing audio pipeline for user: {user_name}")
        
        # Get or create today's session using user_name as thread_id equivalent
        session_id = voice_assistant.db.get_or_create_session(user_name)
        
        # Load conversation history
        conversations = voice_assistant.db.get_session_conversations(session_id)
        messages = []
        for conv in conversations:
            messages.append({"role": "user", "content": conv["user_input"]})
            messages.append({"role": "assistant", "content": conv["ai_response"]})
        
        # Set initial state for LangGraph
        initial_state = PipelineState(
            audio_path=temp_audio_path,
            transcribed_text=None,
            emotion=None,
            ai_response=None,
            messages=messages,
            user_name=user_name,
            session_id=session_id
        )
        
        # Run the pipeline with LangGraph
        final_state = pipeline_app.invoke(initial_state)
        
        # Add new conversation to database
        voice_assistant.db.add_conversation(
            session_id,
            final_state["transcribed_text"],
            final_state["ai_response"],
            final_state["emotion"]
        )
        
        # Perform Text-to-Speech
        audio_response = voice_assistant.text_to_speech(final_state["ai_response"], final_state["emotion"])
        
        # Clean up temporary file
        os.unlink(temp_audio_path)
        
        logger.info("Pipeline completed successfully")
        
        # Return audio response with metadata
        return StreamingResponse(
            io.BytesIO(audio_response),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=response.mp3",
                "X-User": user_name,
                "X-Transcription": final_state["transcribed_text"],
                "X-Emotion": final_state["emotion"],
                "X-Response": final_state["ai_response"],
                "X-Session-ID": str(session_id)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline Error: {e}")
        if 'temp_audio_path' in locals():
            try:
                os.unlink(temp_audio_path)
            except Exception as cleanup_e:
                logger.error(f"Error cleaning up temp file: {cleanup_e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/summarize-session/{session_id}")
async def summarize_session(session_id: int):
    """Summarize conversations for a specific session"""
    try:
        # Get conversations for the session
        conversations = voice_assistant.db.get_session_conversations(session_id)
        
        if not conversations:
            raise HTTPException(status_code=404, detail="No conversations found for this session")
        
        # Generate summary
        summary = voice_assistant.summarize_conversations(conversations)
        
        # Update session with summary
        voice_assistant.db.update_session_summary(session_id, summary)
        
        return {
            "session_id": session_id,
            "summary": summary,
            "conversation_count": len(conversations)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Summarization Error: {e}")
        raise HTTPException(status_code=500, detail=f"Summarization failed: {str(e)}")

@app.get("/user-summary/{user_name}")
async def get_user_summary(user_name: str):
    """Get the latest summary for a user"""
    summary = voice_assistant.db.get_user_summary(user_name)
    
    if not summary:
        return {"user_name": user_name, "summary": "No previous conversations found"}
    
    return {"user_name": user_name, "summary": summary}

@app.post("/test-tts")
async def test_tts(text: str, emotion: str = "neutral"):
    """Test endpoint for TTS functionality"""
    try:
        audio_response = voice_assistant.text_to_speech(text, emotion)
        return StreamingResponse(
            io.BytesIO(audio_response),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "attachment; filename=test_tts.mp3"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

