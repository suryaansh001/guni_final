import os
import io
import time
import traceback
import logging
import requests
import hashlib
import sqlite3
import tempfile
import pyttsx3
import uuid
import json
import urllib.parse
import paho.mqtt.client as mqtt
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Response, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from pydantic import BaseModel
from datetime import datetime
from groq import Groq
from typing import Optional

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

# --- LocalDatabase class ---
class LocalDatabase:
    """Local SQLite database for storing conversations and user data"""
    
    def __init__(self, db_path="voice_assistant_enhanced.db"):
        self.db_path = db_path
        self.init_database()
        self.check_database_integrity()
        self.initialize_default_api_keys()
    
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
            
            # API Keys Management Table (KEEP ONLY THIS ONE)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL UNIQUE,
                    api_key TEXT NOT NULL,
                    description TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_by TEXT DEFAULT 'system',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    last_used_at TIMESTAMP,
                    usage_count INTEGER DEFAULT 0,
                    CHECK(service_name IN ('groq', 'elevenlabs', 'compreface', 'openai', 'gemini', 'anthropic', 'huggingface'))
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
            
            # Admin API Key Management Log
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_key_admin_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_type TEXT CHECK(action_type IN ('create', 'update', 'delete', 'activate', 'deactivate')) NOT NULL,
                    service_name TEXT NOT NULL,
                    old_key_hash TEXT,
                    new_key_hash TEXT,
                    admin_user TEXT NOT NULL,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            # API Key Usage Log Table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS api_key_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_name TEXT NOT NULL,
                    api_key_id INTEGER,
                    operation_type TEXT,
                    status TEXT CHECK(status IN ('success', 'failed', 'expired', 'rate_limited')),
                    error_message TEXT,
                    response_time_ms INTEGER,
                    user_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (api_key_id) REFERENCES api_keys (id)
                )
            ''')
            conn.commit()
    def initialize_default_api_keys(self):
        """Initialize default API keys from environment variables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check if API keys already exist
            cursor.execute('SELECT COUNT(*) FROM api_keys')
            existing_count = cursor.fetchone()[0]
            
            if existing_count == 0:
                # Load from environment variables as default
                default_keys = {
                    'groq': {
                        'key': os.getenv("GROQ_API_KEY", ""),
                        'description': 'Groq LLM API for text generation'
                    },
                    'elevenlabs': {
                        'key': os.getenv("ELEVENLABS_API_KEY", ""),
                        'description': 'ElevenLabs TTS API for voice synthesis'
                    },
                    'compreface': {
                        'key': "e4648f5d-3ee5-4005-88e4-4bd9dfbef942",
                        'description': 'CompreFace API for face recognition'
                    },
                    'huggingface': {
                        'key': os.getenv("HUGGINGFACE_API_KEY", ""),
                        'description': 'Hugging Face API for speech-to-text'
                    }
                }
                
                for service, config in default_keys.items():
                    if config['key']:  # Only insert if key exists
                        cursor.execute('''
                            INSERT OR IGNORE INTO api_keys (service_name, api_key, description, created_by)
                            VALUES (?, ?, ?, ?)
                        ''', (service, config['key'], config['description'], 'system_init'))
                
                conn.commit()
                logger.info("Default API keys initialized from environment variables")
    # API Key Management Methods
    def get_api_key(self, service_name):
        """Get active API key for a service"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM api_keys 
                WHERE service_name = ? AND is_active = TRUE 
                AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                ORDER BY created_at DESC
                LIMIT 1
            ''', (service_name,))
            
            result = cursor.fetchone()
            if result:
                # Update last used timestamp and usage count
                cursor.execute('''
                    UPDATE api_keys 
                    SET last_used_at = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                    WHERE id = ?
                ''', (result['id'],))
                conn.commit()
                
                return dict(result)
            return None
    
    def add_api_key(self, service_name, api_key, description=None, admin_user='admin', expires_at=None):
        """Add or update API key for a service"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Deactivate existing keys for this service
            cursor.execute('''
                UPDATE api_keys 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE service_name = ? AND is_active = TRUE
            ''', (service_name,))
            
            # Insert new API key
            cursor.execute('''
                INSERT INTO api_keys (service_name, api_key, description, created_by, expires_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (service_name, api_key, description, admin_user, expires_at))
            
            new_key_id = cursor.lastrowid
            
            # Log the admin action
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            cursor.execute('''
                INSERT INTO api_key_admin_log (action_type, service_name, new_key_hash, admin_user, reason)
                VALUES (?, ?, ?, ?, ?)
            ''', ('create', service_name, key_hash, admin_user, f"Added new API key for {service_name}"))
            
            conn.commit()
            logger.info(f"API key added for service: {service_name} by admin: {admin_user}")
            return new_key_id
    
    def update_api_key(self, service_name, new_api_key, admin_user='admin', reason=None):
        """Update API key for a service"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current active key
            cursor.execute('''
                SELECT api_key FROM api_keys 
                WHERE service_name = ? AND is_active = TRUE
            ''', (service_name,))
            
            old_key_result = cursor.fetchone()
            old_key_hash = None
            if old_key_result:
                old_key_hash = hashlib.sha256(old_key_result[0].encode()).hexdigest()[:16]
            
            # Deactivate old key and add new one
            result = self.add_api_key(service_name, new_api_key, f"Updated by {admin_user}", admin_user)
            
            # Log the update action
            new_key_hash = hashlib.sha256(new_api_key.encode()).hexdigest()[:16]
            cursor.execute('''
                INSERT INTO api_key_admin_log (action_type, service_name, old_key_hash, new_key_hash, admin_user, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', ('update', service_name, old_key_hash, new_key_hash, admin_user, reason or f"Updated API key for {service_name}"))
            
            conn.commit()
            logger.info(f"API key updated for service: {service_name} by admin: {admin_user}")
            return result
    def deactivate_api_key(self, service_name, admin_user='admin', reason=None):
        """Deactivate API key for a service"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE api_keys 
                SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP
                WHERE service_name = ? AND is_active = TRUE
            ''', (service_name,))
            
            # Log the deactivation
            cursor.execute('''
                INSERT INTO api_key_admin_log (action_type, service_name, admin_user, reason)
                VALUES (?, ?, ?, ?)
            ''', ('deactivate', service_name, admin_user, reason or f"Deactivated API key for {service_name}"))
            
            conn.commit()
            logger.info(f"API key deactivated for service: {service_name} by admin: {admin_user}")
    def log_api_key_usage(self, service_name, operation_type, status, error_message=None, response_time_ms=None, user_name=None):
        """Log API key usage for monitoring"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get current API key ID
            cursor.execute('''
                SELECT id FROM api_keys 
                WHERE service_name = ? AND is_active = TRUE
                LIMIT 1
            ''', (service_name,))
            
            api_key_result = cursor.fetchone()
            api_key_id = api_key_result[0] if api_key_result else None
            
            cursor.execute('''
                INSERT INTO api_key_usage_log 
                (service_name, api_key_id, operation_type, status, error_message, response_time_ms, user_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (service_name, api_key_id, operation_type, status, error_message, response_time_ms, user_name))
            
            conn.commit()
    
    def get_api_key_usage_stats(self, service_name=None, days=30):
        """Get API key usage statistics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            where_clause = "WHERE created_at >= date('now', '-{} days')".format(days)
            if service_name:
                where_clause += " AND service_name = '{}'".format(service_name)
            
            cursor.execute(f'''
                SELECT service_name, 
                       COUNT(*) as total_calls,
                       SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_calls,
                       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_calls,
                       AVG(response_time_ms) as avg_response_time,
                       MAX(created_at) as last_call
                FROM api_key_usage_log 
                {where_clause}
                GROUP BY service_name
                ORDER BY total_calls DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]

    def get_all_api_keys(self):
        """Get all API keys with their status (admin function)"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT id, service_name, 
                       SUBSTR(api_key, 1, 8) || '...' || SUBSTR(api_key, -4) as masked_key,
                       description, is_active, created_by, created_at, updated_at, 
                       expires_at, last_used_at, usage_count
                FROM api_keys 
                ORDER BY service_name, created_at DESC
            ''')
            
            return [dict(row) for row in cursor.fetchall()]
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

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

