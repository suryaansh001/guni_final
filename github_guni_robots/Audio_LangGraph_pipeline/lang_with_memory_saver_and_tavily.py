#!/usr/bin/env python3
"""
FastAPI Voice Assistant with LangGraph MemorySaver, Tavily Search, and User Profile Upload
Handles STT -> Emotion Analysis -> Tavily Search -> LLM -> TTS pipeline with chat summaries and user profiles
Includes endpoint for receiving face recognition subject name
"""

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Query
from fastapi.responses import StreamingResponse
from transformers import pipeline
import tempfile
import os
import io
import logging
from typing import Optional, Dict, List, TypedDict, Annotated
from dotenv import load_dotenv
import json
from datetime import datetime
import sqlite3
from contextlib import contextmanager
from groq import Groq
import assemblyai as aai
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.tools.tavily_search import TavilySearchResults
import httpx
import base64

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure AssemblyAI
aai.settings.api_key = os.getenv("ASSEMBLYAI_API_KEY")

# Configure Tavily
tavily_api_key = os.getenv("TAVILY_API_KEY")
if not tavily_api_key:
    logger.warning("TAVILY_API_KEY not found. Search functionality will be limited.")

app = FastAPI(title="Voice Assistant with MemorySaver API", version="1.0.0")

class DatabaseManager:
    def __init__(self, db_path: str = "voice_assistant.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    session_date DATE NOT NULL,
                    raw_conversations TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_name) REFERENCES users (name)
                )
            ''')
            
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT UNIQUE NOT NULL,
                    face_photo TEXT, -- Base64-encoded image
                    info TEXT, -- JSON string of additional info
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_name) REFERENCES users (name)
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
    
    def get_or_create_session(self, user_name: str) -> int:
        """Get today's session or create a new one"""
        today = datetime.now().date()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('INSERT OR IGNORE INTO users (name) VALUES (?)', (user_name,))
            
            cursor.execute('''
                SELECT id FROM chat_sessions 
                WHERE user_name = ? AND session_date = ?
            ''', (user_name, today))
            result = cursor.fetchone()
            
            if result:
                return result['id']
            
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
            
            cursor.execute('''
                INSERT INTO conversations (session_id, user_input, ai_response, emotion)
                VALUES (?, ?, ?, ?)
            ''', (session_id, user_input, ai_response, emotion))
            
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
    
    def save_user_profile(self, user_name: str, face_photo: str, info: Dict) -> None:
        """Save or update user profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('INSERT OR IGNORE INTO users (name) VALUES (?)', (user_name,))
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles (user_name, face_photo, info, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_name, face_photo, json.dumps(info)))
            
            conn.commit()
            logger.info(f"Saved profile for user: {user_name}")
    
    def get_user_profile(self, user_name: str) -> Optional[Dict]:
        """Retrieve user profile"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT face_photo, info FROM user_profiles WHERE user_name = ?
            ''', (user_name,))
            result = cursor.fetchone()
            if result:
                return {
                    "face_photo": result['face_photo'],
                    "info": json.loads(result['info'])
                }
            return None
    
    def update_user_name(self, old_name: str, new_name: str) -> None:
        """Update user name across all relevant tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('UPDATE users SET name = ? WHERE name = ?', (new_name, old_name))
            cursor.execute('UPDATE chat_sessions SET user_name = ? WHERE user_name = ?', (new_name, old_name))
            cursor.execute('UPDATE user_profiles SET user_name = ? WHERE user_name = ?', (new_name, old_name))
            
            conn.commit()
            logger.info(f"Updated user name from {old_name} to {new_name}")

class VoiceAssistant:
    def __init__(self):
        # API Keys
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        
        # Initialize Groq client with custom HTTP client
        if self.groq_api_key:
            try:
                self.groq_client = Groq(
                    api_key=self.groq_api_key,
                    http_client=httpx.Client(timeout=30.0)
                )
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self.groq_client = None
        else:
            self.groq_client = None
            logger.warning("GROQ_API_KEY not found. LLM and TTS functionality will be limited.")
        
        # Initialize Tavily tool
        self.tavily_tool = TavilySearchResults(max_results=2) if tavily_api_key else None
        
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
        
        # TTS Configuration
        self.tts_voice_name = "Fritz-PlayAI"
        self.tts_model = "playai-tts"
        
        # LLM Configuration
        self.llm_model = "llama-3.3-70b-versatile"
        
        # Database Manager
        self.db = DatabaseManager()
        
        # Store current user name
        self.current_user_name = None

    def set_user_name(self, user_name: str):
        """Set or update the current user name"""
        if self.current_user_name and self.current_user_name != user_name:
            self.db.update_user_name(self.current_user_name, user_name)
        self.current_user_name = user_name
        logger.info(f"Set current user name to: {user_name}")

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
        """Convert text to speech using Groq's TTS API via HTTP"""
        if not self.groq_api_key:
            raise HTTPException(status_code=500, detail="GROQ_API_KEY not configured")
        temp_audio_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
                temp_audio_path = temp_audio.name
            logger.info(f"TTS Request - Text: '{text}', Voice: {self.tts_voice_name}, Model: {self.tts_model}")
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": self.tts_model,
                "voice": self.tts_voice_name,
                "input": text,
                "response_format": "wav"
            }
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/audio/speech",
                    headers=headers,
                    json=payload
                )
            if response.status_code != 200:
                logger.error(f"TTS HTTP Error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"TTS API error: {response.text}")
            with open(temp_audio_path, 'wb') as f:
                f.write(response.content)
            logger.info(f"Audio written to temporary file: {temp_audio_path}")
            if not os.path.exists(temp_audio_path):
                raise HTTPException(status_code=500, detail="TTS audio file was not created")
            file_size = os.path.getsize(temp_audio_path)
            logger.info(f"Generated audio file size: {file_size} bytes")
            if file_size == 0:
                raise HTTPException(status_code=500, detail="TTS generated empty audio file")
            with open(temp_audio_path, 'rb') as audio_file:
                audio_content = audio_file.read()
            logger.info(f"TTS Success for emotion: {emotion}, final audio size: {len(audio_content)} bytes")
            return audio_content
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"TTS Error: {str(e)}")
            import traceback
            logger.error(f"TTS Error traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Text-to-speech service error: {str(e)}")
        finally:
            if temp_audio_path and os.path.exists(temp_audio_path):
                try:
                    os.unlink(temp_audio_path)
                    logger.info(f"Cleaned up temporary TTS file: {temp_audio_path}")
                except Exception as cleanup_e:
                    logger.error(f"Error cleaning up TTS temp file: {cleanup_e}")
    
    def summarize_conversations(self, conversations: List[Dict]) -> str:
        """Summarize a list of conversations using Groq"""
        if not self.groq_client or not conversations:
            return "No conversations to summarize."
        
        try:
            logger.info(f"Conversations for summary: {json.dumps(conversations, indent=2)}")
            conversation_text = ""
            for conv in conversations:
                conversation_text += f"User: {conv['user_input']}\nAssistant: {conv['ai_response']}\n\n"
            
            system_prompt = """Create a concise summary (1-2 sentences) capturing:
            1. Main topics discussed
            2. User's emotional state
            3. Any key actions or follow-ups
            
            Conversation to summarize:"""
            
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": conversation_text}
                ],
                model=self.llm_model,
                temperature=0.3,
                max_tokens=100
            )
            
            summary = response.choices[0].message.content.strip()
            logger.info(f"Generated summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error(f"Summarization Error: {e}")
            return "Error generating conversation summary."

# Initialize the voice assistant
voice_assistant = VoiceAssistant()

# Define State for LangGraph
class PipelineState(TypedDict):
    audio_path: Optional[str]
    transcribed_text: Optional[str]
    emotion: Optional[str]
    ai_response: Optional[str]
    messages: Annotated[List[Dict], add_messages]
    user_name: str
    session_id: int
    summary: str

# Define nodes for LangGraph
def stt_node(state: PipelineState) -> PipelineState:
    state["transcribed_text"] = voice_assistant.speech_to_text(state["audio_path"])
    return state

def analyze_emotion_node(state: PipelineState) -> PipelineState:
    emotion_result = voice_assistant.analyze_emotion(state["transcribed_text"])
    state["emotion"] = emotion_result["emotion"]
    return state

def chatbot_node(state: PipelineState) -> PipelineState:
    logger.info(f"Loaded summary for chatbot: {state['summary']}")
    profile = voice_assistant.db.get_user_profile(state["user_name"])
    profile_info = ""
    if profile:
        info = profile["info"]
        profile_info = f"User Profile: Name: {state['user_name']}, Hobbies: {info.get('hobbies', []):}, Background: {info.get('background', 'N/A')}, Preferences: {info.get('preferences', 'N/A')}"
    
    system_prompt = f"""You are a helpful and emotionally intelligent voice assistant talking to {state['user_name']}.

EMOTIONAL CONTEXT: {state['emotion']}
{profile_info}
Previous conversation summary: {state['summary'] or 'No previous summary available.'}

INSTRUCTIONS:
- Keep responses conversational and concise (2-3 sentences max)
- Address the user by name when appropriate
- Match the user's emotional tone while being helpful
- For queries starting with 'What' or 'Who', perform a search using the Tavily tool
- Respond naturally as if in a voice conversation, using profile info when relevant"""

    valid_messages = [
        msg for msg in state["messages"]
        if isinstance(msg, dict) and "role" in msg and "content" in msg
    ]
    
    messages = [
        {"role": "system", "content": system_prompt}
    ] + valid_messages + [
        {"role": "user", "content": state["transcribed_text"]}
    ]
    
    logger.info(f"Messages sent to Groq: {json.dumps(messages, indent=2)}")
    
    try:
        if voice_assistant.tavily_tool and state["transcribed_text"].lower().startswith(("what", "who")):
            search_results = voice_assistant.tavily_tool.invoke({"query": state["transcribed_text"]})
            messages.append({"role": "tool", "content": json.dumps(search_results)})
            logger.info(f"Messages after Tavily search: {json.dumps(messages, indent=2)}")
            response = voice_assistant.groq_client.chat.completions.create(
                messages=messages,
                model=voice_assistant.llm_model,
                temperature=0.7,
                max_tokens=150
            )
            state["ai_response"] = response.choices[0].message.content.strip()
        else:
            response = voice_assistant.groq_client.chat.completions.create(
                messages=messages,
                model=voice_assistant.llm_model,
                temperature=0.7,
                max_tokens=150
            )
            state["ai_response"] = response.choices[0].message.content.strip()
        
        state["messages"] = valid_messages + [
            {"role": "user", "content": state["transcribed_text"]},
            {"role": "assistant", "content": state["ai_response"]}
        ]
    except Exception as e:
        logger.error(f"Chatbot node error: {e}")
        state["ai_response"] = f"I apologize, {state['user_name']}, but I'm having trouble processing your request right now. Please try again."
        state["messages"] = valid_messages + [
            {"role": "user", "content": state["transcribed_text"]},
            {"role": "assistant", "content": state["ai_response"]}
        ]
    
    return state

def summarize_node(state: PipelineState) -> PipelineState:
    try:
        conversations = voice_assistant.db.get_session_conversations(state["session_id"])
        if conversations:
            summary = voice_assistant.summarize_conversations(conversations)
            state["summary"] = summary
            logger.info(f"Updated summary in state: {summary}")
        else:
            state["summary"] = "No conversations to summarize."
            logger.info("No conversations found for summarization.")
    except Exception as e:
        logger.error(f"Summarize node error: {e}")
        state["summary"] = "Error generating summary."
    
    return state

# Build the graph
graph_builder = StateGraph(PipelineState)
graph_builder.add_node("stt", stt_node)
graph_builder.add_node("analyze_emotion", analyze_emotion_node)
graph_builder.add_node("chatbot", chatbot_node)
graph_builder.add_node("summarize", summarize_node)

graph_builder.add_edge("stt", "analyze_emotion")
graph_builder.add_edge("analyze_emotion", "chatbot")
graph_builder.add_edge("chatbot", "summarize")
graph_builder.add_edge("summarize", END)
graph_builder.set_entry_point("stt")

# Initialize MemorySaver
memory = MemorySaver()
pipeline_app = graph_builder.compile(checkpointer=memory)

@app.get("/")
async def root():
    return {"message": "Voice Assistant with MemorySaver API is running!"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "services": {
            "stt": "available" if voice_assistant.assemblyai_api_key else "unavailable",
            "emotion_analysis": "available" if voice_assistant.emotion_analyzer else "unavailable",
            "llm_groq": "available" if voice_assistant.groq_client else "unavailable",
            "tts_groq": "available" if voice_assistant.groq_client else "unavailable",
            "tavily_search": "available" if voice_assistant.tavily_tool else "unavailable",
            "database": "available"
        }
    }

@app.post("/process-audio")
async def process_audio(
    audio: UploadFile = File(...),
    user_name: str = Form(...),
    thread_id: str = Form(...)
):
    if not audio.filename.endswith(('.wav', '.mp3', '.m4a', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format")
    
    temp_audio_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_audio:
            content = await audio.read()
            temp_audio.write(content)
            temp_audio_path = temp_audio.name
        
        logger.info(f"Processing audio pipeline for user: {user_name}, thread_id: {thread_id}")
        
        session_id = voice_assistant.db.get_or_create_session(user_name)
        
        checkpoint = memory.get({"configurable": {"thread_id": thread_id}})
        initial_summary = checkpoint["channel_values"].get("summary", "") if checkpoint else ""
        logger.info(f"Loaded initial summary for thread_id {thread_id}: {initial_summary}")
        
        initial_state = PipelineState(
            audio_path=temp_audio_path,
            transcribed_text=None,
            emotion=None,
            ai_response=None,
            messages=[],
            user_name=user_name,
            session_id=session_id,
            summary=initial_summary
        )
        
        final_state = pipeline_app.invoke(
            initial_state,
            config={"configurable": {"thread_id": thread_id}}
        )
        
        voice_assistant.db.add_conversation(
            session_id,
            final_state["transcribed_text"],
            final_state["ai_response"],
            final_state["emotion"]
        )
        
        try:
            audio_response = voice_assistant.text_to_speech(final_state["ai_response"], final_state["emotion"])
            
            logger.info("Pipeline completed successfully - returning WAV audio")
            
            return StreamingResponse(
                io.BytesIO(audio_response),
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "attachment; filename=response.wav",
                    "X-User": user_name,
                    "X-Transcription": final_state["transcribed_text"],
                    "X-Emotion": final_state["emotion"],
                    "X-Response": final_state["ai_response"],
                    "X-Session-ID": str(session_id),
                    "X-Summary": final_state["summary"]
                }
            )
            
        except Exception as tts_error:
            logger.error(f"TTS failed, returning text response: {tts_error}")
            return {
                "user": user_name,
                "transcription": final_state["transcribed_text"],
                "emotion": final_state["emotion"],
                "response": final_state["ai_response"],
                "session_id": session_id,
                "summary": final_state["summary"],
                "tts_error": str(tts_error)
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    finally:
        if temp_audio_path and os.path.exists(temp_audio_path):
            try:
                os.unlink(temp_audio_path)
            except Exception as cleanup_e:
                logger.error(f"Error cleaning up temp file: {cleanup_e}")

@app.post("/receive-subject")
async def receive_subject(subject: Dict):
    """Receive subject name from face recognition and update user name"""
    try:
        subject_name = subject.get("subject")
        if not subject_name or not isinstance(subject_name, str):
            raise HTTPException(status_code=400, detail="Invalid or missing 'subject' field")
        
        voice_assistant.set_user_name(subject_name)
        return {"message": f"User name updated to {subject_name}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Receive subject error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process subject: {str(e)}")

@app.post("/upload-profile")
async def upload_profile(file: UploadFile = File(...)):
    """Handle JSON profile upload"""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="File must be in JSON format")
    
    try:
        content = await file.read()
        profile_data = json.loads(content.decode('utf-8'))
        
        required_fields = ["name", "face_photo", "info"]
        if not all(field in profile_data for field in required_fields):
            raise HTTPException(status_code=400, detail="JSON must contain 'name', 'face_photo', and 'info' fields")
        
        user_name = profile_data["name"]
        face_photo = profile_data["face_photo"]
        info = profile_data["info"]
        
        if not isinstance(user_name, str) or not user_name.strip():
            raise HTTPException(status_code=400, detail="Invalid or empty 'name' field")
        if not isinstance(face_photo, str) or not face_photo.startswith("data:image/"):
            raise HTTPException(status_code=400, detail="'face_photo' must be a base64-encoded image")
        if not isinstance(info, dict):
            raise HTTPException(status_code=400, detail="'info' must be a dictionary")
        
        voice_assistant.db.save_user_profile(user_name, face_photo, info)
        
        return {"message": f"Profile for {user_name} uploaded successfully"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile upload error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process profile: {str(e)}")

@app.post("/summarize-session/{session_id}")
async def summarize_session(session_id: int):
    try:
        conversations = voice_assistant.db.get_session_conversations(session_id)
        if not conversations:
            raise HTTPException(status_code=404, detail="No conversations found for this session")
        
        summary = voice_assistant.summarize_conversations(conversations)
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

@app.get("/get-summary/{user_name}")
async def get_summary(user_name: str):
    try:
        session_id = voice_assistant.db.get_or_create_session(user_name)
        conversations = voice_assistant.db.get_session_conversations(session_id)
        if not conversations:
            return {"user_name": user_name, "summary": "No previous conversations found"}
        summary = voice_assistant.summarize_conversations(conversations)
        return {"user_name": user_name, "summary": summary}
    except Exception as e:
        logger.error(f"Get Summary Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve summary: {str(e)}")

@app.get("/test-tts")
async def test_tts(text: str = Query(...), emotion: str = Query("neutral")):
    try:
        logger.info(f"Testing TTS with text: '{text}', emotion: '{emotion}'")
        audio_response = voice_assistant.text_to_speech(text, emotion)
        logger.info(f"TTS test successful, returning {len(audio_response)} bytes")
        return StreamingResponse(
            io.BytesIO(audio_response),
            media_type="audio/wav",
            headers={"Content-Disposition": "attachment; filename=test_tts.wav"}
        )
    except Exception as e:
        logger.error(f"TTS test error: {e}")
        return {"error": str(e), "text": text, "emotion": emotion}

@app.get("/debug-groq-tts")
async def debug_groq_tts():
    try:
        if not voice_assistant.groq_client:
            return {"error": "Groq client not initialized", "groq_api_key_present": bool(voice_assistant.groq_api_key)}
        
        test_text = "Hello, this is a test of the text to speech system."
        
        logger.info(f"Debug TTS - Testing with: '{test_text}'")
        logger.info(f"Debug TTS - Model: {voice_assistant.tts_model}")
        logger.info(f"Debug TTS - Voice: {voice_assistant.tts_voice_name}")
        
        headers = {
            "Authorization": f"Bearer {voice_assistant.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": voice_assistant.tts_model,
            "voice": voice_assistant.tts_voice_name,
            "input": test_text,
            "response_format": "wav"
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                "https://api.groq.com/openai/v1/audio/speech",
                headers=headers,
                json=payload
            )
        if response.status_code != 200:
            return {"error": f"TTS HTTP Error: {response.status_code} - {response.text}"}
        
        return {
            "status": "success",
            "test_text": test_text,
            "model": voice_assistant.tts_model,
            "voice": voice_assistant.tts_voice_name
        }
        
    except Exception as e:
        logger.error(f"Debug TTS error: {e}")
        import traceback
        return {
            "error": str(e),
            "error_type": str(type(e)),
            "traceback": traceback.format_exc(),
            "groq_client_available": voice_assistant.groq_client is not None
        }

@app.get("/debug-memory/{thread_id}")
async def debug_memory(thread_id: str):
    try:
        checkpoint = memory.get({"configurable": {"thread_id": thread_id}})
        if not checkpoint:
            return {"error": "No checkpoint found for thread_id", "thread_id": thread_id}
        return {
            "thread_id": thread_id,
            "state": checkpoint["channel_values"],
            "summary": checkpoint["channel_values"].get("summary", "No summary found")
        }
    except Exception as e:
        logger.error(f"Debug Memory error: {e}")
        return {"error": str(e), "thread_id": thread_id}

@app.get("/debug-tavily/{query}")
async def debug_tavily(query: str):
    try:
        if not voice_assistant.tavily_tool:
            return {"error": "Tavily tool not initialized", "tavily_api_key_present": bool(tavily_api_key)}
        results = voice_assistant.tavily_tool.invoke({"query": query})
        return {
            "query": query,
            "results": results,
            "result_count": len(results) if isinstance(results, list) else 0
        }
    except Exception as e:
        logger.error(f"Debug Tavily error: {e}")
        return {"error": str(e), "query": query}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)