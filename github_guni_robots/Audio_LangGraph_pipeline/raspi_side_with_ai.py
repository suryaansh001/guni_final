import math
import time
import sys
import threading
import requests
import json
import os
import tempfile
import pyaudio
import wave
from OpenGL.GL import *
from OpenGL.GLU import *
import numpy as np
from queue import Queue
import logging
import random
import cv2
import base64
import whisper
import pygame
import sqlite3
from datetime import datetime
from elevenlabs.client import ElevenLabs
from groq import Groq
import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# GUNI Information for context
GUNI_INFO = """
Ganpat University (GUNI) is a prestigious educational institution located in Gujarat, India. 
Key information about GUNI:
- Founded in 2005
- Located in Mehsana, Gujarat
- Known for engineering, management, pharmacy, and other professional courses
- Modern campus with state-of-the-art facilities
- Strong industry connections and placement support
- Focus on innovation, research, and practical learning
- Various clubs and cultural activities for students
- Hostel facilities available for students
"""
class LocalDatabase:
    """Local SQLite database for storing conversations and user data"""
    
    def __init__(self, db_path="voice_assistant.db"):
        self.db_path = db_path
        self.init_database()
        self.check_database_integrity()
    
    def init_database(self):
        """Initialize the database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Users table (simplified, removed sync fields)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_role TEXT CHECK(user_role IN ('student', 'faculty', 'other')) DEFAULT 'other',
                    user_id TEXT UNIQUE,
                    department TEXT,
                    name TEXT NOT NULL UNIQUE,
                    mobile_number TEXT,
                    personal_email TEXT,
                    institute_email TEXT,
                    gender TEXT,
                    occupation TEXT,
                    parent_mobile_number TEXT,
                    parent_email TEXT,
                    address TEXT,
                    city TEXT,
                    state TEXT,
                    country TEXT,
                    preferred_language TEXT DEFAULT 'english',
                    face_photo TEXT,
                    is_synced_by_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Single conversations table (merged chat_sessions and conversations)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    session_date DATE NOT NULL,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    summary TEXT,
                    language_used TEXT DEFAULT 'english',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_name) REFERENCES users (name)
                )
            ''')
            
            # User profiles table (simplified)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_name TEXT PRIMARY KEY,
                    face_photo TEXT,
                    info TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_name) REFERENCES users (name)
                )
            ''')
            
            # Conversation context table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_name TEXT NOT NULL,
                    context_type TEXT NOT NULL,
                    context_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_name) REFERENCES users (name)
                )
            ''')
            
            # Unknown users tracking table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS unknown_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unknown_user_name TEXT NOT NULL UNIQUE,
                    face_photo TEXT NOT NULL,
                    detection_confidence REAL,
                    detection_count INTEGER DEFAULT 1,
                    first_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_synced_by_admin BOOLEAN DEFAULT FALSE,
                    resolved_user_name TEXT,
                    resolved_at TIMESTAMP,
                    FOREIGN KEY (resolved_user_name) REFERENCES users (name)
                )
            ''')
            
            # Admin sync log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT CHECK(action_type IN ('sync_unknown_user', 'resolve_unknown_user')) NOT NULL,
                    unknown_user_name TEXT,
                    target_user_name TEXT,
                    admin_user TEXT,
                    sync_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            conn.commit()
    
    def get_user_details(self, user_name):
        """Get user details from database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT * FROM users WHERE name = ?', (user_name,))
                result = cursor.fetchone()
                if result:
                    return dict(result)
                return {}
            except sqlite3.OperationalError as e:
                logger.error(f"Database error: {e}")
                # If table doesn't exist or column is missing, ensure user exists and return empty dict
                self.ensure_user_exists(user_name)
                return {}

    def ensure_user_exists(self, user_name):
        """Ensure user exists in database, create if not exists"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT name FROM users WHERE name = ?', (user_name,))
                if not cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO users (name, user_id) VALUES (?, ?)
                    ''', (user_name, user_name))
                    conn.commit()
                    logger.info(f"Created new user: {user_name}")
            except sqlite3.OperationalError as e:
                logger.error(f"Database error when ensuring user exists: {e}")
                # Re-initialize database if there's a schema issue
                logger.info("Reinitializing database schema...")
                self.init_database()
                # Try again after reinitializing
                try:
                    cursor.execute('SELECT name FROM users WHERE name = ?', (user_name,))
                    if not cursor.fetchone():
                        cursor.execute('''
                            INSERT INTO users (name, user_id) VALUES (?, ?)
                        ''', (user_name, user_name))
                        conn.commit()
                        logger.info(f"Created new user after schema fix: {user_name}")
                except Exception as retry_error:
                    logger.error(f"Failed to create user even after schema fix: {retry_error}")

    
    def update_user_details(self, user_name, user_details):
        """Update user details in database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build dynamic update query
            update_fields = []
            update_values = []
            
            for field, value in user_details.items():
                if field in ['user_role', 'user_id', 'department', 'name', 'mobile_number', 
                           'personal_email', 'institute_email', 'gender', 'occupation',
                           'parent_mobile_number', 'parent_email', 'address', 'city',
                           'state', 'country', 'preferred_language', 'face_photo', 'is_synced_by_admin']:
                    update_fields.append(f"{field} = ?")
                    update_values.append(value)
            
            if update_fields:
                update_values.append(user_name)
                query = f'''
                    UPDATE users 
                    SET {", ".join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE name = ?
                '''
                cursor.execute(query, update_values)
                conn.commit()
                logger.info(f"Updated user details for: {user_name}")
    
    def add_conversation(self, user_name, user_input, ai_response, language_used='english', summary=None):
        """Add a new conversation to the database"""
        today = datetime.now().date().isoformat()
        
        # Ensure user exists
        self.ensure_user_exists(user_name)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversations (user_name, session_date, user_input, ai_response, summary, language_used)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_name, today, user_input, ai_response, summary, language_used))
            conn.commit()
            logger.info(f"Saved conversation for user: {user_name}")
    
    def get_recent_conversations(self, user_name, limit=5):
        """Get recent conversations for a user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_input, ai_response, language_used, timestamp
                FROM conversations 
                WHERE user_name = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (user_name, limit))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    'user': row['user_input'],
                    'assistant': row['ai_response'],
                    'language_used': row['language_used'],
                    'timestamp': row['timestamp']
                })
            
            return conversations[::-1]  # Return in chronological order
    
    def create_unknown_user(self, face_photo, confidence=None):
        """Create an unknown user entry when face detection detects unknown face"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Generate unique unknown user name with current date
            today = datetime.now().strftime("%Y-%m-%d")
            
            # Find next available unknown user number for today
            cursor.execute('''
                SELECT unknown_user_name FROM unknown_users 
                WHERE unknown_user_name LIKE ? 
                ORDER BY unknown_user_name DESC
            ''', (f"unknown_%_{today}",))
            
            existing_unknowns = cursor.fetchall()
            next_number = len(existing_unknowns) + 1
            
            unknown_user_name = f"unknown_{next_number}_{today}"
            
            # Check if this detection already exists (update count if it does)
            cursor.execute('''
                SELECT id, detection_count FROM unknown_users 
                WHERE unknown_user_name = ?
            ''', (unknown_user_name,))
            existing = cursor.fetchone()
            
            if existing:
                # Update detection count and last detected time
                cursor.execute('''
                    UPDATE unknown_users 
                    SET detection_count = detection_count + 1,
                        last_detected_at = CURRENT_TIMESTAMP
                    WHERE unknown_user_name = ?
                ''', (unknown_user_name,))
            else:
                # Create new unknown user entry
                cursor.execute('''
                    INSERT INTO unknown_users (unknown_user_name, face_photo, detection_confidence)
                    VALUES (?, ?, ?)
                ''', (unknown_user_name, face_photo, confidence))
                
                # Create corresponding user entry
                cursor.execute('''
                    INSERT INTO users (name, user_id, face_photo)
                    VALUES (?, ?, ?)
                ''', (unknown_user_name, unknown_user_name, face_photo))
            
            conn.commit()
            return unknown_user_name
    
    def create_or_update_user_profile(self, user_name, face_photo=None, info=None):
        """Create or update user profile"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Ensure user exists
            self.ensure_user_exists(user_name)
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles (user_name, face_photo, info, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_name, face_photo, info))
            conn.commit()
    
    def get_user_profile(self, user_name):
        """Get user profile"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_profiles WHERE user_name = ?', (user_name,))
            result = cursor.fetchone()
            if result:
                return dict(result)
            return {}
    
    def add_conversation_context(self, user_name, context_type, context_data):
        """Add conversation context"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Ensure user exists
            self.ensure_user_exists(user_name)
            
            cursor.execute('''
                INSERT INTO conversation_context (user_name, context_type, context_data)
                VALUES (?, ?, ?)
            ''', (user_name, context_type, context_data))
            conn.commit()
    def check_database_integrity(self):
        """Check if database has all required columns and fix if needed"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if users table has all required columns
                cursor.execute("PRAGMA table_info(users)")
                columns = [row[1] for row in cursor.fetchall()]
                
                required_columns = [
                    'id', 'user_role', 'user_id', 'department', 'name', 'mobile_number',
                    'personal_email', 'institute_email', 'gender', 'occupation',
                    'parent_mobile_number', 'parent_email', 'address', 'city',
                    'state', 'country', 'preferred_language', 'face_photo',
                    'is_synced_by_admin', 'created_at', 'updated_at'
                ]
                
                missing_columns = set(required_columns) - set(columns)
                if missing_columns:
                    logger.warning(f"Missing columns in users table: {missing_columns}")
                    logger.info("Recreating database with correct schema...")
                    
                    # Backup existing data if table exists
                    try:
                        cursor.execute("SELECT name FROM users")
                        existing_users = [row[0] for row in cursor.fetchall()]
                    except:
                        existing_users = []
                    
                    # Drop and recreate tables
                    cursor.execute("DROP TABLE IF EXISTS users")
                    cursor.execute("DROP TABLE IF EXISTS conversations")
                    cursor.execute("DROP TABLE IF EXISTS user_profiles")
                    cursor.execute("DROP TABLE IF EXISTS conversation_context")
                    cursor.execute("DROP TABLE IF EXISTS unknown_users")
                    cursor.execute("DROP TABLE IF EXISTS admin_sync_log")
                    
                    # Reinitialize database
                    self.init_database()
                    
                    # Restore users if they existed
                    for user in existing_users:
                        try:
                            cursor.execute("INSERT INTO users (name, user_id) VALUES (?, ?)", (user, user))
                        except:
                            pass
                    
                    conn.commit()
                    logger.info("Database schema fixed and data restored")
                
                return True
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False
    def get_conversation_context(self, user_name, context_type=None):
        """Get conversation context for user"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if context_type:
                cursor.execute('''
                    SELECT * FROM conversation_context 
                    WHERE user_name = ? AND context_type = ?
                    ORDER BY created_at DESC
                ''', (user_name, context_type))
            else:
                cursor.execute('''
                    SELECT * FROM conversation_context 
                    WHERE user_name = ?
                    ORDER BY created_at DESC
                ''', (user_name,))
            
            return [dict(row) for row in cursor.fetchall()]

class VoiceAssistantClient:
    """Voice Assistant Client with OpenGL Expression Display, CompreFace Integration, and Local Processing"""
    
    def __init__(self, width=900, height=700, api_url="http://localhost:8001", 
                 user_name="test_user", compreface_url="http://localhost:8000", 
                 compreface_api_key="e4648f5d-3ee5-4005-88e4-4bd9dfbef942"):
        # Initialize pygame and OpenGL
        pygame.init()
        self.width = width
        self.height = height
        self.user_greeted = False
        
        # Create OpenGL window
        self.screen = pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("Robot Voice Assistant - Interactive Test with Face Recognition & Whisper")
        
        # Initialize OpenGL settings
        self.init_opengl()
        
        # Initialize font for text rendering
        pygame.font.init()
        self.font = pygame.font.SysFont("Arial", 16)
        self.big_font = pygame.font.SysFont("Arial", 20, bold=True)
        
        # Time tracking
        self.clock = pygame.time.Clock()
        self.start_time = time.time()
        
        # Voice Assistant Configuration
        self.api_url = api_url
        self.user_name = user_name
        self.default_user_name = user_name
        
        # Initialize database
        self.db = LocalDatabase()
        
        # CompreFace Configuration
        self.compreface_url = compreface_url
        self.compreface_api_key = "e4648f5d-3ee5-4005-88e4-4bd9dfbef942"
        self.face_recognition_enabled = True
        
        # API Keys
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        
        # Initialize Groq client
        if self.groq_api_key:
            try:
                self.groq_client = Groq(
                    api_key=self.groq_api_key,
                    http_client=httpx.Client(timeout=30.0)
                )
                logger.info("Groq client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {e}")
                self.groq_client = None
        else:
            self.groq_client = None
            logger.warning("GROQ_API_KEY not found. LLM functionality will be limited.")
        
        # Initialize ElevenLabs client
        if self.elevenlabs_api_key:
            try:
                self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
                logger.info("ElevenLabs client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize ElevenLabs client: {e}")
                self.elevenlabs_client = None
        else:
            self.elevenlabs_client = None
            logger.warning("ELEVENLABS_API_KEY not found. TTS functionality will be limited.")
        
        # ElevenLabs TTS Configuration
        self.elevenlabs_voice_id = "zgqefOY5FPQ3bB7OZTVR"  # Default voice
        self.elevenlabs_model_id = "eleven_multilingual_v2"
        
        # LLM Configuration
        self.llm_model = "llama-3.3-70b-versatile"
        
        # Face recognition state
        self.face_recognition_status = "Not attempted"
        self.recognized_user = None
        self.face_confidence = 0.0
        try:
            import pyttsx3
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)  # Speed of speech
            self.tts_engine.setProperty('volume', 0.9)  # Volume (0-1)
            self.use_local_tts = True
            logger.info("Local TTS engine initialized")
        except ImportError:
            self.tts_engine = None
            self.use_local_tts = False
            logger.warning("pyttsx3 not installed. Install with: pip install pyttsx3")
        except Exception as e:
            self.tts_engine = None
            self.use_local_tts = False
            logger.error(f"Failed to initialize local TTS engine: {e}")
        
        # Audio Configuration
        self.audio_config = {
            'chunk': 1024,
            'format': pyaudio.paInt16,
            'channels': 1,
            'rate': 16000,
            'record_seconds': 5
        }
        
        # Expression mapping
        self.expression_map = {
            "happy": "happy",
            "excited": "happy",
            "sad": "sad", 
            "very_sad": "sad",
            "angry": "angry",
            "furious": "angry",
            "surprised": "surprised",
            "shocked": "surprised",
            "confused": "confused",
            "bewildered": "confused",
            "sleepy": "sleepy",
            "asleep": "sleepy",
            "loving": "love",
            "lovestruck": "love",
            "playful": "wink",
            "flirty": "wink",
            "nervous": "nervous",
            "panicked": "nervous"
        }
        
        # Available robot expressions for LLM selection
        self.available_expressions = {
            # Basic emotions that match the expression map
            "happy": "Classic happy expression - general happiness, contentment, joy",
            "sad": "Sad expression - sadness, disappointment, melancholy",
            "angry": "Angry expression - anger, frustration, irritation",
            "surprised": "Surprised expression - surprise, wonder, amazement, shock",
            "confused": "Confused expression - confusion, puzzlement, uncertainty",
            "sleepy": "Sleepy expression - tiredness, drowsiness, low energy",
            "love": "Love expression - affection, adoration, romantic feelings",
            "wink": "Playful wink expression - playfulness, teasing, flirtation",
            "nervous": "Nervous expression - anxiety, worry, nervousness",
            "neutral": "Neutral expression - default, calm, balanced"
        }
        
        # Current expression and colors
        self.current_expression = "happy"
        self.target_expression = "happy"
        self.expression_transition_time = 0.0
        self.expression_transition_duration = 0.5
        
        self.color_map = {
            "happy": (0.2, 0.8, 1.0),
            "sad": (0.3, 0.5, 1.0),
            "angry": (1.0, 0.3, 0.3),
            "surprised": (1.0, 0.7, 0.2),
            "confused": (0.9, 0.6, 0.9),
            "love": (1.0, 0.4, 0.7),
            "sleepy": (0.7, 0.5, 1.0),
            "wink": (0.2, 1.0, 0.6),
            "nervous": (1.0, 0.8, 0.3),
            "neutral": (0.8, 0.8, 0.8)
        }
        self.current_color = self.color_map["happy"]
        
        # Voice interaction state
        self.is_recording = False
        self.is_processing = False
        self.is_speaking = False
        self.is_face_recognizing = False
        self.conversation_active = False
        
        # Status tracking
        self.last_user_input = ""
        self.last_ai_response = ""
        self.last_expression_change = time.time()
        self.api_status = "Disconnected"
        
        # Threading
        self.expression_queue = Queue()
        self.audio_thread = None
        
        # Running state
        self.running = True
        
        # Animation parameters
        self.face_center_x = 0.0
        self.face_center_y = 0.2
        self.face_size = 1.6
        
        # Eye animation parameters
        self.blink_timer = 0.0
        self.next_blink = 3.0 + random.random() * 4.0
        self.is_blinking = False
        self.blink_duration = 0.2
        
        # Setup control buttons
        self.setup_buttons()
        
        # Test connections
        self.test_api_connection()
        self.test_compreface_connection()
    
    def setup_buttons(self):
        """Setup interactive buttons for voice control"""
        self.buttons = []
        
        # Main voice interaction button
        self.buttons.append({
            "id": "voice_interaction",
            "text": "🎤 Start Voice Chat",
            "x": -1.8,
            "y": -1.0,
            "width": 3.6,
            "height": 0.3,
            "color": (0.2, 0.7, 0.2),
            "hover_color": (0.3, 0.9, 0.3),
            "action": self.start_continuous_conversation,
            "enabled": True
        })
        
        # Stop button
        self.buttons.append({
            "id": "stop_interaction",
            "text": "⏹️ Stop",
            "x": -1.8,
            "y": -1.4,
            "width": 1.7,
            "height": 0.25,
            "color": (0.7, 0.2, 0.2),
            "hover_color": (0.9, 0.3, 0.3),
            "action": self.stop_interaction,
            "enabled": True
        })
        
        # Test connection button
        self.buttons.append({
            "id": "test_connection",
            "text": "🔗 Test Connection",
            "x": 0.1,
            "y": -1.4,
            "width": 1.7,
            "height": 0.25,
            "color": (0.2, 0.2, 0.7),
            "hover_color": (0.3, 0.3, 0.9),
            "action": self.test_api_connection,
            "enabled": True
        })
        
        # Face recognition test button
        self.buttons.append({
            "id": "test_face",
            "text": "👤 Test Face",
            "x": -1.8,
            "y": -1.7,
            "width": 1.7,
            "height": 0.25,
            "color": (0.7, 0.5, 0.2),
            "hover_color": (0.9, 0.7, 0.3),
            "action": self.test_face_recognition,
            "enabled": True
        })
        
        # Calculate pixel coordinates for mouse detection
        for button in self.buttons:
            pixel_x = int((button["x"] + 2.5) / 5.0 * self.width)
            pixel_y = int((2.0 - button["y"] - button["height"]) / 4.0 * self.height)
            pixel_width = int(button["width"] / 5.0 * self.width)
            pixel_height = int(button["height"] / 4.0 * self.height)
            
            button["pixel_x"] = pixel_x
            button["pixel_y"] = pixel_y
            button["pixel_width"] = pixel_width
            button["pixel_height"] = pixel_height

    def init_opengl(self):
        """Initialize OpenGL settings"""
        glViewport(0, 0, self.width, self.height)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-2.5, 2.5, -2.0, 2.0, -1.0, 1.0)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glClearColor(0.08, 0.08, 0.12, 1.0)
        glLineWidth(2.0)
    
    def test_api_connection(self):
        """Test connection to the STT server API"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                self.api_status = "Connected"
                logger.info("API connection successful")
            else:
                self.api_status = f"Error {response.status_code}"
                logger.warning(f"API responded with status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.api_status = "Connection Error"
            logger.error(f"Cannot connect to API at {self.api_url}: {e}")
    
    def send_audio_to_server(self, audio_path):
        """Send audio to server for STT using customized Whisper"""
        try:
            logger.info(f"Sending audio to server for transcription: {audio_path}")
            
            with open(audio_path, 'rb') as audio_file:
                files = {'audio': audio_file}
                data = {'user_name': self.user_name}
                
                response = requests.post(
                    f"{self.api_url}/transcribe_audio",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"STT Response: {result}")
                
                if result.get('success', False):
                    logger.info(f"Transcription successful: '{result['text']}'")
                    logger.info(f"Detected language: {result['language_name']} (confidence: {result['language_confidence']:.2f})")
                    return result
                else:
                    logger.error(f"STT failed: {result.get('error', 'Unknown error')}")
                    return {"success": False, "text": "", "error": result.get('error', 'Unknown error')}
            else:
                logger.error(f"STT request failed with status {response.status_code}: {response.text}")
                return {"success": False, "text": "", "error": f"Server error: {response.status_code}"}
        
        except Exception as e:
            logger.error(f"Error sending audio to server: {e}")
            return {"success": False, "text": "", "error": str(e)}
    
    def analyze_emotion(self, text: str) -> dict:
        """Analyze emotion using server-side emotion analyzer"""
        try:
            logger.info(f"Analyzing emotion for text: '{text}'")
            
            response = requests.post(
                f"{self.api_url}/analyze_emotion",
                json={"text": text},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success', False):
                    logger.info(f"Emotion analysis successful: {result['emotion']} (confidence: {result['confidence']:.2f})")
                    return result
                else:
                    logger.error(f"Emotion analysis failed: {result.get('error', 'Unknown error')}")
                    return {"emotion": "neutral", "confidence": 1.0}
            else:
                logger.error(f"Emotion analysis request failed: {response.status_code}")
                return {"emotion": "neutral", "confidence": 1.0}
        
        except Exception as e:
            logger.error(f"Error analyzing emotion: {e}")
            return {"emotion": "neutral", "confidence": 1.0}
    def analyze_emotion(self, text: str) -> dict:
        """Analyze emotion from text - using server API"""
        try:
            response = requests.post(
                f"{self.api_url}/analyze_emotion",
                json={"text": text},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                emotion = result.get("emotion", "neutral")
                confidence = result.get("confidence", 1.0)
                logger.info(f"User Emotion Analysis: {emotion} (confidence: {confidence:.2f})")
                return {"emotion": emotion, "confidence": confidence}
            else:
                logger.error(f"Emotion analysis server error: {response.status_code}")
                return {"emotion": "neutral", "confidence": 1.0}
        except Exception as e:
            logger.error(f"Emotion analysis error: {e}")
            return {"emotion": "neutral", "confidence": 1.0}
    
    def generate_llm_response(self, user_input, user_emotion, user_name, recent_conversations=None):
        """Generate LLM response directly using Groq client"""
        if not self.groq_client:
            return {
                "robot_emotion": "neutral",
                "robot_expression": "happy",
                "text_response": "I'm sorry, I'm having trouble connecting to the LLM service right now.",
                "language_used": "english"
            }
        
        # Initialize default values at the beginning
        preferred_language = "english"
        
        try:
            # Get user details from local DB
            user_details = self.db.get_user_details(user_name)
            if user_details:
                preferred_language = user_details.get('preferred_language', 'english')
            else:
                # Create default user if not exists
                self.db.ensure_user_exists(user_name)
                preferred_language = 'english'
            
            # Prepare conversation history for context
            conversation_history = ""
            if recent_conversations:
                for msg in recent_conversations:
                    conversation_history += f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}\n"
            
            # Create comprehensive system prompt
            expressions_list = "\n".join([f"  - {emotion}: {description}" for emotion, description in self.available_expressions.items()])
            
            system_prompt = f"""You are GUNI Assistant, an intelligent AI assistant for Ganpat University (GUNI) students and faculty. You have complete autonomy to make decisions about language, emotions, expressions, and responses.

    CRITICAL INSTRUCTIONS:
    1. You MUST provide THREE outputs in your response:
    - LANGUAGE: Detect the user's language and respond in the same language (english/hindi/gujarati/other)
    - ROBOT_EXPRESSION: Choose the most appropriate expression from the available options
    - TEXT_RESPONSE: Your conversational response (maximum 80 words)

    2. LANGUAGE DETECTION AND RESPONSE:
    - Automatically detect the user's language from their input
    - Respond in the same language the user used
    - For Hindi: Use romanized Hindi (Hindi words written in English script)
    - For Gujarati: Use romanized Gujarati (Gujarati words written in English script)
    - For English: Use proper English
    - Handle code-switching naturally if user mixes languages

    3. ROBOT EXPRESSION SELECTION:
    You have complete freedom to choose the most appropriate expression based on:
    - Context of the conversation
    - User's emotional state: {user_emotion}
    - Your response content and tone
    - Situational appropriateness
    
    Available expressions (use EXACT emotion names):
    {expressions_list}

    4. CONTENT GUIDELINES:
    - Be helpful, empathetic, and engaging
    - Adapt your personality to match the conversation flow
    - Handle jokes, casual conversations, academic queries equally well
    - You can be playful, serious, supportive, or excited as appropriate
    - Make decisions about formality level based on context

    5. SAFETY AND SCOPE:
    - Prioritize GUNI-related information when relevant
    - Avoid harmful, illegal, or unethical content
    - If asked about other universities, politely redirect to GUNI topics
    - Handle sensitive topics with appropriate care

    CONTEXT INFORMATION:
    - User's name: {user_name}
    - User's detected emotion: {user_emotion}
    - User's previous language preference: {preferred_language}
    - Recent conversation: {conversation_history}

    GUNI INFORMATION:
    {GUNI_INFO}

    RESPONSE FORMAT (MANDATORY - use exact emotion names):
    LANGUAGE: [detected_language]
    ROBOT_EXPRESSION: [emotion_name]
    TEXT_RESPONSE: [your response in detected language]

    IMPORTANT: For ROBOT_EXPRESSION, use only these exact words: happy, sad, angry, surprised, confused, sleepy, love, wink, nervous, neutral"""

            # Create the prompt with user input
            user_prompt = f"User says: {user_input}"
            
            # Generate response using Groq
            response = self.groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model=self.llm_model,
                temperature=0.8,
                max_tokens=500
            )
            
            llm_response = response.choices[0].message.content.strip()
            logger.info(f"LLM Response: {llm_response}")
            
            # Parse the response
            detected_language = "english"
            robot_expression = "happy"  # Default fallback
            text_response = "I'm here to help you!"  # Default fallback
            
            try:
                lines = llm_response.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('LANGUAGE:'):
                        detected_language = line.replace('LANGUAGE:', '').strip().lower()
                    elif line.startswith('ROBOT_EXPRESSION:'):
                        expression_part = line.replace('ROBOT_EXPRESSION:', '').strip().lower()
                        # Validate expression against available emotions
                        if expression_part in self.available_expressions:
                            robot_expression = expression_part
                        else:
                            logger.warning(f"Invalid expression from LLM: {expression_part}, using default 'happy'")
                    elif line.startswith('TEXT_RESPONSE:'):
                        text_response = line.replace('TEXT_RESPONSE:', '').strip()
                
                # If parsing failed, try alternative parsing
                if text_response == "I'm here to help you!":
                    # Extract text that doesn't contain format markers
                    text_lines = []
                    for line in lines:
                        if not any(marker in line for marker in ['LANGUAGE:', 'ROBOT_EXPRESSION:', 'TEXT_RESPONSE:']):
                            text_lines.append(line.strip())
                    
                    if text_lines:
                        text_response = ' '.join(text_lines)
            
            except Exception as e:
                logger.error(f"Error parsing LLM response: {e}")
                # Use intelligent fallback based on user emotion
                robot_expression = self._map_user_emotion_to_robot(user_emotion)
                text_response = llm_response  # Use the full response as fallback
            
            # Update user's language preference if it changed
            if detected_language != preferred_language:
                try:
                    self.db.update_user_details(user_name, {"preferred_language": detected_language})
                    logger.info(f"Updated language preference for {user_name}: {detected_language}")
                except Exception as update_error:
                    logger.error(f"Failed to update language preference: {update_error}")
            
            # Return the processed response
            return {
                "robot_emotion": robot_expression,
                "robot_expression": robot_expression,
                "text_response": text_response,
                "language_used": detected_language
            }
            
        except Exception as e:
            logger.error(f"LLM generation error: {e}")
            import traceback
            logger.error(f"LLM error traceback: {traceback.format_exc()}")
            
            # Intelligent fallback response
            fallback_expression = self._map_user_emotion_to_robot(user_emotion)
            
            # Intelligent language-based fallback responses
            if preferred_language == 'hindi':
                fallback_text = f"Namaste {user_name}! Main aapki madad karne ke liye yahan hun. Kripaya phir se koshish kariye."
            elif preferred_language == 'gujarati':
                fallback_text = f"Namaste {user_name}! Hu tamari madad karva mate yahan chu. Kripaya fari koshish karo."
            else:
                fallback_text = f"Hello {user_name}! I'm here to help you. Please feel free to ask me anything about GUNI or how I can assist you."
            
            return {
                "robot_emotion": fallback_expression,
                "robot_expression": fallback_expression,
                "text_response": fallback_text,
                "language_used": preferred_language
            }

    
    def _map_user_emotion_to_robot(self, user_emotion):
        """Map user emotion to appropriate robot expression"""
        emotion_mapping = {
            "joy": "happy",
            "happiness": "happy",
            "sadness": "sad",
            "anger": "angry",
            "surprise": "surprised",
            "fear": "nervous",
            "disgust": "confused",
            "neutral": "neutral",
            "love": "love",
            "excitement": "happy",
            "anxiety": "nervous",
            "worry": "nervous",
            "confusion": "confused"
        }
        
        user_emotion_lower = user_emotion.lower()
        
        # Direct mapping if exists
        if user_emotion_lower in emotion_mapping:
            return emotion_mapping[user_emotion_lower]
        
        # Check if user emotion contains keywords
        for key, value in emotion_mapping.items():
            if key in user_emotion_lower:
                return value
        
        # Default to happy for unknown emotions
        return "happy"
    
    def text_to_speech_elevenlabs(self, text, robot_emotion):
        """Convert text to speech using ElevenLabs API"""
        if not self.elevenlabs_client:
            logger.warning("ElevenLabs client not initialized, using fallback TTS")
            return self.speak_text(text)
        
        try:
            logger.info(f"ElevenLabs TTS Request - Text: '{text}', Voice: {self.elevenlabs_voice_id}")
            
            # Generate audio stream using ElevenLabs
            audio_stream = self.elevenlabs_client.text_to_speech.stream(
                text=text,
                voice_id=self.elevenlabs_voice_id,
                model_id=self.elevenlabs_model_id
            )
            
            # Process the audio bytes manually
            audio_chunks = []
            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    audio_chunks.append(chunk)
            
            # Combine all chunks into single audio content
            audio_content = b''.join(audio_chunks)
            
            if not audio_content:
                logger.error("ElevenLabs generated empty audio")
                return self.speak_text(text)
            
            # Save to temporary file for playback
            temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_audio.write(audio_content)
            temp_audio.close()
            
            logger.info(f"ElevenLabs audio saved to: {temp_audio.name}")
            
            # Play the audio using pygame
            try:
                # Initialize pygame mixer if not already done
                if not pygame.mixer.get_init():
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                
                pygame.mixer.music.load(temp_audio.name)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                    if not self.is_speaking:
                        pygame.mixer.music.stop()
                        break
                
                logger.info("ElevenLabs audio playback completed")
                
                # Clean up
                try:
                    os.unlink(temp_audio.name)
                except:
                    pass
                
                return True
                
            except Exception as e:
                logger.error(f"Audio playback error: {e}")
                os.unlink(temp_audio.name)
                return self.speak_text(text)
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS error: {e}")
            return self.speak_text(text)

    def stop_interaction(self):
        """Stop any ongoing interaction"""
        self.conversation_active = False
        self.is_recording = False
        self.is_processing = False
        self.is_speaking = False
        self.is_face_recognizing = False
        self.user_greeted = False
        logger.info("Interaction stopped by user")
    
    def set_expression(self, expression_name):
        """Set robot expression with smooth transition"""
        if expression_name in self.expression_map:
            visual_expression = self.expression_map[expression_name]
        else:
            visual_expression = expression_name
        
        if visual_expression not in self.color_map:
            visual_expression = "neutral"
        
        if visual_expression != self.target_expression:
            logger.info(f"Expression change: {self.target_expression} -> {visual_expression}")
            self.target_expression = visual_expression
            self.expression_transition_time = time.time()
            self.last_expression_change = time.time()
    
    def update_expression_transition(self):
        """Handle smooth expression transitions"""
        if self.current_expression != self.target_expression:
            elapsed = time.time() - self.expression_transition_time
            progress = min(elapsed / self.expression_transition_duration, 1.0)
            
            if progress >= 1.0:
                self.current_expression = self.target_expression
                self.current_color = self.color_map[self.current_expression]
            else:
                current_color = self.color_map[self.current_expression]
                target_color = self.color_map[self.target_expression]
                
                self.current_color = (
                    current_color[0] + (target_color[0] - current_color[0]) * progress,
                    current_color[1] + (target_color[1] - current_color[1]) * progress,
                    current_color[2] + (target_color[2] - current_color[2]) * progress
                )
    
    def update_blink(self, t):
        """Handle natural blinking animation"""
        if not self.is_blinking:
            if t > self.next_blink:
                self.is_blinking = True
                self.blink_timer = t
        else:
            if t - self.blink_timer > self.blink_duration:
                self.is_blinking = False
                self.next_blink = t + 2.0 + random.random() * 6.0
    
    def record_audio(self):
        """Record audio from microphone"""
        try:
            audio = pyaudio.PyAudio()
            
            temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_audio_path = temp_audio_file.name
            temp_audio_file.close()
            
            stream = audio.open(
                format=self.audio_config['format'],
                channels=self.audio_config['channels'],
                rate=self.audio_config['rate'],
                input=True,
                frames_per_buffer=self.audio_config['chunk']
            )
            
            logger.info("Recording started...")
            frames = []
            
            for _ in range(0, int(self.audio_config['rate'] / self.audio_config['chunk'] * self.audio_config['record_seconds'])):
                if not self.is_recording:
                    break
                data = stream.read(self.audio_config['chunk'], exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            logger.info("Recording finished.")
            
            wf = wave.open(temp_audio_path, 'wb')
            wf.setnchannels(self.audio_config['channels'])
            wf.setsampwidth(audio.get_sample_size(self.audio_config['format']))
            wf.setframerate(self.audio_config['rate'])
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return temp_audio_path
        except Exception as e:
            logger.error(f"Audio recording error: {e}")
            return None
    
    def voice_interaction_worker(self):
        """Worker function for voice interaction"""
        try:
            self.is_recording = True
            self.is_processing = False
            self.is_speaking = False
            
            # Step 1: Record audio
            audio_path = self.record_audio()
            self.is_recording = False
            
            if not audio_path:
                logger.error("Failed to record audio")
                return
            
            # Step 2: Send audio to server for STT processing
            self.is_processing = True
            stt_response = self.send_audio_to_server(audio_path)
            
            # Clean up audio file
            try:
                os.unlink(audio_path)
            except:
                pass
            
            if not stt_response or not stt_response.get('success', False):
                logger.error("Failed to get STT response")
                self.is_processing = False
                return
            
            # Step 3: Process the transcribed text
            user_input = stt_response.get('text', '')
            self.last_user_input = user_input
            
            if not user_input.strip():
                logger.info("No speech detected")
                self.is_processing = False
                return
            
            # Step 4: Get emotion analysis - could be part of STT response or separate call
            user_emotion_response = self.analyze_emotion(user_input)
            user_emotion = user_emotion_response.get('emotion', 'neutral')
            
            # Step 5: Get recent conversations from local database
            recent_conversations = self.db.get_recent_conversations(self.user_name)
            
            # Step 6: Generate LLM response with robot expression
            response_data = self.generate_llm_response(
                user_input=user_input,
                user_emotion=user_emotion,
                user_name=self.user_name,
                recent_conversations=recent_conversations
            )
            
            self.is_processing = False
            
            # Step 7: Save conversation to local database
            self.db.add_conversation(
                user_name=self.user_name,
                user_input=user_input,
                ai_response=response_data["text_response"],
                language_used=response_data["language_used"]
            )
            
            # Step 8: Update robot expression
            robot_expression = response_data.get('robot_expression', 'happy')
            self.set_expression(robot_expression)
            
            # Step 9: Text to speech and playback
            self.is_speaking = True
            self.last_ai_response = response_data["text_response"]
            self.text_to_speech_elevenlabs(response_data["text_response"], robot_expression)
            self.is_speaking = False
            
            logger.info("Voice interaction completed successfully")
        except Exception as e:
            logger.error(f"Voice interaction error: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.is_recording = False
            self.is_processing = False
            self.is_speaking = False
    
    def handle_mouse_click(self, mouse_pos):
        """Handle mouse clicks on buttons"""
        mouse_x, mouse_y = mouse_pos
        
        for button in self.buttons:
            if (button["pixel_x"] <= mouse_x <= button["pixel_x"] + button["pixel_width"] and
                button["pixel_y"] <= mouse_y <= button["pixel_y"] + button["pixel_height"]):
                
                if button["enabled"] and button["action"]:
                    logger.info(f"Button clicked: {button['text']}")
                    button["action"]()
                break

    # Drawing methods
    def draw_circle(self, cx, cy, radius, filled=True, segments=32):
        """Draw a circle using OpenGL"""
        if filled:
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(cx, cy)
        else:
            glBegin(GL_LINE_LOOP)
        
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            glVertex2f(x, y)
        glEnd()
    
    def draw_ellipse(self, cx, cy, rx, ry, filled=True, segments=32):
        """Draw an ellipse using OpenGL"""
        if filled:
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(cx, cy)
        else:
            glBegin(GL_LINE_LOOP)
        
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = cx + rx * math.cos(angle)
            y = cy + ry * math.sin(angle)
            glVertex2f(x, y)
        glEnd()
    
    def draw_rectangle(self, x, y, width, height, filled=True):
        """Draw a rectangle using OpenGL"""
        if filled:
            glBegin(GL_QUADS)
        else:
            glBegin(GL_LINE_LOOP)
        
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()
    
    def draw_rounded_rectangle(self, x, y, width, height, radius, filled=True):
        """Draw a rounded rectangle using OpenGL"""
        if filled:
            # Main rectangle
            glBegin(GL_QUADS)
            glVertex2f(x + radius, y)
            glVertex2f(x + width - radius, y)
            glVertex2f(x + width - radius, y + height)
            glVertex2f(x + radius, y + height)
            glEnd()
            
            # Side rectangles
            glBegin(GL_QUADS)
            glVertex2f(x, y + radius)
            glVertex2f(x + radius, y + radius)
            glVertex2f(x + radius, y + height - radius)
            glVertex2f(x, y + height - radius)
            glEnd()
            
            glBegin(GL_QUADS)
            glVertex2f(x + width - radius, y + radius)
            glVertex2f(x + width, y + radius)
            glVertex2f(x + width, y + height - radius)
            glVertex2f(x + width - radius, y + height - radius)
            glEnd()
            
            # Corner circles
            self.draw_circle(x + radius, y + radius, radius, True, 16)
            self.draw_circle(x + width - radius, y + radius, radius, True, 16)
            self.draw_circle(x + width - radius, y + height - radius, radius, True, 16)
            self.draw_circle(x + radius, y + height - radius, radius, True, 16)
    
    def draw_line(self, x1, y1, x2, y2):
        """Draw a line using OpenGL"""
        glBegin(GL_LINES)
        glVertex2f(x1, y1)
        glVertex2f(x2, y2)
        glEnd()
    
    def draw_curve(self, points):
        """Draw a smooth curve through points"""
        glBegin(GL_LINE_STRIP)
        for point in points:
            glVertex2f(point[0], point[1])
        glEnd()
    
    def generate_quadratic_curve(self, x1, y1, cx, cy, x2, y2, segments=20):
        """Generate points for a quadratic Bezier curve"""
        points = []
        for i in range(segments + 1):
            t = i / segments
            x = (1-t)**2 * x1 + 2*(1-t)*t * cx + t**2 * x2
            y = (1-t)**2 * y1 + 2*(1-t)*t * cy + t**2 * y2
            points.append((x, y))
        return points
    
    def draw_eye(self, cx, cy, size, blink_factor=1.0, pupil_offset_x=0, pupil_offset_y=0):
        """Draw an interactive eye with pupil tracking and blinking"""
        if self.is_blinking or blink_factor < 0.1:
            glLineWidth(4.0)
            self.draw_line(cx - size, cy, cx + size, cy)
            return
        
        # Eye white
        glColor3f(1.0, 1.0, 1.0)
        eye_height = size * blink_factor
        self.draw_ellipse(cx, cy, size, eye_height, True)
        
        # Eye outline
        glColor3f(*self.current_color)
        glLineWidth(3.0)
        self.draw_ellipse(cx, cy, size, eye_height, False)
        
        # Pupil
        glColor3f(0.1, 0.1, 0.1)
        pupil_size = size * 0.6
        pupil_x = cx + pupil_offset_x * size * 0.3
        pupil_y = cy + pupil_offset_y * eye_height * 0.3
        self.draw_circle(pupil_x, pupil_y, pupil_size, True)
        
        # Highlight
        glColor3f(1.0, 1.0, 1.0)
        highlight_size = pupil_size * 0.3
        self.draw_circle(pupil_x - highlight_size*0.5, pupil_y + highlight_size*0.5, highlight_size, True)
    
    def draw_face(self, t):
        """Draw the robot face with current expression"""
        glClear(GL_COLOR_BUFFER_BIT)
        
        # Update blinking
        self.update_blink(t)
        
        # Calculate animation values
        breathing = math.sin(1.2 * t) * 0.03
        
        # Add speaking animation
        if self.is_speaking:
            breathing += math.sin(12 * t) * 0.02
        
        # Head position
        head_x = self.face_center_x
        head_y = self.face_center_y + breathing
        head_size = self.face_size
        
        # Draw face background with glow effect
        if self.is_recording:
            glow_intensity = 0.3 + 0.2 * abs(math.sin(4 * t))
            glColor4f(1.0, 0.3, 0.3, glow_intensity)
            self.draw_circle(head_x, head_y, head_size * 0.8, True)
        
        # Main face circle
        glColor3f(0.15, 0.15, 0.20)
        self.draw_circle(head_x, head_y, head_size * 0.7, True)
        
        # Face outline with expression color
        glColor3f(*self.current_color)
        glLineWidth(4.0)
        self.draw_circle(head_x, head_y, head_size * 0.7, False)
        
        # Expression-specific features
        if self.current_expression == "happy":
            eye_blink = 0.8 if not self.is_blinking else 0.0
            self.draw_eye(head_x - 0.35, head_y + 0.15, 0.12, eye_blink)
            self.draw_eye(head_x + 0.35, head_y + 0.15, 0.12, eye_blink)
            
            smile_points = self.generate_quadratic_curve(
                head_x - 0.4, head_y - 0.2,
                head_x, head_y - 0.45,
                head_x + 0.4, head_y - 0.2
            )
            glLineWidth(6.0)
            glColor3f(*self.current_color)
            self.draw_curve(smile_points)
            
            glColor4f(1.0, 0.6, 0.7, 0.6)
            self.draw_circle(head_x - 0.55, head_y - 0.05, 0.08, True)
            self.draw_circle(head_x + 0.55, head_y - 0.05, 0.08, True)
            
        elif self.current_expression == "sad":
            pupil_y_offset = -0.3
            self.draw_eye(head_x - 0.35, head_y + 0.1, 0.12, 1.0, 0, pupil_y_offset)
            self.draw_eye(head_x + 0.35, head_y + 0.1, 0.12, 1.0, 0, pupil_y_offset)
            
            glColor3f(*self.current_color)
            glLineWidth(4.0)
            self.draw_line(head_x - 0.5, head_y + 0.35, head_x - 0.2, head_y + 0.25)
            self.draw_line(head_x + 0.2, head_y + 0.25, head_x + 0.5, head_y + 0.35)
            
            frown_points = self.generate_quadratic_curve(
                head_x - 0.3, head_y - 0.25,
                head_x, head_y - 0.15,
                head_x + 0.3, head_y - 0.25
            )
            glLineWidth(5.0)
            self.draw_curve(frown_points)
            
            glColor4f(0.4, 0.8, 1.0, 0.8)
            tear_y = head_y - 0.05 - 0.3 * abs(math.sin(t * 2))
            self.draw_ellipse(head_x - 0.5, tear_y, 0.03, 0.08, True)
        
        elif self.current_expression == "surprised":
            self.draw_eye(head_x - 0.35, head_y + 0.15, 0.15, 1.0)
            self.draw_eye(head_x + 0.35, head_y + 0.15, 0.15, 1.0)
            
            glColor3f(*self.current_color)
            glLineWidth(6.0)
            self.draw_circle(head_x, head_y - 0.3, 0.15, False)
            
            glLineWidth(4.0)
            self.draw_line(head_x - 0.5, head_y + 0.4, head_x - 0.2, head_y + 0.4)
            self.draw_line(head_x + 0.2, head_y + 0.4, head_x + 0.5, head_y + 0.4)
        
        else:  # neutral or default
            self.draw_eye(head_x - 0.35, head_y + 0.15, 0.12, 1.0)
            self.draw_eye(head_x + 0.35, head_y + 0.15, 0.12, 1.0)
            
            glColor3f(*self.current_color)
            glLineWidth(4.0)
            self.draw_line(head_x - 0.3, head_y - 0.3, head_x + 0.3, head_y - 0.3)
            
            glLineWidth(3.0)
            self.draw_line(head_x - 0.5, head_y + 0.35, head_x - 0.2, head_y + 0.35)
            self.draw_line(head_x + 0.2, head_y + 0.35, head_x + 0.5, head_y + 0.35)
        
        # Draw buttons
        self.draw_buttons()
        
        # Draw status information
        self.draw_status_info()
        
        # Swap buffers
        pygame.display.flip()

    def test_compreface_connection(self):
        """Test connection to CompreFace API"""
        try:
            headers = {
                'x-api-key': "e4648f5d-3ee5-4005-88e4-4bd9dfbef942",
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{self.compreface_url}/api/v1/recognition/subjects", 
                headers=headers, 
                timeout=5
            )
            
            if response.status_code == 200:
                self.face_recognition_status = "Connected"
                logger.info("CompreFace connection successful")
            else:
                self.face_recognition_status = f"Error {response.status_code}"
                logger.warning(f"CompreFace responded with status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            self.face_recognition_status = "Connection Error"
            logger.error(f"Cannot connect to CompreFace at {self.compreface_url}: {e}")
            self.face_recognition_enabled = False
    
    def capture_face_image(self):
        """Capture image from camera for face recognition"""
        try:
            logger.info("Starting camera for face capture...")
            cap = cv2.VideoCapture(0)
            
            if not cap.isOpened():
                logger.error("Cannot open camera")
                return None
            
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            ret, frame = cap.read()
            cap.release()
            
            if not ret:
                logger.error("Failed to capture frame")
                return None
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            temp_image = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            cv2.imwrite(temp_image.name, cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
            temp_image.close()
            
            logger.info(f"Face image captured: {temp_image.name}")
            return temp_image.name
        except Exception as e:
            logger.error(f"Error capturing face image: {e}")
            return None
    
    def recognize_face(self, image_path):
        """Recognize face using CompreFace API"""
        try:
            logger.info("Sending image to CompreFace for recognition...")
            
            headers = {
                'x-api-key': "e4648f5d-3ee5-4005-88e4-4bd9dfbef942"
            }
            
            with open(image_path, 'rb') as image_file:
                files = {
                    'file': image_file,
                    'threshold': '0.5'
                }
                
                response = requests.post(
                    f"{self.compreface_url}/api/v1/recognition/recognize",
                    headers=headers,
                    files=files,
                    timeout=10
                )
            
            try:
                os.unlink(image_path)
            except:
                pass
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"CompreFace response: {result}")
                
                if result.get('result') and len(result['result']) > 0:
                    face_data = result['result'][0]
                    
                    if face_data.get('subjects') and len(face_data['subjects']) > 0:
                        subject = face_data['subjects'][0]
                        subject_name = subject.get('subject', 'Unknown')
                        confidence = subject.get('similarity', 0.0)
                        
                        logger.info(f"Face recognized: {subject_name} (confidence: {confidence:.2f})")
                        
                        return {
                            'recognized': True,
                            'name': subject_name,
                            'confidence': confidence,
                            'status': 'success'
                        }
                    else:
                        logger.info("Face detected but not recognized")
                        return {
                            'recognized': False,
                            'name': f'Unknown_User_{int(time.time())}',
                            'confidence': 0.0,
                            'status': 'face_detected_not_recognized'
                        }
                else:
                    logger.info("No face detected in image")
                    return {
                        'recognized': False,
                        'name': self.default_user_name,
                        'confidence': 0.0,
                        'status': 'no_face_detected'
                    }
            else:
                logger.error(f"CompreFace API error: {response.status_code} - {response.text}")
                return {
                    'recognized': False,
                    'name': self.default_user_name,
                    'confidence': 0.0,
                    'status': 'api_error'
                }
        except Exception as e:
            logger.error(f"Face recognition error: {e}")
            return {
                'recognized': False,
                'name': self.default_user_name,
                'confidence': 0.0,
                'status': 'error'
            }
    
    def test_face_recognition(self):
        """Test face recognition functionality"""
        if not self.face_recognition_enabled:
            logger.warning("Face recognition is disabled")
            return
        
        def face_test_worker():
            try:
                self.is_face_recognizing = True
                self.set_expression("confused")
                
                image_path = self.capture_face_image()
                if not image_path:
                    self.face_recognition_status = "Camera Error"
                    self.is_face_recognizing = False
                    return
                
                result = self.recognize_face(image_path)
                
                if result['recognized']:
                    self.face_recognition_status = f"Recognized: {result['name']}"
                    self.set_expression("happy")
                else:
                    self.face_recognition_status = f"Not recognized: {result['status']}"
                    self.set_expression("confused")
                
                self.recognized_user = result['name']
                self.face_confidence = result['confidence']
                
                logger.info(f"Face recognition test completed: {result}")
            except Exception as e:
                logger.error(f"Face recognition test error: {e}")
                self.face_recognition_status = "Test Error"
            finally:
                self.is_face_recognizing = False
        
        face_thread = threading.Thread(target=face_test_worker)
        face_thread.daemon = True
        face_thread.start()
    
    def start_continuous_conversation(self):
        """Start continuous conversation with face recognition"""
        if self.audio_thread and self.audio_thread.is_alive():
            logger.info("Conversation already in progress")
            return
        
        # Changed logic to use the greeted flag instead of checking recognized_user
        if not self.user_greeted:
            logger.info("Starting face recognition and greeting")
            self.audio_thread = threading.Thread(target=self.recognize_face_and_greet)
            self.audio_thread.daemon = True
            self.audio_thread.start()
        else:
            # If user already greeted, start the conversation
            logger.info("User already greeted, starting conversation")
            self.conversation_active = True
            self.audio_thread = threading.Thread(target=self.continuous_conversation_worker)
            self.audio_thread.daemon = True
            self.audio_thread.start()
    
    def recognize_face_and_greet(self):
        """Recognize face and greet the user before conversation"""
        try:
            # Face Recognition step
            self.is_face_recognizing = True
            self.set_expression("confused")
            logger.info("Starting face recognition process")
            
            image_path = self.capture_face_image()
            if image_path:
                logger.info(f"Face image captured: {image_path}")
                result = self.recognize_face(image_path)
                
                if result['recognized']:
                    self.user_name = result['name']
                    self.recognized_user = result['name']
                    self.face_confidence = result['confidence']
                    self.face_recognition_status = f"Recognized: {result['name']}"
                    self.set_expression("happy")
                    logger.info(f"Face recognized: {self.user_name} with confidence {self.face_confidence}")
                else:
                    self.user_name = self.default_user_name
                    self.recognized_user = "Unknown"
                    self.face_confidence = 0.0
                    self.face_recognition_status = f"Not recognized"
                    self.set_expression("neutral")
                    logger.info(f"Face not recognized, using default user name: {self.default_user_name}")
            else:
                self.user_name = self.default_user_name
                self.recognized_user = "Unknown"
                self.face_recognition_status = "Camera Error"
                logger.warning(f"Camera error, using default user name: {self.default_user_name}")
            
            self.is_face_recognizing = False
            
            # Get user conversation history from local database
            recent_conversations = self.db.get_recent_conversations(self.user_name, limit=2)
            conversation_summary = ""
            if recent_conversations:
                conversation_summary = "We've spoken before. "
                
            # Create greeting message
            greeting_message = f"Hello {self.recognized_user}! {conversation_summary}Press the green button to start the conversation with me."
            logger.info(f"Greeting message: '{greeting_message}'")
            self.last_ai_response = greeting_message
            
            # Speak the greeting
            self.is_speaking = True
            logger.info("Starting to speak greeting...")
            self.speak_text(greeting_message)
            self.is_speaking = False
            logger.info("Finished speaking greeting")
            
            # Set the flag indicating user has been greeted
            self.user_greeted = True
            logger.info("User has been greeted, ready for conversation")
            
            # Update the button text to indicate next step
            for button in self.buttons:
                if button["id"] == "voice_interaction":
                    button["text"] = "🎤 Start Conversation"
                    logger.info("Updated button text to 'Start Conversation'")
                    break
                    
        except Exception as e:
            logger.error(f"Face recognition and greeting error: {e}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.is_face_recognizing = False
            self.recognized_user = self.default_user_name  # Set a default in case of error
    
    def speak_text(self, text):
        """Generate and play TTS audio for the given text using local TTS"""
        try:
            logger.info(f"Speaking text with local TTS: '{text}'")
            
            # Try to use local TTS first
            if self.use_local_tts and self.tts_engine:
                try:
                    logger.info("Using local TTS engine")
                    
                    def tts_thread_func():
                        self.tts_engine.say(text)
                        self.tts_engine.runAndWait()
                    
                    # Run TTS in a separate thread to avoid blocking
                    tts_thread = threading.Thread(target=tts_thread_func)
                    tts_thread.daemon = True
                    tts_thread.start()
                    
                    # Wait for TTS to complete
                    tts_thread.join()
                    return True
                except Exception as e:
                    logger.error(f"Local TTS failed: {e}")
                    logger.info("Falling back to platform-specific TTS")
            
            # As a final fallback, try with platform-specific TTS
            try:
                logger.info("Using platform-specific TTS as a fallback")
                if os.name == 'posix':  # Linux
                    os.system(f'espeak "{text}"')
                elif os.name == 'nt':  # Windows
                    import win32com.client
                    speaker = win32com.client.Dispatch("SAPI.SpVoice")
                    speaker.Speak(text)
                logger.info("Platform-specific TTS completed")
                return True
            except Exception as fallback_error:
                logger.error(f"All TTS methods failed: {fallback_error}")
                return False
                
        except Exception as e:
            logger.error(f"Text-to-speech error: {e}")
            logger.error(f"Speech error traceback: {traceback.format_exc()}")
            return False
    
    def continuous_conversation_worker(self):
        """Worker function for continuous conversation with server-side transcription"""
        try:
            # Start continuous conversation loop
            while self.conversation_active:
                try:
                    self.is_recording = True
                    self.is_processing = False
                    self.is_speaking = False
                    
                    audio_path = self.record_audio()
                    self.is_recording = False
                    
                    if not audio_path:
                        logger.error("Failed to record audio")
                        break
                    
                    if not self.conversation_active:
                        break
                    
                    # Send audio to server for STT only
                    self.is_processing = True
                    stt_response = self.send_audio_to_server(audio_path)
                    
                    try:
                        os.unlink(audio_path)
                    except:
                        pass
                    
                    if not stt_response or not stt_response.get('success', False):
                        logger.error("Failed to get STT response")
                        self.is_processing = False
                        continue
                    
                    # Process the transcribed text
                    user_input = stt_response.get('text', '')
                    self.last_user_input = user_input
                    
                    if not user_input or len(user_input.strip()) < 3:
                        logger.info("No meaningful speech detected - entering sleep mode")
                        
                        self.set_expression("sleepy")
                        self.last_ai_response = "Going to sleep..."
                        
                        time.sleep(2)
                        self.set_expression("neutral")
                        self.is_processing = False
                        continue
                    
                    # Get emotion analysis - using server API
                    user_emotion_response = self.analyze_emotion(user_input)
                    user_emotion = user_emotion_response.get('emotion', 'neutral')
                    
                    # Get recent conversations from local database
                    recent_conversations = self.db.get_recent_conversations(self.user_name)
                    
                    # Generate LLM response with robot expression - locally on Pi
                    response_data = self.generate_llm_response(
                        user_input=user_input,
                        user_emotion=user_emotion,
                        user_name=self.user_name,
                        recent_conversations=recent_conversations
                    )
                    
                    self.is_processing = False
                    
                    # Save conversation to local database
                    try:
                        self.db.add_conversation(
                            user_name=self.user_name,
                            user_input=user_input,
                            ai_response=response_data["text_response"],
                            language_used=response_data["language_used"]
                        )
                    except Exception as db_error:
                        logger.error(f"Failed to save conversation to database: {db_error}")
                    
                    if not self.conversation_active:
                        break
                    
                    # Update robot expression
                    robot_expression = response_data.get('robot_expression', 'happy')
                    self.set_expression(robot_expression)
                    
                    # Text to speech and playback
                    self.is_speaking = True
                    self.last_ai_response = response_data["text_response"]
                    # Use ElevenLabs TTS (preferred) or fallback to local TTS
                    self.text_to_speech_elevenlabs(response_data["text_response"], robot_expression)
                    self.is_speaking = False
                    
                    logger.info("Voice interaction turn completed - continuing conversation")
                    time.sleep(0.5)
                    
                except Exception as turn_error:
                    logger.error(f"Error in conversation turn: {turn_error}")
                    import traceback
                    logger.error(f"Conversation turn traceback: {traceback.format_exc()}")
                    time.sleep(1)
                    continue
            
            logger.info("Continuous conversation ended")
        except Exception as e:
            logger.error(f"Continuous conversation error: {e}")
            import traceback
            logger.error(f"Continuous conversation traceback: {traceback.format_exc()}")
        finally:
            self.conversation_active = False
            self.is_recording = False
            self.is_processing = False
            self.is_speaking = False
            self.is_face_recognizing = False
            
            # Reset button text after conversation ends
            for button in self.buttons:
                if button["id"] == "voice_interaction":
                    button["text"] = "🎤 Start Voice Chat"
                    break
        
    def draw_buttons(self):
        """Draw control buttons"""
        for button in self.buttons:
            if not button["enabled"]:
                continue
            
            if button["id"] == "voice_interaction":
                if self.conversation_active:
                    glColor3f(0.2, 1.0, 0.2)
                elif self.is_face_recognizing:
                    glColor3f(1.0, 0.6, 0.2)
                elif self.is_recording:
                    glColor3f(1.0, 0.3, 0.3)
                elif self.is_processing:
                    glColor3f(1.0, 0.8, 0.2)
                elif self.is_speaking:
                    glColor3f(0.3, 1.0, 0.3)
                else:
                    glColor3f(*button["color"])
            else:
                glColor3f(*button["color"])
            
            self.draw_rounded_rectangle(
                button["x"], button["y"],
                button["width"], button["height"],
                0.05, True
            )
            
            glColor3f(1.0, 1.0, 1.0)
            glLineWidth(2.0)
            self.draw_rounded_rectangle(
                button["x"], button["y"],
                button["width"], button["height"],
                0.05, False
            )
    
    def draw_status_info(self):
        """Draw status information on screen"""
        # Render status text to surfaces
        status_texts = [
            f"API: {self.api_status}",
            f"Face Recognition: {self.face_recognition_status}",
            f"Current User: {self.user_name}"
        ]
        
        if self.last_user_input:
            status_texts.append(f"You: {self.last_user_input[:50]}")
        
        if self.last_ai_response:
            status_texts.append(f"AI: {self.last_ai_response[:50]}")
        
        if self.is_recording:
            status_texts.append("🎤 Recording...")
        elif self.is_processing:
            status_texts.append("⏳ Processing...")
        elif self.is_speaking:
            status_texts.append("🔊 Speaking...")
        elif self.conversation_active:
            status_texts.append("💬 Conversation Active")
        
        # Since OpenGL doesn't have text rendering built-in,
        # we use a dummy rendering only to simulate text
        # In a real implementation, you would need to use pygame or other
        # libraries to render text to textures and then display them
    
    def run(self):
        """Main application loop"""
        while self.running:
            current_time = time.time() - self.start_time
            
            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_mouse_click(event.pos)
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.start_voice_interaction()
                    elif event.key == pygame.K_c:
                        self.start_continuous_conversation()
                    elif event.key == pygame.K_s:
                        self.stop_interaction()
                    elif event.key == pygame.K_t:
                        self.test_api_connection()
                    elif event.key == pygame.K_f:
                        self.test_face_recognition()
            
            # Update expression transitions
            self.update_expression_transition()
            
            # Draw the face
            self.draw_face(current_time)
            
            # Control frame rate
            self.clock.tick(60)
        
        # Cleanup
        self.stop_interaction()
        pygame.quit()
        sys.exit()
if __name__ == "__main__":
    import argparse
    import traceback
    
    parser = argparse.ArgumentParser(description='Robot Voice Assistant Interactive Interface with Face Recognition')
    parser.add_argument('--api-url', type=str, default="http://localhost:8001", 
                       help='API server URL (default: http://localhost:8001)')
    parser.add_argument('--user', type=str, default="test_user", 
                       help='User name for API requests (default: test_user)')
    parser.add_argument('--width', type=int, default=900, 
                       help='Window width (default: 900)')
    parser.add_argument('--height', type=int, default=700, 
                       help='Window height (default: 700)')
    parser.add_argument('--compreface-url', type=str, default="http://localhost:8000",
                       help='CompreFace server URL (default: http://localhost:8000)')
    parser.add_argument('--compreface-api-key', type=str, default="",
                       help='CompreFace API key')
    
    args = parser.parse_args()
    
    try:
        print("Initializing Robot Voice Assistant with Face Recognition...")
        client = VoiceAssistantClient(
            width=args.width,
            height=args.height,
            api_url=args.api_url,
            user_name=args.user,
            compreface_url=args.compreface_url,
            compreface_api_key=args.compreface_api_key
        )
        print("Starting application...")
        client.run()
    except KeyboardInterrupt:
        print("\n👋 Application interrupted by user. Goodbye!")
    except Exception as e:
        logger.error(f"Application error: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        print(f"❌ Error: {e}")
        sys.exit(1)