db = LocalDatabase()

def get_api_keys():
    groq_key_data = db.get_api_key('groq')
    elevenlabs_key_data = db.get_api_key('elevenlabs')
    huggingface_key_data = db.get_api_key('huggingface')
    return {
        'groq': groq_key_data['api_key'] if groq_key_data else None,
        'elevenlabs': elevenlabs_key_data['api_key'] if elevenlabs_key_data else None,
        'huggingface': huggingface_key_data['api_key'] if huggingface_key_data else None
    }

api_keys = get_api_keys()

groq_client = Groq(api_key=api_keys['groq']) if api_keys['groq'] else None
elevenlabs_client = ElevenLabs(api_key=api_keys['elevenlabs']) if api_keys['elevenlabs'] else None

HUGGINGFACE_MODEL_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
def transcribe_audio_huggingface(audio_bytes, huggingface_api_key, filename="audio.wav"):
    """
    Transcribe audio using Hugging Face Whisper model
    Send raw audio data directly instead of multipart form data
    """
    headers = {
        "Authorization": f"Bearer {huggingface_api_key}",
        "Content-Type": "audio/wav"  # Set appropriate content type based on audio format
    }
    
    try:
        # Send raw audio bytes directly in the request body
        response = requests.post(
            HUGGINGFACE_MODEL_URL,
            headers=headers,
            data=audio_bytes,  # Send raw bytes instead of files
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "")
            logger.info(f"Hugging Face STT successful: {text[:100]}...")  # Log first 100 chars
            return text
        else:
            logger.error(f"Hugging Face STT failed with status {response.status_code}: {response.text}")
            return ""
            
    except requests.exceptions.Timeout:
        logger.error("Hugging Face STT request timed out")
        return ""
    except requests.exceptions.RequestException as e:
        logger.error(f"Hugging Face STT request failed: {e}")
        return ""
    except Exception as e:
        logger.error(f"Unexpected error in Hugging Face STT: {e}")
        return ""

# Alternative version that handles multiple audio formats dynamically
def transcribe_audio_huggingface_auto_format(audio_bytes, huggingface_api_key, filename="audio.wav"):
    """
    Enhanced version that tries to detect audio format from filename or content
    """
    # Determine content type based on filename extension
    content_type_map = {
        '.wav': 'audio/wav',
        '.mp3': 'audio/mpeg',
        '.flac': 'audio/flac',
        '.ogg': 'audio/ogg',
        '.m4a': 'audio/m4a',
        '.webm': 'audio/webm'
    }
    
    # Extract file extension
    file_ext = filename.lower().split('.')[-1] if '.' in filename else 'wav'
    if not file_ext.startswith('.'):
        file_ext = '.' + file_ext
    
    content_type = content_type_map.get(file_ext, 'audio/wav')  # Default to wav
    
    headers = {
        "Authorization": f"Bearer {huggingface_api_key}",
        "Content-Type": content_type
    }
    
    try:
        response = requests.post(
            HUGGINGFACE_MODEL_URL,
            headers=headers,
            data=audio_bytes,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get("text", "")
            logger.info(f"Hugging Face STT successful with {content_type}: {text[:100]}...")
            return text
        else:
            logger.error(f"Hugging Face STT failed with status {response.status_code}: {response.text}")
            return ""
            
    except Exception as e:
        logger.error(f"Hugging Face STT error: {e}")
        return ""

def tts_pyttsx3_fallback(text, language='en'):
    """Fallback TTS using pyttsx3 when ElevenLabs fails"""
    try:
        logger.info("Using pyttsx3 fallback TTS")
        
        # Create a temporary file for audio output
        temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_audio_path = temp_audio_file.name
        temp_audio_file.close()
        
        # Initialize pyttsx3
        engine = pyttsx3.init()
        
        # Set properties
        engine.setProperty('rate', 150)  # Speed of speech
        engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
        
        # Set voice based on language
        voices = engine.getProperty('voices')
        if voices:
            # Try to find appropriate voice for language
            for voice in voices:
                if language == 'hi' and ('hindi' in voice.name.lower() or 'hi' in voice.id.lower()):
                    engine.setProperty('voice', voice.id)
                    break
                elif language == 'en' and ('english' in voice.name.lower() or 'en' in voice.id.lower()):
                    engine.setProperty('voice', voice.id)
                    break
            else:
                # Use default voice if specific language not found
                engine.setProperty('voice', voices[0].id)
        
        # Save speech to file
        engine.save_to_file(text, temp_audio_path)
        engine.runAndWait()
        
        # Read the generated audio file
        with open(temp_audio_path, 'rb') as audio_file:
            audio_content = audio_file.read()
        
        # Clean up temp file
        try:
            os.unlink(temp_audio_path)
        except:
            pass
        
        logger.info(f"Generated fallback audio content of {len(audio_content)} bytes")
        return audio_content, "wav"  # Return format info
        
    except Exception as e:
        logger.error(f"pyttsx3 fallback TTS error: {e}")
        return None, None

def tts_elevenlabs(text, elevenlabs_client, voice_id="zgqefOY5FPQ3bB7OZTVR", model_id="eleven_multilingual_v2"):
    if not elevenlabs_client:
        logger.error("ElevenLabs client not available, trying fallback TTS")
        return tts_pyttsx3_fallback(text)
    
    try:
        audio_stream = elevenlabs_client.text_to_speech.stream(
            text=text,
            voice_id=voice_id,
            model_id=model_id
        )
        audio_chunks = [chunk for chunk in audio_stream]
        audio_content = b''.join(audio_chunks)
        logger.info(f"Generated audio content of {len(audio_content)} bytes")
        return audio_content, "mp3"  # Return format info
    except Exception as e:
        logger.error(f"ElevenLabs TTS error: {e}, trying fallback TTS")
        return tts_pyttsx3_fallback(text)

available_expressions = {
    "cute_neutral": "Cute neutral expression - default, calm, balanced with gentle smile",
    "happy": "Happy expression - general happiness, contentment, joy",
    "overjoyed": "Overjoyed expression - extreme happiness, excitement, enthusiasm",
    "excited": "Excited expression - extreme happiness, excitement, enthusiasm", 
    "love": "Love expression - affection, adoration, romantic feelings",
    "in_love": "In Love expression - affection, adoration, romantic feelings",
    "sad": "Sad expression - sadness, disappointment, melancholy",
    "crying": "Crying expression - sadness, disappointment, melancholy",
    "heartbroken": "Heartbroken expression - sadness, disappointment, melancholy",
    "angry": "Angry expression - anger, frustration, rage",
    "furious": "Furious expression - anger, frustration, rage", 
    "sleepy": "Sleepy expression - tiredness, drowsiness, low energy",
    "surprised": "Surprised expression - surprise, amazement, shock",
    "shocked": "Shocked expression - surprise, amazement, shock",
    "confused": "Confused expression - confusion, bewilderment, uncertainty",
    "money_eyes": "Money Eyes expression - greed, excitement about money",
    "playful": "Playful expression - playfulness, teasing, fun",
    "mischievous": "Mischievous expression - playfulness, teasing, fun",
    "talking": "Talking expression - speaking, communicating",
    "laughing": "Laughing expression - happiness, joy, contentment",
    "neutral": "Neutral expression - default, calm, balanced with gentle smile"
}

def map_user_emotion_to_robot(user_emotion):
    emotion_mapping = {
        "joy": "happy",
        "happiness": "happy",
        "excitement": "excited",
        "overjoyed": "overjoyed",
        "enthusiasm": "excited",
        "sadness": "sad",
        "crying": "crying",
        "heartbreak": "heartbroken",
        "depression": "sad",
        "anger": "angry",
        "rage": "furious",
        "fury": "furious",
        "irritation": "angry",
        "surprise": "surprised",
        "shock": "shocked",
        "amazement": "surprised",
        "fear": "confused",
        "anxiety": "confused",
        "worry": "confused",
        "confusion": "confused",
        "disgust": "confused",
        "neutral": "cute_neutral",
        "love": "love",
        "affection": "in_love",
        "romance": "love",
        "playful": "playful",
        "mischief": "mischievous",
        "tired": "sleepy",
        "sleepy": "sleepy",
        "drowsy": "sleepy"
    }
    user_emotion_lower = user_emotion.lower()
    if user_emotion_lower in emotion_mapping:
        return emotion_mapping[user_emotion_lower]
    for key, value in emotion_mapping.items():
        if key in user_emotion_lower:
            return value
    return "happy"

def generate_llm_response(user_input, user_emotion, user_name, recent_conversations=None):
    start_time = time.time()
    if not groq_client:
        error_msg = "Groq client not available - API key missing or invalid"
        db.log_api_key_usage('groq', 'generate_response', 'failed', error_msg, user_name=user_name)
        return {
            "robot_emotion": "neutral",
            "robot_expression": "happy",
            "text_response": "I'm sorry, I'm having trouble connecting to the LLM service right now.",
            "language_used": "english"
        }
    preferred_language = "english"
    try:
        user_details = db.get_user_details(user_name)
        if user_details:
            preferred_language = user_details.get('preferred_language', 'english')
        else:
            db.ensure_user_exists(user_name)
            preferred_language = 'english'
        conversation_history = ""
        if recent_conversations:
            for msg in recent_conversations:
                conversation_history += f"User: {msg.get('user', '')}\nAssistant: {msg.get('assistant', '')}\n"
        expressions_list = "\n".join([f"  - {emotion}: {description}" for emotion, description in available_expressions.items()])
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

EXPRESSION USAGE GUIDELINES:
- For very positive/enthusiastic responses: Use "overjoyed", "excited", "laughing"
- For romantic/affectionate content: Use "love", "in_love"  
- For regular positive responses: Use "happy", "playful"
- For sad content: Use "sad", "crying", "heartbroken" (based on intensity)
- For anger: Use "angry", "furious" (based on intensity)
- For surprise: Use "surprised", "shocked" (based on intensity)
- For tiredness/end of conversation: Use "sleepy"
- For speaking: Use "talking" (mainly for system use)
- For neutral/default: Use "cute_neutral", "neutral"

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

IMPORTANT: For ROBOT_EXPRESSION, use only these exact words: cute_neutral, happy, overjoyed, excited, love, in_love, sad, crying, heartbroken, angry, furious, sleepy, surprised, shocked, confused, money_eyes, playful, mischievous, talking, laughing, neutral"""
        user_prompt = f"User says: {user_input}"
        response = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            max_tokens=500
        )
        response_time_ms = int((time.time() - start_time) * 1000)
        db.log_api_key_usage('groq', 'generate_response', 'success', response_time_ms=response_time_ms, user_name=user_name)
        llm_response = response.choices[0].message.content.strip()
        logger.info(f"LLM Response: {llm_response}")
        detected_language = "english"
        robot_expression = "happy"
        text_response = "I'm here to help you!"
        try:
            lines = llm_response.split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('LANGUAGE:'):
                    detected_language = line.replace('LANGUAGE:', '').strip().lower()
                elif line.startswith('ROBOT_EXPRESSION:'):
                    expression_part = line.replace('ROBOT_EXPRESSION:', '').strip().lower()
                    if expression_part in available_expressions:
                        robot_expression = expression_part
                    else:
                        logger.warning(f"Invalid expression from LLM: {expression_part}, using default 'happy'")
                elif line.startswith('TEXT_RESPONSE:'):
                    text_response = line.replace('TEXT_RESPONSE:', '').strip()
            if text_response == "I'm here to help you!":
                text_lines = []
                for line in lines:
                    if not any(marker in line for marker in ['LANGUAGE:', 'ROBOT_EXPRESSION:', 'TEXT_RESPONSE:']):
                        text_lines.append(line.strip())
                if text_lines:
                    text_response = ' '.join(text_lines)
        except Exception as e:
            logger.error(f"Error parsing LLM response: {e}")
            robot_expression = map_user_emotion_to_robot(user_emotion)
            text_response = llm_response
        if detected_language != preferred_language:
            try:
                db.update_user_details(user_name, {"preferred_language": detected_language})
                logger.info(f"Updated language preference for {user_name}: {detected_language}")
            except Exception as update_error:
                logger.error(f"Failed to update language preference: {update_error}")
        return {
            "robot_emotion": robot_expression,
            "robot_expression": robot_expression,
            "text_response": text_response,
            "language_used": detected_language
        }
    except Exception as e:
        response_time_ms = int((time.time() - start_time) * 1000)
        db.log_api_key_usage('groq', 'generate_response', 'failed', str(e), response_time_ms, user_name)
        logger.error(f"LLM generation error: {e}")
        logger.error(f"LLM error traceback: {traceback.format_exc()}")
        fallback_expression = map_user_emotion_to_robot(user_emotion)
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

@app.post("/process_audio")
async def process_audio(
    audio: UploadFile = File(...),
    user_name: str = Form(...)
):
    """
    Receives audio from Raspberry Pi, processes it, and returns robot expression, LLM text, and TTS audio.
    """
    audio_bytes = await audio.read()
    logger.info(f"Received audio file from user: {user_name}")
    transcript = transcribe_audio_huggingface(audio_bytes, api_keys['huggingface'])
    logger.info(f"Transcribed text: {transcript}")
    
    # Check for short input (sleep trigger)
    transcript_clean = transcript.strip()
    if len(transcript_clean) < 7:
        logger.info(f"Short input detected (length: {len(transcript_clean)}), triggering sleep mode")
        # Return sleepy response for short inputs
        sleep_text = "I'm feeling a bit sleepy now. Let me rest for a moment."
        audio_result = tts_elevenlabs(sleep_text, elevenlabs_client)
        
        # Handle the new return format (content, format)
        if audio_result and len(audio_result) == 2:
            audio_content, audio_format = audio_result
        else:
            audio_content, audio_format = None, None
        
        if not audio_content:
            fallback_result = tts_pyttsx3_fallback(sleep_text, 'en')
            if fallback_result and len(fallback_result) == 2:
                audio_content, audio_format = fallback_result
        
        # Store the conversation
        db.add_conversation(user_name, transcript, sleep_text, language_used="english")
        
        if not audio_content:
            raise HTTPException(status_code=500, detail="Failed to generate sleep audio")
        
        # Set proper media type based on audio format
        media_type = "audio/wav" if audio_format == "wav" else "audio/mpeg"
        
        return Response(
            content=audio_content,
            media_type=media_type,
            headers={
                "X-Robot-Expression": "sleepy",
                "X-LLM-Text": urllib.parse.quote(sleep_text, safe=''),
                "X-Language-Used": "english",
                "X-Audio-Format": audio_format,
                "Content-Length": str(len(audio_content)),
                "Accept-Ranges": "bytes"
            }
        )
    
    user_emotion = "neutral"  # For now, stub. You can add emotion analysis if needed.
    recent_conversations = db.get_recent_conversations(user_name, limit=5)
    llm_result = generate_llm_response(transcript, user_emotion, user_name, recent_conversations)
    robot_expression = llm_result.get("robot_expression", "happy")
    llm_text = llm_result.get("text_response", "I'm here to help you!")
    language_used = llm_result.get("language_used", "english")
    
    # Map language for TTS
    tts_language = 'hi' if language_used in ['hindi', 'hi'] else 'en'
    audio_result = tts_elevenlabs(llm_text, elevenlabs_client)
    
    # Handle the new return format (content, format)
    if audio_result and len(audio_result) == 2:
        audio_content, audio_format = audio_result
    else:
        audio_content, audio_format = None, None
    
    # If ElevenLabs fails, the function automatically falls back to pyttsx3
    if not audio_content:
        logger.warning("Both ElevenLabs and fallback TTS failed, trying basic fallback")
        fallback_result = tts_pyttsx3_fallback(llm_text, tts_language)
        if fallback_result and len(fallback_result) == 2:
            audio_content, audio_format = fallback_result
        else:
            audio_content, audio_format = None, None
    
    db.add_conversation(user_name, transcript, llm_text, language_used=language_used)
    
    if not audio_content:
        raise HTTPException(status_code=500, detail="Failed to generate audio")

    # Encode text for HTTP headers (must be ASCII-compatible)
    import base64
    import urllib.parse
    
    # URL encode the text to make it ASCII-safe for headers
    encoded_llm_text = urllib.parse.quote(llm_text, safe='')
    
    # Set proper media type based on audio format
    media_type = "audio/wav" if audio_format == "wav" else "audio/mpeg"
    
    return Response(
        content=audio_content,
        media_type=media_type,
        headers={
            "X-Robot-Expression": robot_expression,
            "X-LLM-Text": encoded_llm_text,
            "X-Language-Used": language_used,
            "X-Audio-Format": audio_format,
            "Content-Length": str(len(audio_content)),
            "Accept-Ranges": "bytes"
        }
    )
    
@app.get("/available_expressions")
def get_available_expressions():
    """Get the list of available robot expressions and their meanings"""
    return available_expressions
@app.get("/health")
def health_check():
    """Health check endpoint to verify API is running"""
    return {"status": "ok", "message": "API is running smoothly"}
# --- Additional API routes for all database and logic functions ---
from fastapi import Query
from typing import Optional

@app.get("/api_keys")
def api_get_all_api_keys():
    """Get all API keys (admin function)"""
    return db.get_all_api_keys()

@app.get("/api_key_usage_stats")
def api_get_api_key_usage_stats(service_name: Optional[str] = None, days: int = 30):
    """Get API key usage statistics"""
    return db.get_api_key_usage_stats(service_name, days)

@app.get("/user/{user_name}")
def api_get_user_details(user_name: str):
    """Get user details"""
    return db.get_user_details(user_name)

@app.post("/user/{user_name}")
def api_update_user_details(user_name: str, user_details: dict):
    """Update user details"""
    db.update_user_details(user_name, user_details)
    return {"status": "updated"}

@app.get("/conversations/{user_name}")
def api_get_recent_conversations(user_name: str, limit: int = 5):
    """Get recent conversations for a user"""
    return db.get_recent_conversations(user_name, limit)

@app.post("/conversation")
def api_add_conversation(user_name: str = Form(...), user_input: str = Form(...), ai_response: str = Form(...), language_used: str = Form('english'), summary: Optional[str] = Form(None)):
    """Add a new conversation"""
    db.add_conversation(user_name, user_input, ai_response, language_used, summary)
    return {"status": "added"}

@app.post("/unknown_user")
def api_create_unknown_user(face_photo: str = Form(...), confidence: Optional[float] = Form(None)):
    """Create an unknown user entry"""
    return {"unknown_user_name": db.create_unknown_user(face_photo, confidence)}

@app.post("/user_profile/{user_name}")
def api_create_or_update_user_profile(user_name: str, face_photo: Optional[str] = Form(None), info: Optional[str] = Form(None)):
    """Create or update user profile"""
    db.create_or_update_user_profile(user_name, face_photo, info)
    return {"status": "updated"}

@app.get("/user_profile/{user_name}")
def api_get_user_profile(user_name: str):
    """Get user profile"""
    return db.get_user_profile(user_name)

@app.post("/conversation_context")
def api_add_conversation_context(user_name: str = Form(...), context_type: str = Form(...), context_data: str = Form(...)):
    """Add conversation context"""
    db.add_conversation_context(user_name, context_type, context_data)
    return {"status": "added"}

@app.get("/conversation_context/{user_name}")
def api_get_conversation_context(user_name: str, context_type: Optional[str] = None):
    """Get conversation context for user"""
    return db.get_conversation_context(user_name, context_type)

# --- You can add more routes for any other non-UI logic from enhanced_4_new_option.py as needed ---

# --- ADMIN ROUTES FROM admin_fastapi_server.py ---
import paho.mqtt.client as mqtt
import uuid
import time

# --- MQTT CONFIG ---
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = "pi-controller/commands"
MQTT_TOPIC_RESPONSE = "pi-controller/responses"
MQTT_TOPIC_STATUS = "pi-controller/status"

command_responses = {}
pi_status = {"online": False, "last_seen": None}

# --- API KEY SECURITY (simple) ---
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "guni-admin-demo-key")

def verify_admin_api_key(request):
    api_key = request.headers.get("x-admin-api-key")
    if api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key.")

# --- MQTT CLIENT ---
class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
            client.subscribe(MQTT_TOPIC_RESPONSE)
            client.subscribe(MQTT_TOPIC_STATUS)
        else:
            logger.error(f"Failed to connect to MQTT, return code {rc}")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            if topic == MQTT_TOPIC_RESPONSE:
                command_id = payload.get("command_id")
                if command_id:
                    command_responses[command_id] = payload
            elif topic == MQTT_TOPIC_STATUS:
                pi_status["online"] = payload.get("status") == "online"
                pi_status["last_seen"] = time.time()
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def on_disconnect(self, client, userdata, rc):
        logger.info("Disconnected from MQTT Broker")

    def connect(self):
        try:
            self.client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT connection error: {e}")
            return False

    def publish_command(self, command, command_id):
        message = {
            "command_id": command_id,
            "command": command,
            "timestamp": time.time()
        }
        result = self.client.publish(MQTT_TOPIC_COMMAND, json.dumps(message))
        return result.rc == 0

# Initialize MQTT client
mqtt_client = MQTTClient()

def wait_for_response(command_id, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        if command_id in command_responses:
            resp = command_responses[command_id]
            del command_responses[command_id]
            return resp
        time.sleep(0.2)
    return {"status": "timeout", "error": "No response from Pi"}

# --- COMPREHENSIVE ADMIN DATABASE MANAGEMENT ENDPOINTS ---

@app.get("/admin/users")
def admin_get_all_users(request: Request):
    """Get all users (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC')
            users = [dict(row) for row in cursor.fetchall()]
        return {"users": users}
    except Exception as e:
        logger.error(f"Error getting users: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/users")
def admin_add_user(request: Request, user_data: dict):
    """Add new user (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # Build dynamic INSERT query
            columns = list(user_data.keys())
            placeholders = ['?' for _ in columns]
            values = list(user_data.values())
            
            query = f"""
                INSERT INTO users ({', '.join(columns)}) 
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(query, values)
            conn.commit()
            
            return {"success": True, "message": "User added successfully", "user_id": cursor.lastrowid}
    except Exception as e:
        logger.error(f"Error adding user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/admin/users/{user_id}")
def admin_update_user(user_id: int, request: Request, user_data: dict):
    """Update user (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # Build dynamic UPDATE query
            set_clauses = [f"{col} = ?" for col in user_data.keys()]
            values = list(user_data.values()) + [user_id]
            
            query = f"""
                UPDATE users 
                SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """
            
            cursor.execute(query, values)
            conn.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"success": True, "message": "User updated successfully"}
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: int, request: Request):
    """Delete user (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            # First delete related conversations
            cursor.execute('DELETE FROM conversations WHERE user_name = (SELECT name FROM users WHERE id = ?)', (user_id,))
            
            # Delete user profiles
            cursor.execute('DELETE FROM user_profiles WHERE user_name = (SELECT name FROM users WHERE id = ?)', (user_id,))
            
            # Delete conversation context
            cursor.execute('DELETE FROM conversation_context WHERE user_name = (SELECT name FROM users WHERE id = ?)', (user_id,))
            
            # Finally delete the user
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {"success": True, "message": "User deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ADMIN API ENDPOINTS ---

@app.get("/admin/api-keys")
def admin_get_api_keys(request: Request):
    """Get all API keys (admin function)"""
    verify_admin_api_key(request)
    try:
        keys = db.get_all_api_keys()
        if keys is None:
            return {"api_keys": [], "message": "No API keys found"}
        
        if isinstance(keys, dict):
            if "api_keys" in keys:
                return keys
            elif "keys" in keys:
                return {"api_keys": keys["keys"]}
            else:
                return {"api_keys": [keys]}
        elif isinstance(keys, list):
            return {"api_keys": keys}
        else:
            return {"api_keys": []}
    except Exception as e:
        logger.error(f"Error in admin_get_api_keys: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/admin/api-keys")
def admin_add_api_key(request: Request, service_name: str = Form(...), api_key: str = Form(...), 
                     description: Optional[str] = Form(None), expires_at: Optional[str] = Form(None)):
    """Add new API key (admin function)"""
    verify_admin_api_key(request)
    admin_user = request.headers.get("x-admin-user", "admin")
    try:
        db.add_api_key(service_name, api_key, description, admin_user, expires_at)
        return {"success": True, "message": f"API key for {service_name} added successfully"}
    except Exception as e:
        logger.error(f"Error adding API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/admin/api-keys/{service_name}")
def admin_update_api_key(service_name: str, request: Request, new_api_key: str = Form(...), 
                        reason: Optional[str] = Form(None)):
    """Update API key (admin function)"""
    verify_admin_api_key(request)
    admin_user = request.headers.get("x-admin-user", "admin")
    try:
        db.update_api_key(service_name, new_api_key, admin_user, reason)
        return {"success": True, "message": f"API key for {service_name} updated successfully"}
    except Exception as e:
        logger.error(f"Error updating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/api-keys/{service_name}")
def admin_deactivate_api_key(service_name: str, request: Request, reason: Optional[str] = Form(None)):
    """Deactivate API key (admin function)"""
    verify_admin_api_key(request)
    admin_user = request.headers.get("x-admin-user", "admin")
    try:
        db.deactivate_api_key(service_name, admin_user, reason)
        return {"success": True, "message": f"API key for {service_name} deactivated successfully"}
    except Exception as e:
        logger.error(f"Error deactivating API key: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/api-keys/usage")
def admin_get_api_key_usage_stats(request: Request, days: int = 30, service: Optional[str] = None):
    """Get API key usage statistics (admin function)"""
    verify_admin_api_key(request)
    try:
        stats = db.get_api_key_usage_stats(service_name=service, days=days)
        return stats
    except Exception as e:
        logger.error(f"Error getting usage stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/api-keys/logs")
def admin_get_api_key_logs(request: Request):
    """Get API key admin logs (admin function)"""
    verify_admin_api_key(request)
    try:
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''SELECT * FROM api_key_admin_log ORDER BY created_at DESC LIMIT 50''')
            logs = [dict(row) for row in cursor.fetchall()]
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Error getting admin logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/sync-history")
def admin_get_sync_history(request: Request):
    """Get sync history (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''SELECT * FROM admin_sync_log ORDER BY sync_timestamp DESC LIMIT 50''')
            logs = [dict(row) for row in cursor.fetchall()]
        return {"success": True, "sync_history": logs}
    except Exception as e:
        logger.error(f"Error getting sync history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- ROBOT CONTROL VIA MQTT ---

@app.post("/admin/robot/send-command")
def admin_send_robot_command(request: Request, command: str = Form(...), timeout: Optional[int] = Form(30)):
    """Send command to robot via MQTT (admin function)"""
    verify_admin_api_key(request)
    command_id = str(uuid.uuid4())
    if not mqtt_client.publish_command(command, command_id):
        raise HTTPException(status_code=500, detail="Failed to send MQTT message")
    return {"status": "sent", "command_id": command_id, "command": command}

@app.get("/admin/robot/command-response/{command_id}")
def admin_get_command_response(command_id: str, request: Request):
    """Get robot command response (admin function)"""
    verify_admin_api_key(request)
    if command_id in command_responses:
        response = command_responses[command_id]
        del command_responses[command_id]
        return response
    else:
        return {"status": "pending", "message": "Response not received yet"}

@app.get("/admin/robot/status")
def admin_get_robot_status(request: Request):
    """Get robot status (admin function)"""
    verify_admin_api_key(request)
    current_time = time.time()
    if pi_status["last_seen"] and (current_time - pi_status["last_seen"]) < 60:
        status = "online"
    else:
        status = "offline"
    return {"status": status, "last_seen": pi_status["last_seen"]}

# --- REMOTE DATABASE CONTROL ENDPOINTS ---

@app.get("/admin/pi/tables")
def admin_get_pi_tables(request: Request):
    """Get Pi database tables (admin function)"""
    verify_admin_api_key(request)
    command_id = str(uuid.uuid4())
    mqtt_client.publish_command("get_tables", command_id)
    resp = wait_for_response(command_id)
    return resp

@app.get("/admin/pi/table/{table_name}")
def admin_get_pi_table_data(table_name: str, request: Request):
    """Get Pi table data (admin function)"""
    verify_admin_api_key(request)
    command_id = str(uuid.uuid4())
    mqtt_client.client.publish(MQTT_TOPIC_COMMAND, json.dumps({
        "command_id": command_id,
        "command": "get_table_data",
        "table": table_name
    }))
    resp = wait_for_response(command_id)
    return resp

@app.post("/admin/pi/table/{table_name}/row")
def admin_insert_pi_table_row(table_name: str, request: Request, data: dict):
    """Insert row into Pi table (admin function)"""
    verify_admin_api_key(request)
    command_id = str(uuid.uuid4())
    mqtt_client.client.publish(MQTT_TOPIC_COMMAND, json.dumps({
        "command_id": command_id,
        "command": "insert_table_row",
        "table": table_name,
        "data": data
    }))
    resp = wait_for_response(command_id)
    return resp

@app.put("/admin/pi/table/{table_name}/row/{row_id}")
def admin_update_pi_table_row(table_name: str, row_id: int, request: Request, data: dict, id_column: str = "id"):
    """Update row in Pi table (admin function)"""
    verify_admin_api_key(request)
    command_id = str(uuid.uuid4())
    mqtt_client.client.publish(MQTT_TOPIC_COMMAND, json.dumps({
        "command_id": command_id,
        "command": "update_table_row",
        "table": table_name,
        "row_id": row_id,
        "data": data,
        "id_column": id_column
    }))
    resp = wait_for_response(command_id)
    return resp

@app.delete("/admin/pi/table/{table_name}/row/{row_id}")
def admin_delete_pi_table_row(table_name: str, row_id: int, request: Request, id_column: str = "id"):
    """Delete row from Pi table (admin function)"""
    verify_admin_api_key(request)
    command_id = str(uuid.uuid4())
    mqtt_client.client.publish(MQTT_TOPIC_COMMAND, json.dumps({
        "command_id": command_id,
        "command": "delete_table_row",
        "table": table_name,
        "row_id": row_id,
        "id_column": id_column
    }))
    resp = wait_for_response(command_id)
    return resp

# --- ADMIN DASHBOARD DATA ---

@app.get("/admin/dashboard")
def admin_get_dashboard_data(request: Request):
    """Get admin dashboard data (admin function)"""
    verify_admin_api_key(request)
    try:
        # Get API key stats
        api_key_stats = db.get_api_key_usage_stats(days=7)
        
        # Get robot status
        current_time = time.time()
        robot_online = pi_status["last_seen"] and (current_time - pi_status["last_seen"]) < 60
        
        # Get recent conversations count
        import sqlite3
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM conversations WHERE date(timestamp) = date('now')")
            today_conversations = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
        
        return {
            "api_key_stats": api_key_stats,
            "robot_status": {
                "online": robot_online,
                "last_seen": pi_status["last_seen"]
            },
            "today_conversations": today_conversations,
            "total_users": total_users,
            "timestamp": current_time
        }
    except Exception as e:
        logger.error(f"Error getting dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Initialize MQTT on startup ---
@app.on_event("startup")
def startup_event():
    """Initialize MQTT connection on startup"""
    try:
        mqtt_client.connect()
        logger.info("MQTT client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize MQTT client: {e}")

@app.get("/admin/conversations")
def admin_get_all_conversations(request: Request, limit: int = 100, offset: int = 0):
    """Get all conversations with pagination (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total count
            cursor.execute('SELECT COUNT(*) FROM conversations')
            total = cursor.fetchone()[0]
            
            # Get conversations with pagination
            cursor.execute('''
                SELECT * FROM conversations 
                ORDER BY timestamp DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            conversations = [dict(row) for row in cursor.fetchall()]
            
        return {"conversations": conversations, "total": total, "limit": limit, "offset": offset}
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/admin/conversations/{conversation_id}")
def admin_delete_conversation(conversation_id: int, request: Request):
    """Delete conversation (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
            conn.commit()
            
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Conversation not found")
            
            return {"success": True, "message": "Conversation deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/database/stats")
def admin_get_database_stats(request: Request):
    """Get database statistics (admin function)"""
    verify_admin_api_key(request)
    try:
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.cursor()
            
            stats = {}
            
            # Count records in each table
            tables = ['users', 'conversations', 'user_profiles', 'unknown_users', 'api_keys', 'conversation_context']
            for table in tables:
                cursor.execute(f'SELECT COUNT(*) FROM {table}')
                stats[f'{table}_count'] = cursor.fetchone()[0]
            
            # Recent activity
            cursor.execute('SELECT COUNT(*) FROM conversations WHERE timestamp >= date("now", "-7 days")')
            stats['conversations_last_7_days'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE created_at >= date("now", "-30 days")')
            stats['new_users_last_30_days'] = cursor.fetchone()[0]
            
            # Database file size
            import os
            if os.path.exists(db.db_path):
                stats['database_size_bytes'] = os.path.getsize(db.db_path)
            else:
                stats['database_size_bytes'] = 0
                
        return {"stats": stats}
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    try:
        if mqtt_client.client:
            mqtt_client.client.loop_stop()
            mqtt_client.client.disconnect()
        logger.info("MQTT client disconnected")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)

