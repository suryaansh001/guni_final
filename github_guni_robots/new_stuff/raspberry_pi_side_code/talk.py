#!/usr/bin/env python3
"""
Enhanced Robot Face Expression System for Raspberry Pi Display with Voice Assistant Integration
A comprehensive cute robot face with emotional expressions, creative animations, and enhanced visual effects.
Features tears, heartbreak animations, blinking, breathing, voice interaction, and more dynamic expressions.
"""

import json
import math
import time
import random
import sys
import os
import threading
import requests
import tempfile
import pyaudio
import wave
import argparse
import logging
import urllib.parse
import struct
from typing import Dict, List, Tuple, Optional, Any

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError as e:
    print(f"Required libraries not installed: {e}")
    print("Install with: pip install pygame PyOpenGL PyOpenGL_accelerate requests pyaudio")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

expp = "cute_neutral"

class VoiceAssistantClient:
    """Voice Assistant Client for API Communication"""
    
    def __init__(self, api_url="http://localhost:8001", user_name="test_user"):
        self.api_url = api_url
        self.user_name = user_name
        
        # Audio Configuration
        self.audio_config = {
            'chunk': 1024,
            'format': pyaudio.paInt16,
            'channels': 1,
            'rate': 16000,
            'record_seconds': 10
        }
        
        # State tracking
        self.is_recording = False
        self.is_processing = False
        self.is_speaking = False
        self.api_status = "Disconnected"
        self.last_user_input = ""
        self.last_ai_response = ""
        
        # Test connection
        self.test_api_connection()
    
    def store_conversation(self, user_input, ai_response, language_used='english'):
        """Store conversation in the server database"""
        try:
            if not user_input or not ai_response:
                logger.warning("Skipping conversation storage - missing user input or AI response")
                return False
            
            logger.info(f"Storing conversation for user: {self.user_name}")
            logger.info(f"User input: {user_input[:100]}...")
            logger.info(f"AI response: {ai_response[:100]}...")
            
            data = {
                'user_name': self.user_name,
                'user_input': user_input,
                'ai_response': ai_response,
                'language_used': language_used
            }
            
            response = requests.post(
                f"{self.api_url}/conversation",
                data=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'added':
                    logger.info("Conversation stored successfully in server database")
                    return True
                else:
                    logger.warning(f"Failed to store conversation: {result}")
                    return False
            else:
                logger.error(f"Failed to store conversation: HTTP {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("Timeout while storing conversation")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Connection error while storing conversation")
            return False
        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            return False
    
    def test_api_connection(self):
        """Test connection to the voice assistant API"""
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
    
    def send_audio_to_api(self, audio_path):
        """Send audio to the API and get response"""
        try:
            logger.info(f"Sending audio to API: {self.api_url}")
            
            with open(audio_path, 'rb') as audio_file:
                files = {
                    'audio': ('audio.wav', audio_file, 'audio/wav')
                }
                data = {
                    'user_name': self.user_name
                }
                
                response = requests.post(
                    f"{self.api_url}/process_audio",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            # Cleanup temp file
            try:
                os.unlink(audio_path)
            except:
                pass
            
            logger.info(f"API Response Status: {response.status_code}")
            logger.info(f"API Response Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                # The new API returns audio content directly with headers
                import urllib.parse
                
                robot_expression = response.headers.get('X-Robot-Expression', 'cute_neutral')
                encoded_text_response = response.headers.get('X-LLM-Text', 'I am here to help!')
                language_used = response.headers.get('X-Language-Used', 'english')
                audio_format = response.headers.get('X-Audio-Format', 'mp3')
                
                # Decode the URL-encoded text response
                try:
                    text_response = urllib.parse.unquote(encoded_text_response)
                except Exception as decode_error:
                    logger.warning(f"Failed to decode text response: {decode_error}")
                    text_response = encoded_text_response  # Use as-is if decoding fails
                
                # Save audio content to temp file with correct extension
                file_extension = '.wav' if audio_format == 'wav' else '.mp3'
                temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
                temp_audio.write(response.content)
                temp_audio.close()
                
                result = {
                    'robot_expression': robot_expression,
                    'text_response': text_response,
                    'language_used': language_used,
                    'audio_file': temp_audio.name,
                    'audio_format': audio_format,
                    'user_input': f"Processed via {self.user_name}"
                }
                
                logger.info(f"API Response parsed: {result}")
                return result
            else:
                logger.error(f"API Error: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to API")
            return None
        except Exception as e:
            logger.error(f"API communication error: {e}")
            return None
    
    def play_audio_response(self, response_data):
        """Play audio response from API"""
        if not response_data:
            logger.error("No response data to play audio from")
            return
        
        if 'audio_file' in response_data and response_data['audio_file']:
            try:
                audio_file_path = response_data['audio_file']
                audio_format = response_data.get('audio_format', 'mp3')
                
                logger.info(f"Playing {audio_format} audio file: {audio_file_path}")
                
                # Initialize pygame mixer with appropriate settings based on format
                try:
                    pygame.mixer.quit()  # Ensure clean state
                except:
                    pass
                
                # Different settings for WAV vs MP3
                if audio_format == 'wav':
                    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
                else:
                    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
                
                # Load and play audio
                try:
                    pygame.mixer.music.load(audio_file_path)
                    pygame.mixer.music.play()
                    
                    logger.info(f"Audio playback started ({audio_format} format)")
                    
                    # Wait for playback to complete
                    while pygame.mixer.music.get_busy():
                        pygame.time.Clock().tick(10)
                        if not self.is_speaking:
                            pygame.mixer.music.stop()
                            break
                    
                    logger.info("Audio playback completed")
                except pygame.error as e:
                    logger.error(f"Pygame audio error: {e}")
                    
                    # Alternative playback method for WAV files
                    if audio_format == 'wav':
                        try:
                            logger.info("Trying alternative WAV playback method")
                            sound = pygame.mixer.Sound(audio_file_path)
                            sound.play()
                            
                            # Wait for sound to finish
                            while pygame.mixer.get_busy():
                                pygame.time.Clock().tick(10)
                                if not self.is_speaking:
                                    pygame.mixer.stop()
                                    break
                            
                            logger.info("Alternative WAV playback completed")
                        except Exception as alt_error:
                            logger.error(f"Alternative WAV playback failed: {alt_error}")
                
                # Cleanup temp file
                try:
                    os.unlink(audio_file_path)
                except:
                    pass
                    
            except Exception as e:
                logger.error(f"Audio playback error: {e}")
        else:
            logger.warning("No audio_file in response data")
            # If there's text response but no audio, at least log it
            if 'text_response' in response_data:
                logger.info(f"Text response (no audio): {response_data['text_response']}")

class AnimationEngine:
    """Handles complex animations like tears, blinking, breathing effects"""

    def __init__(self):
        self.start_time = time.time()
        self.tears = []
        self.hearts = []
        self.sparkles = []
        self.last_blink = 0
        self.blink_duration = 0.15
        self.is_blinking = False
        self.breathing_offset = 0
        
        # Talking animation
        self.is_talking = False
        self.talk_start_time = 0
        self.talk_phase = 0
        self.talk_speed = 8  # Speed of mouth movement

    def update(self, delta_time: float):
        """Update all animations"""
        current_time = time.time()
        
        # Update tears
        self.update_tears(delta_time)
        
        # Update floating hearts
        self.update_floating_hearts(delta_time)
        
        # Update sparkles
        self.update_sparkles(delta_time)
        
        # Handle automatic blinking
        self.update_blinking(current_time)
        
        # Update breathing animation
        self.update_breathing(current_time)

    def update_tears(self, delta_time: float):
        """Update falling tears animation"""
        # Remove tears that have fallen off screen
        self.tears = [tear for tear in self.tears if tear['y'] > -50]
        
        # Update existing tears
        for tear in self.tears:
            tear['y'] -= tear['speed'] * delta_time
            tear['x'] += tear['sway'] * math.sin(tear['y'] * 0.01) * delta_time

    def add_tear(self, x: float, y: float):
        """Add a new tear drop with reduced quantity and round shape"""
        # Only add tear if we don't have too many (reduced density)
        if len(self.tears) < 3:  # Maximum 3 tears at a time
            tear = {
                'x': x + random.uniform(-5, 5),  # Less spread
                'y': y,
                'speed': random.uniform(50, 80),  # Moderate speed
                'sway': random.uniform(-10, 10),  # Less sway
                'size': random.uniform(6, 10),  # Smaller round tears
                'alpha': random.uniform(0.8, 1.0)  # Good visibility
            }
            self.tears.append(tear)

    def update_floating_hearts(self, delta_time: float):
        """Update floating hearts for love expressions"""
        # Remove old hearts
        self.hearts = [heart for heart in self.hearts if heart['life'] > 0]
        
        # Update existing hearts
        for heart in self.hearts:
            heart['y'] += heart['speed'] * delta_time
            heart['x'] += heart['drift'] * delta_time
            heart['life'] -= delta_time
            heart['rotation'] += heart['rot_speed'] * delta_time
            heart['size'] = heart['base_size'] * (1.0 + 0.2 * math.sin(heart['pulse'] * heart['life']))

    def add_floating_heart(self, x: float, y: float):
        """Add a floating heart"""
        heart = {
            'x': x + random.uniform(-20, 20),
            'y': y,
            'speed': random.uniform(30, 60),
            'drift': random.uniform(-20, 20),
            'life': random.uniform(2, 4),
            'base_size': random.uniform(8, 15),
            'size': 10,
            'rotation': 0,
            'rot_speed': random.uniform(-2, 2),
            'pulse': random.uniform(3, 6),
            'color': [random.uniform(0.8, 1.0), random.uniform(0.3, 0.6), random.uniform(0.3, 0.6)]
        }
        self.hearts.append(heart)

    def update_sparkles(self, delta_time: float):
        """Update twinkling sparkles"""
        # Remove old sparkles
        self.sparkles = [sparkle for sparkle in self.sparkles if sparkle['life'] > 0]
        
        # Update existing sparkles
        for sparkle in self.sparkles:
            sparkle['life'] -= delta_time
            sparkle['rotation'] += sparkle['rot_speed'] * delta_time
            sparkle['alpha'] = sparkle['life'] / sparkle['max_life']

    def add_sparkle(self, x: float, y: float):
        """Add a twinkling sparkle"""
        sparkle = {
            'x': x + random.uniform(-30, 30),
            'y': y + random.uniform(-30, 30),
            'life': random.uniform(1, 2),
            'max_life': 2,
            'size': random.uniform(4, 8),
            'rotation': random.uniform(0, 2 * math.pi),
            'rot_speed': random.uniform(-5, 5),
            'alpha': 1.0,
            'color': [random.uniform(0.8, 1.0), random.uniform(0.8, 1.0), random.uniform(0.3, 1.0)]
        }
        self.sparkles.append(sparkle)

    def update_blinking(self, current_time: float):
        """Handle automatic blinking"""
        if self.is_blinking:
            if current_time - self.last_blink > self.blink_duration:
                self.is_blinking = False
        else:
            # Random blink every 2-5 seconds
            if current_time - self.last_blink > random.uniform(2, 5):
                self.start_blink(current_time)

    def start_blink(self, current_time: float):
        """Start a blink animation"""
        self.is_blinking = True
        self.last_blink = current_time

    def get_blink_factor(self, current_time: float) -> float:
        """Get current blink closure factor (0 = open, 1 = closed)"""
        if not self.is_blinking:
            return 0.0
        
        elapsed = current_time - self.last_blink
        progress = elapsed / self.blink_duration
        
        if progress >= 1.0:
            return 0.0
        
        # Smooth blink curve
        return math.sin(progress * math.pi)

    def update_breathing(self, current_time: float):
        """Update breathing animation"""
        self.breathing_offset = math.sin(current_time * 2) * 3

    def start_talking(self):
        """Start talking animation"""
        self.is_talking = True
        self.talk_start_time = time.time()

    def stop_talking(self):
        """Stop talking animation"""
        self.is_talking = False

    def get_talk_mouth_offset(self, current_time: float) -> float:
        """Get mouth radius variation for talking animation"""
        if not self.is_talking:
            return 0.0
        
        elapsed = current_time - self.talk_start_time
        # Create varied mouth movement for natural talking - radius variation
        base_variation = math.sin(elapsed * self.talk_speed) * 0.8
        secondary_variation = math.sin(elapsed * self.talk_speed * 1.5) * 0.4
        quick_variation = math.sin(elapsed * self.talk_speed * 2.8) * 0.3
        
        # Combine variations and ensure it's always positive for radius
        total_variation = base_variation + secondary_variation + quick_variation
        # Scale and offset to make radius variation between 0.3 and 1.5
        return 0.3 + (total_variation + 1.0) * 0.6


class VibrationEngine:
    """Enhanced vibration effects and screen shake animations"""

    def __init__(self, vibration_patterns: Dict = None):
        self.current_pattern = "none"
        self.start_time = 0
        self.patterns = vibration_patterns or {
            "none": {"intensity": 0, "frequency": 0},
            "gentle": {"intensity": 2, "frequency": 10},
            "medium": {"intensity": 5, "frequency": 15},
            "strong": {"intensity": 8, "frequency": 20},
            "excited": {"intensity": 3, "frequency": 25},
            "nervous": {"intensity": 1, "frequency": 30},
            "heartbreak": {"intensity": 12, "frequency": 8},
            "rage": {"intensity": 15, "frequency": 35},
            "giggle": {"intensity": 4, "frequency": 12}
        }

    def start_vibration(self, pattern: str):
        """Start a vibration pattern"""
        self.current_pattern = pattern
        self.start_time = time.time()

    def calculate_offset(self, current_time: float) -> Tuple[float, float]:
        """Calculate enhanced vibration offset for current time"""
        if self.current_pattern == "none":
            return 0.0, 0.0

        pattern_data = self.patterns.get(self.current_pattern, self.patterns["none"])
        if pattern_data["intensity"] == 0:
            return 0.0, 0.0

        elapsed = current_time - self.start_time
        intensity = pattern_data["intensity"]
        frequency = pattern_data["frequency"]

        if self.current_pattern == "heartbreak":
            # Heartbreak has a distinctive breaking pattern
            x_offset = intensity * math.sin(elapsed * frequency) * (1 + 0.5 * math.sin(elapsed * frequency * 3))
            y_offset = intensity * math.cos(elapsed * frequency * 0.7) * (1 + 0.3 * math.cos(elapsed * frequency * 5))
        elif self.current_pattern == "giggle":
            # Giggle has a bouncy pattern
            x_offset = intensity * math.sin(elapsed * frequency) * 0.5
            y_offset = intensity * abs(math.sin(elapsed * frequency * 2))
        else:
            # Standard vibration patterns
            x_offset = intensity * math.sin(elapsed * frequency) * random.uniform(0.8, 1.2)
            y_offset = intensity * math.cos(elapsed * frequency * 1.3) * random.uniform(0.8, 1.2)

        return x_offset, y_offset


class ExpressionLoader:
    """Enhanced expression loader with new emotional states"""

    def __init__(self, config_file: str = "enhanced_expressions.json"):
        self.config_file = config_file
        self.expressions = {}
        self.parameter_maps = {}
        self.settings = {}
        self.load_expressions()

    def load_expressions(self) -> bool:
        """Load expressions from JSON file with enhanced defaults"""
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
            
            self.parameter_maps = data.get("parameter_maps", {})
            self.expressions = data.get("expressions", {})
            self.settings = data.get("settings", {})
            
            print(f"Loaded {len(self.expressions)} expressions from {self.config_file}")
            print(f"Available expressions: {list(self.expressions.keys())}")
            
            if not self.validate_configuration():
                print("Configuration validation failed, using defaults")
                self.load_default_configuration()
                return False
                
            print(f"Successfully loaded configuration from {self.config_file}")
            return True
        except FileNotFoundError:
            print(f"Configuration file {self.config_file} not found, using defaults")
            self.load_default_configuration()
            return False
        except json.JSONDecodeError as e:
            print(f"JSON decode error in {self.config_file}: {e}, using defaults")
            self.load_default_configuration()
            return False
        except Exception as e:
            print(f"Error loading configuration: {e}, using defaults")
            self.load_default_configuration()
            return False

    def validate_configuration(self) -> bool:
        """Validate the loaded configuration"""
        required_maps = ["eyebrow_positions", "eye_sizes", "eye_shapes", "mouth_shapes"]
        missing_maps = [req_map for req_map in required_maps if req_map not in self.parameter_maps]
        
        if missing_maps:
            print(f"Missing parameter maps: {missing_maps}")
            return False
            
        if not self.expressions:
            print("No expressions found in configuration")
            return False
            
        print(f"Configuration validated successfully. Found {len(self.expressions)} expressions.")
        return True

    def load_default_configuration(self):
        """Load basic fallback configuration if JSON fails"""
        print("Loading minimal fallback configuration...")
        
        # Only override settings if they're empty
        if not self.settings:
            self.settings = {
                "display": {"width": 480, "height": 320, "fps": 60},
                "colors": {
                    "face": [0.9, 0.9, 0.9],
                    "pupil": [0.0, 0.0, 0.0],
                    "eyebrow": [0.7, 0.7, 0.7],
                    "tear": [0.7, 0.9, 1.0, 0.8]
                }
            }
        
        # Only add missing parameter maps
        if not self.parameter_maps:
            self.parameter_maps = {}
            
        default_parameter_maps = {
            "eyebrow_positions": {
                "very_low": -30, "low": -15, "normal": 0,
                "raised": 15, "high": 30, "very_high": 45,
                "angry": -25, "worried": 10
            },
            "eye_sizes": {
                "tiny": 0.5, "small": 0.7, "normal": 1.0,
                "large": 1.3, "huge": 1.6, "cute_default": 1.4,
                "sleepy": 0.3, "wide_awake": 1.8
            },
            "eye_shapes": {
                "circle": "circle", "oval": "oval", "half_closed": "horizontal_oval",
                "closed": "line", "crescent_happy": "crescent_up", "crescent_sad": "crescent_down",
                "wide": "wide_circle", "squinted": "squinted_oval", "heart": "heart_shape", 
                "star": "star_shape", "x_shaped": "x_eyes", "spiral": "spiral_eyes",
                "dollar": "dollar_eyes", "sleepy": "closed"
            },
            "mouth_shapes": {
                "neutral": "horizontal_line", "small_smile": "slight_curve_up", "big_smile": "wide_curve_up",
                "small_frown": "slight_curve_down", "big_frown": "wide_curve_down", "open_small": "small_oval",
                "open_wide": "large_oval", "open_round": "circle", "cute_smile": "gentle_curve_up",
                "pout": "small_pout", "kiss": "small_pucker", "wavy": "wavy_line",
                "zigzag": "zigzag_line", "heart": "heart_mouth", "gasp": "shocked_oval",
                "talking": "circular_varying"
            },
            "vibration_patterns": {
                "none": {"intensity": 0, "frequency": 0},
                "gentle": {"intensity": 2, "frequency": 10},
                "medium": {"intensity": 5, "frequency": 15},
                "strong": {"intensity": 8, "frequency": 20},
                "excited": {"intensity": 3, "frequency": 25},
                "heartbreak": {"intensity": 12, "frequency": 8},
                "rage": {"intensity": 15, "frequency": 35}
            }
        }
        
        # Add missing parameter maps
        for key, value in default_parameter_maps.items():
            if key not in self.parameter_maps:
                self.parameter_maps[key] = value

        # Only add minimal expressions if none were loaded from JSON
        if not self.expressions:
            self.expressions = {
                "cute_neutral": {
                    "eyes": {"shape": "circle", "size": "cute_default"},
                    "pupils": {"position": "center", "size": "normal"},
                    "eyebrows": {"position": "normal"},
                    "mouth": {"shape": "cute_smile"},
                    "background": {"color": "none", "effect": "none"},
                    "vibration": {"pattern": "none"},
                    "special_effects": []
                },
                "happy": {
                    "eyes": {"shape": "crescent_happy", "size": "cute_default"},
                    "pupils": {"position": "center", "size": "normal"},
                    "eyebrows": {"position": "raised"},
                    "mouth": {"shape": "big_smile"},
                    "background": {"color": "yellow", "effect": "sparkles"},
                    "vibration": {"pattern": "gentle"},
                    "special_effects": ["sparkles"]
                },
                "sad": {
                    "eyes": {"shape": "crescent_sad", "size": "large"},
                    "pupils": {"position": "down", "size": "large"},
                    "eyebrows": {"position": "low"},
                    "mouth": {"shape": "big_frown"},
                    "background": {"color": "blue", "effect": "rain"},
                    "vibration": {"pattern": "gentle"},
                    "special_effects": ["tears"]
                },
                "talking": {
                    "eyes": {"shape": "circle", "size": "cute_default"},
                    "pupils": {"position": "center", "size": "normal"},
                    "eyebrows": {"position": "normal"},
                    "mouth": {"shape": "talking"},
                    "background": {"color": "none", "effect": "none"},
                    "vibration": {"pattern": "none"},
                    "special_effects": []
                }
            }

    def get_expression(self, expression_name: str) -> Dict:
        """Get expression data with fallback"""
        return self.expressions.get(expression_name, self.expressions.get("cute_neutral", {}))

    def get_all_expressions(self) -> Dict[str, str]:
        """Get all available expressions with descriptions for API integration"""
        expression_descriptions = {}
        
        for expression_name in self.expressions.keys():
            # Generate a description based on the expression name and its characteristics
            if "happy" in expression_name or "joy" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - happiness, joy, contentment"
            elif "love" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - affection, adoration, romantic feelings"
            elif "excited" in expression_name or "overjoyed" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - extreme happiness, excitement, enthusiasm"
            elif "sad" in expression_name or "crying" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - sadness, disappointment, melancholy"
            elif "angry" in expression_name or "furious" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - anger, frustration, rage"
            elif "surprised" in expression_name or "shocked" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - surprise, amazement, shock"
            elif "sleepy" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - tiredness, drowsiness, low energy"
            elif "confused" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - confusion, bewilderment, uncertainty"
            elif "neutral" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - default, calm, balanced"
            elif "talking" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - speaking, communicating"
            elif "playful" in expression_name or "mischievous" in expression_name:
                description = f"{expression_name.replace('_', ' ').title()} expression - playfulness, teasing, fun"
            else:
                description = f"{expression_name.replace('_', ' ').title()} expression"
                
            expression_descriptions[expression_name] = description
            
        return expression_descriptions

class ExpressionEngine:
    """Enhanced expression engine with animation timing"""

    def __init__(self, loader: ExpressionLoader):
        self.loader = loader
        self.current_expression = "cute_neutral"
        self.target_expression = "cute_neutral"
        self.transition_progress = 1.0
        self.transition_speed = 2.0
        self.animation_engine = AnimationEngine()
        self.last_expression_change = 0

    def set_expression(self, expression_name: str, transition_speed: float = 2.0):
        """Set target expression with enhanced transitions"""
        if expression_name != self.target_expression:
            self.current_expression = self.target_expression
            self.target_expression = expression_name
            self.transition_progress = 0.0
            self.transition_speed = transition_speed
            self.last_expression_change = time.time()
            
            # Trigger special effects based on expression
            self.trigger_expression_effects(expression_name)

    def trigger_expression_effects(self, expression_name: str):
        """Trigger special visual effects when expression changes"""
        expression_data = self.loader.get_expression(expression_name)
        effects = expression_data.get("special_effects", [])
        
        for effect in effects:
            if effect == "tears" and expression_name in ["sad", "heartbroken", "crying"]:
                # Add larger initial tears for sad expressions
                for _ in range(4):  # More tears
                    self.animation_engine.add_tear(240 - 60 + random.uniform(-15, 15), 220)
                    self.animation_engine.add_tear(240 + 60 + random.uniform(-15, 15), 220)
            
            elif effect == "floating_hearts" and expression_name in ["love", "in_love"]:
                # Add floating hearts
                for _ in range(3):  # More hearts for love
                    self.animation_engine.add_floating_heart(240, 200)
            
            elif effect == "sparkles" and expression_name in ["happy", "excited", "overjoyed", "playful"]:
                # Add sparkles around face for happy expressions
                for _ in range(6):  # More sparkles for happiness
                    self.animation_engine.add_sparkle(240, 200)

    def update(self, delta_time: float):
        """Enhanced update with continuous effects"""
        if self.transition_progress < 1.0:
            self.transition_progress = min(1.0, self.transition_progress + delta_time * self.transition_speed)

        # Update animations
        self.animation_engine.update(delta_time)
        
        # Continuously add effects for certain expressions
        current_time = time.time()
        expression_data = self.loader.get_expression(self.target_expression)
        effects = expression_data.get("special_effects", [])
        
        # Add continuous tears for sad expressions - LARGER tears
        if "tears" in effects and random.random() < 0.03:  # Increased chance
            self.animation_engine.add_tear(240 - 60 + random.uniform(-20, 20), 230)
            if random.random() < 0.6:  # More frequent both eyes
                self.animation_engine.add_tear(240 + 60 + random.uniform(-20, 20), 230)
        
        # Add continuous hearts for love - more frequent
        if "floating_hearts" in effects and random.random() < 0.02:  # Increased chance
            self.animation_engine.add_floating_heart(240 + random.uniform(-100, 100), 160)
        
        # Add continuous sparkles for excitement - more frequent for happy expressions
        if "sparkles" in effects and random.random() < 0.04:  # Increased chance
            self.animation_engine.add_sparkle(240 + random.uniform(-120, 120), 200 + random.uniform(-80, 80))

    def calculate_expression_data(self) -> Dict:
        """Calculate current expression data with enhanced transitions"""
        if self.transition_progress >= 1.0:
            return self.loader.get_expression(self.target_expression)
        else:
            current_data = self.loader.get_expression(self.current_expression)
            target_data = self.loader.get_expression(self.target_expression)
            return self.blend_expressions(current_data, target_data, self.transition_progress)

    def blend_expressions(self, expr1: Dict, expr2: Dict, blend_factor: float) -> Dict:
        """Enhanced expression blending"""
        return expr2.copy()  # Simplified for now


class EnhancedRobotFace:
    """Enhanced robot face renderer with creative visual effects"""

    def __init__(self, width: int = 480, height: int = 320, settings: Dict = None):
        self.width = width
        self.height = height
        self.animation_time = 0.0
        
        # Enhanced proportions - LARGER FACE
        self.eye_base_size = min(width, height) * 0.20  # Increased from 0.12
        self.eye_separation = width * 0.35  # Increased from 0.25
        self.mouth_y_offset = height * 0.20  # Increased from 0.15
        
        # Enhanced colors from settings or defaults
        colors = settings.get("colors", {}) if settings else {}
        self.face_color = tuple(colors.get("face", [0.9, 0.9, 0.9]))
        self.pupil_color = tuple(colors.get("pupil", [0.0, 0.0, 0.0]))
        self.eyebrow_color = tuple(colors.get("eyebrow", [0.7, 0.7, 0.7]))
        self.tear_color = tuple(colors.get("tear", [0.7, 0.9, 1.0, 0.8]))

    def initialize_opengl(self):
        """Initialize enhanced OpenGL settings with centered coordinates"""
        glClearColor(0.1, 0.1, 0.1, 1.0)  # Dark background
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glEnable(GL_POINT_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)
        glHint(GL_POINT_SMOOTH_HINT, GL_NICEST)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glOrtho(-2.5, 2.5, -2.0, 2.0, -1.0, 1.0)  # Center coordinate system
        glMatrixMode(GL_MODELVIEW)

    def draw_circle(self, x: float, y: float, radius: float, filled: bool = True, segments: int = 32):
        """Draw enhanced circle with smooth edges"""
        if filled:
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(x, y)
        else:
            glBegin(GL_LINE_LOOP)
        
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
        glEnd()

    def draw_heart_shape(self, x: float, y: float, size: float, rotation: float = 0):
        """Draw complete, full heart shape"""
        glPushMatrix()
        glTranslatef(x, y, 0)
        glRotatef(math.degrees(rotation), 0, 0, 1)
        
        # Draw filled heart using parametric heart equation
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0, 0)  # Center point
        
        # Create complete heart shape
        segments = 100  # More segments for smoother heart
        for i in range(segments + 1):
            t = i / segments * 2 * math.pi
            
            # Parametric heart equation for complete, filled heart
            heart_x = size * 0.5 * 16 * math.sin(t)**3 / 16
            heart_y = size * 0.5 * (13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t)) / 16
            
            # Keep the heart pointing upward (normal orientation)
            glVertex2f(heart_x, heart_y)
        
        glEnd()
        glPopMatrix()

    def draw_broken_heart(self, x: float, y: float, size: float, break_offset: float = 0):
        """Draw a larger broken heart with jagged crack"""
        # Make broken heart larger for better visibility
        large_size = size * 1.5  # 50% larger
        
        # Left half
        glPushMatrix()
        glTranslatef(x - break_offset, y, 0)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0, -large_size * 0.5)
        
        segments = 16
        for i in range(segments + 1):
            t = i / segments * math.pi
            hx = -large_size * 0.3 + large_size * 0.3 * math.cos(t)
            hy = large_size * 0.2 + large_size * 0.3 * math.sin(t)
            glVertex2f(hx, hy)
        
        # Jagged break line - more pronounced
        for i in range(7):  # More jagged pieces
            jx = i * 3 - 9
            jy = -large_size * 0.3 + i * large_size * 0.1 + random.uniform(-5, 5)
            glVertex2f(jx, jy)
        
        glEnd()
        glPopMatrix()
        
        # Right half
        glPushMatrix()
        glTranslatef(x + break_offset, y, 0)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0, -large_size * 0.5)
        
        for i in range(segments + 1):
            t = i / segments * math.pi + math.pi
            hx = large_size * 0.3 + large_size * 0.3 * math.cos(t)
            hy = large_size * 0.2 + large_size * 0.3 * math.sin(t)
            glVertex2f(hx, hy)
        
        # Jagged break line - more pronounced
        for i in range(7):  # More jagged pieces
            jx = -i * 3 + 9
            jy = -large_size * 0.3 + i * large_size * 0.1 + random.uniform(-5, 5)
            glVertex2f(jx, jy)
        
        glEnd()
        glPopMatrix()

    def draw_enhanced_eyes(self, expression_data: Dict, vibration_offset: Tuple[float, float], animation_engine):
        """Draw enhanced eyes with special shapes, blinking, and eyelashes"""
        eyes_data = expression_data.get("eyes", {})
        pupils_data = expression_data.get("pupils", {})
        
        eye_shape = eyes_data.get("shape", "circle")
        eye_size = eyes_data.get("size", "cute_default")
        
        # Get size multiplier based on expression
        if eye_size == "huge":
            size_multiplier = 2.0
        elif eye_size == "large":
            size_multiplier = 1.6
        elif eye_size == "sleepy":
            size_multiplier = 0.8
        else:
            size_multiplier = 1.4
            
        eye_radius = 0.35 * size_multiplier  # Increased from 0.25 for larger face
        
        # Add breathing effect
        breathing_scale = 1.0 + animation_engine.breathing_offset * 0.01
        eye_radius *= breathing_scale
        
        # Use centered coordinates for eyes
        eye_separation = 0.8  # Increased from 0.6 for larger face
        left_eye_x = -eye_separation/2 + vibration_offset[0]/100
        right_eye_x = eye_separation/2 + vibration_offset[0]/100
        eye_y = 0.3 + vibration_offset[1]/100 + animation_engine.breathing_offset/100
        
        # Get blink factor
        blink_factor = animation_engine.get_blink_factor(time.time())
        
        glColor3f(*self.face_color)
        
        if eye_shape == "heart":
            glColor3f(1.0, 0.3, 0.5)  # Proper pink color for hearts
            # Make hearts larger and complete for love expressions
            heart_size = eye_radius * 1.5
            self.draw_heart_shape(left_eye_x, eye_y, heart_size)
            self.draw_heart_shape(right_eye_x, eye_y, heart_size)
        elif eye_shape == "star":
            glColor3f(1.0, 1.0, 0.3)  # Bright yellow for excitement
            # Add rotation for overjoyed/excited expressions
            star_rotation = time.time() * 180  # Rotating stars
            self.draw_star(left_eye_x, eye_y, eye_radius, star_rotation)
            self.draw_star(right_eye_x, eye_y, eye_radius, star_rotation)
        elif eye_shape == "x_eyes":
            glColor3f(1.0, 0.2, 0.2)  # Red for dizzy/knocked out
            self.draw_x_eyes(left_eye_x, eye_y, eye_radius)
            self.draw_x_eyes(right_eye_x, eye_y, eye_radius)
        elif eye_shape == "spiral":
            glColor3f(0.7, 0.7, 1.0)  # Light blue for confusion
            self.draw_spiral(left_eye_x, eye_y, eye_radius)
            self.draw_spiral(right_eye_x, eye_y, eye_radius)
        elif eye_shape == "crescent_happy":
            # Happy expressions - keep eyes visible like cute_neutral but add crescents
            glColor3f(*self.face_color)
            # Draw normal eyes first for happy expressions
            self.draw_circle(left_eye_x, eye_y, eye_radius)
            self.draw_circle(right_eye_x, eye_y, eye_radius)
            # Add pupils for happy eyes
            if blink_factor < 0.7:
                self.draw_pupils(left_eye_x, right_eye_x, eye_y, eye_radius, pupils_data, blink_factor)
        elif eye_shape == "crescent_sad":
            # Sad crescent eyes (downward curves)
            glColor3f(*self.face_color)
            self.draw_sad_crescents(left_eye_x, eye_y, eye_radius)
            self.draw_sad_crescents(right_eye_x, eye_y, eye_radius)
        elif eye_shape == "closed":
            # Closed eyes for sleep
            glColor3f(*self.face_color)
            self.draw_closed_eyes(left_eye_x, eye_y, eye_radius)
            self.draw_closed_eyes(right_eye_x, eye_y, eye_radius)
        elif eye_shape == "laughing":
            # Wide open eyes for laughing
            glColor3f(*self.face_color)
            # Make eyes much larger for laughing
            laugh_radius = eye_radius * 1.8
            self.draw_circle(left_eye_x, eye_y, laugh_radius)
            self.draw_circle(right_eye_x, eye_y, laugh_radius)
            # Draw pupils for laughing eyes
            if blink_factor < 0.7:
                self.draw_pupils(left_eye_x, right_eye_y, eye_y, laugh_radius, pupils_data, blink_factor)
        else:
            # Standard eye shapes with blinking
            if blink_factor > 0:
                # Blinking - draw closed/squinted eyes
                eye_height = eye_radius * (1.0 - blink_factor * 0.8)
                self.draw_oval(left_eye_x, eye_y, eye_radius, eye_height)
                self.draw_oval(right_eye_x, eye_y, eye_radius, eye_height)
                
                # Draw eyelashes during blinks
                if blink_factor > 0.5:  # Only show eyelashes when eyes are more closed
                    self.draw_eyelashes(left_eye_x, eye_y, eye_radius)
                    self.draw_eyelashes(right_eye_x, eye_y, eye_radius)
            else:
                # Normal open eyes
                if eye_shape == "circle":
                    self.draw_circle(left_eye_x, eye_y, eye_radius)
                    self.draw_circle(right_eye_x, eye_y, eye_radius)
                elif eye_shape == "oval":
                    self.draw_oval(left_eye_x, eye_y, eye_radius, eye_radius * 0.8)
                    self.draw_oval(right_eye_x, eye_y, eye_radius, eye_radius * 0.8)
                elif eye_shape == "wide":
                    # Wide eyes for surprise/shock
                    self.draw_circle(left_eye_x, eye_y, eye_radius * 1.2)
                    self.draw_circle(right_eye_x, eye_y, eye_radius * 1.2)
                elif eye_shape == "sleepy":
                    # Sleepy eyes should be closed lines
                    self.draw_closed_eyes(left_eye_x, eye_y, eye_radius)
                    self.draw_closed_eyes(right_eye_x, eye_y, eye_radius)
                elif eye_shape == "squinted":
                    self.draw_oval(left_eye_x, eye_y, eye_radius, eye_radius * 0.4)
                    self.draw_oval(right_eye_x, eye_y, eye_radius, eye_radius * 0.4)
                else:
                    self.draw_circle(left_eye_x, eye_y, eye_radius)
                    self.draw_circle(right_eye_x, eye_y, eye_radius)
            
            # Draw pupils if eyes are open enough
            if blink_factor < 0.7 and eye_shape not in ["x_eyes", "dollar", "spiral", "crescent_happy", "crescent_sad"]:
                self.draw_pupils(left_eye_x, right_eye_x, eye_y, eye_radius, pupils_data, blink_factor)

    def draw_closed_eyes(self, x: float, y: float, radius: float):
        """Draw closed eyes as horizontal lines"""
        glLineWidth(4.0)
        glBegin(GL_LINES)
        glVertex2f(x - radius * 0.8, y)
        glVertex2f(x + radius * 0.8, y)
        glEnd()

    def draw_sad_crescents(self, x: float, y: float, radius: float):
        """Draw downward crescents for sad expressions - FROWN DOWN"""
        glLineWidth(4.0)
        glBegin(GL_LINE_STRIP)
        segments = 20
        for i in range(segments + 1):
            t = i / segments
            # Upper arc for sadness - curves upward like current happy
            angle = math.pi * 0.2 + t * math.pi * 0.6  # Upper portion of circle
            crescent_x = x + radius * 0.8 * math.cos(angle)
            crescent_y = y + radius * 0.8 * math.sin(angle)
            glVertex2f(crescent_x, crescent_y)
        glEnd()

    def draw_happy_crescents(self, x: float, y: float, radius: float):
        """Draw upward crescents for happy expressions - SMILE UP"""
        glLineWidth(4.0)
        glBegin(GL_LINE_STRIP)
        segments = 20
        for i in range(segments + 1):
            t = i / segments
            # Lower arc for happiness - curves downward like current sad
            angle = math.pi * 1.2 + t * math.pi * 0.6  # Lower portion of circle
            crescent_x = x + radius * 0.8 * math.cos(angle)
            crescent_y = y + radius * 0.8 * math.sin(angle)
            glVertex2f(crescent_x, crescent_y)
        glEnd()

    def draw_oval(self, x: float, y: float, width: float, height: float, filled: bool = True, segments: int = 32):
        """Draw enhanced oval"""
        if filled:
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(x, y)
        else:
            glBegin(GL_LINE_LOOP)
        
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            glVertex2f(x + width * math.cos(angle), y + height * math.sin(angle))
        glEnd()

    def draw_star(self, x: float, y: float, size: float, rotation: float = 0):
        """Draw a star shape with optional rotation"""
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(x, y)
        
        for i in range(11):
            angle = 2.0 * math.pi * i / 10 + math.radians(rotation)
            radius = size if i % 2 == 0 else size * 0.4
            glVertex2f(x + radius * math.cos(angle - math.pi / 2), y + radius * math.sin(angle - math.pi / 2))
        glEnd()

    def draw_dollar_sign(self, x: float, y: float, size: float):
        """Draw dollar sign eyes"""
        glLineWidth(4.0)
        # Vertical lines
        glBegin(GL_LINES)
        glVertex2f(x, y - size)
        glVertex2f(x, y + size)
        glEnd()
        
        # S curves
        glBegin(GL_LINE_STRIP)
        segments = 20
        for i in range(segments + 1):
            t = i / segments
            curve_x = x + size * 0.5 * math.sin(t * math.pi * 2)
            curve_y = y + (t - 0.5) * size * 1.5
            glVertex2f(curve_x, curve_y)
        glEnd()

    def draw_x_eyes(self, x: float, y: float, size: float):
        """Draw X-shaped eyes"""
        glLineWidth(6.0)
        glBegin(GL_LINES)
        # First diagonal
        glVertex2f(x - size * 0.5, y - size * 0.5)
        glVertex2f(x + size * 0.5, y + size * 0.5)
        # Second diagonal
        glVertex2f(x - size * 0.5, y + size * 0.5)
        glVertex2f(x + size * 0.5, y - size * 0.5)
        glEnd()

    def draw_spiral(self, x: float, y: float, size: float):
        """Draw spiral eyes"""
        glLineWidth(3.0)
        glBegin(GL_LINE_STRIP)
        
        for i in range(100):
            t = i / 20.0
            radius = size * (1.0 - t / 5.0)
            angle = t * math.pi
            if radius > 0:
                glVertex2f(x + radius * math.cos(angle), y + radius * math.sin(angle))
        glEnd()

    def draw_pupils(self, left_x: float, right_x: float, y: float, eye_radius: float, pupils_data: Dict, blink_factor: float):
        """Draw enhanced pupils"""
        pupil_size = pupils_data.get("size", "normal")
        pupil_position = pupils_data.get("position", "center")
        
        pupil_radius = eye_radius * 0.4 * (1.0 - blink_factor * 0.5)
        
        # Pupil position offset
        offset_x, offset_y = 0, 0
        if pupil_position == "up":
            offset_y = eye_radius * 0.3
        elif pupil_position == "down":
            offset_y = -eye_radius * 0.3
        elif pupil_position == "left":
            offset_x = -eye_radius * 0.3
        elif pupil_position == "right":
            offset_x = eye_radius * 0.3
        
        glColor3f(*self.pupil_color)
        self.draw_circle(left_x + offset_x, y + offset_y, pupil_radius)
        self.draw_circle(right_x + offset_x, y + offset_y, pupil_radius)

    def draw_enhanced_mouth(self, expression_data: Dict, vibration_offset: Tuple[float, float], animation_engine):
        """Draw enhanced mouth with creative shapes"""
        mouth_data = expression_data.get("mouth", {})
        shape = mouth_data.get("shape", "cute_smile")
        
        # Use centered coordinates for mouth
        mouth_x = 0.0 + vibration_offset[0]/100
        mouth_y = -0.3 + vibration_offset[1]/100 + animation_engine.breathing_offset * 0.005
        mouth_width = 0.8  # Increased from 0.6 for larger face
        mouth_height = 0.15  # Increased from 0.1 for larger face
        
        glColor3f(*self.face_color)
        glLineWidth(3.0)
        
        if shape == "heart":
            glColor3f(1.0, 0.4, 0.5)
            self.draw_heart_shape(mouth_x, mouth_y, mouth_width)
        elif shape == "zigzag":
            glColor3f(1.0, 0.3, 0.3)  # Red for angry zigzag
            self.draw_zigzag_mouth(mouth_x, mouth_y, mouth_width, mouth_height)
        elif shape == "wavy":
            glColor3f(0.8, 0.8, 0.3)  # Yellow for confused wavy
            self.draw_wavy_mouth(mouth_x, mouth_y, mouth_width, mouth_height)
        elif shape == "gasp":
            glColor3f(0.1, 0.1, 0.1)  # Dark for open mouth
            self.draw_circle(mouth_x, mouth_y, mouth_width * 0.8, filled=True)
        elif shape == "kiss":
            glColor3f(1.0, 0.5, 0.6)  # Pink for kiss
            self.draw_circle(mouth_x, mouth_y, mouth_width * 0.4, filled=False)
        else:
            # Standard mouth shapes
            self.draw_standard_mouth(mouth_x, mouth_y, mouth_width, mouth_height, shape, animation_engine)

    def draw_zigzag_mouth(self, x: float, y: float, width: float, height: float):
        """Draw zigzag mouth for anger"""
        glBegin(GL_LINE_STRIP)
        segments = 8
        for i in range(segments + 1):
            t = i / segments
            zigzag_x = x + (t - 0.5) * width
            zigzag_y = y + height * (1 if i % 2 == 0 else -1)
            glVertex2f(zigzag_x, zigzag_y)
        glEnd()

    def draw_wavy_mouth(self, x: float, y: float, width: float, height: float):
        """Draw wavy mouth for confusion"""
        glBegin(GL_LINE_STRIP)
        segments = 20
        for i in range(segments + 1):
            t = i / segments
            wave_x = x + (t - 0.5) * width
            wave_y = y + height * math.sin(t * math.pi * 4) * 0.5
            glVertex2f(wave_x, wave_y)
        glEnd()

    def draw_standard_mouth(self, x: float, y: float, width: float, height: float, shape: str, animation_engine=None):
        """Draw standard mouth shapes with correct curves and talking animation"""
        
        if shape == "talking" and animation_engine:
            # Enhanced talking mouth with flattening and rounding at intervals
            talk_phase = (time.time() * animation_engine.talk_speed) % (2 * math.pi)
            
            if talk_phase < math.pi / 4:
                # Flattened mouth (consonants/closed)
                glBegin(GL_LINES)
                glVertex2f(x - width * 0.4, y)
                glVertex2f(x + width * 0.4, y)
                glEnd()
            elif talk_phase < math.pi / 2:
                # Small round mouth (O/U sounds)
                self.draw_circle(x, y, width * 0.2, False)
            elif talk_phase < 3 * math.pi / 4:
                # Wide oval mouth (A sounds)
                self.draw_oval(x, y, width * 0.5, height * 0.3, False)
            elif talk_phase < math.pi:
                # Medium round mouth (E sounds)
                self.draw_oval(x, y, width * 0.3, height * 0.2, False)
            elif talk_phase < 5 * math.pi / 4:
                # Flattened again
                glBegin(GL_LINES)
                glVertex2f(x - width * 0.3, y)
                glVertex2f(x + width * 0.3, y)
                glEnd()
            elif talk_phase < 3 * math.pi / 2:
                # Small round again
                self.draw_circle(x, y, width * 0.15, False)
            elif talk_phase < 7 * math.pi / 4:
                # Slightly open oval
                self.draw_oval(x, y, width * 0.4, height * 0.25, False)
            else:
                # Back to flattened
                glBegin(GL_LINES)
                glVertex2f(x - width * 0.35, y)
                glVertex2f(x + width * 0.35, y)
                glEnd()
        else:
            # Standard mouth shapes with curves
            glBegin(GL_LINE_STRIP)
            segments = 20
            for i in range(segments + 1):
                t = i / segments
                mouth_x = x + (t - 0.5) * width
                
                if shape in ["big_smile", "cute_smile", "small_smile"]:
                    # DOWNWARD curve for smiles - SAD = DOWN (swapped)
                    curve_intensity = 6 if shape == "big_smile" else 4 if shape == "cute_smile" else 2
                    mouth_y = y - height * math.sin(t * math.pi) * curve_intensity
                elif shape in ["big_frown", "small_frown"]:
                    # UPWARD curve for frowns - HAPPY = UP (swapped)
                    curve_intensity = 6 if shape == "big_frown" else 3
                    mouth_y = y + height * math.sin(t * math.pi) * curve_intensity
                elif shape == "kiss":
                    # Small rounded shape for kissing
                    mouth_y = y + height * math.sin(t * math.pi) * 2
                elif shape == "open_wide":
                    # Large open mouth
                    mouth_y = y - height * 3
                elif shape == "open_small":
                    # Small open mouth
                    mouth_y = y - height * 2
                else:  # neutral
                    mouth_y = y
                
                glVertex2f(mouth_x, mouth_y)
            glEnd()

    def draw_special_effects(self, animation_engine, expression_data: Dict):
        """Draw all special visual effects"""
        effects = expression_data.get("special_effects", [])
        
        # Draw tears
        if animation_engine.tears:
            glColor4f(*self.tear_color)
            for tear in animation_engine.tears:
                self.draw_tear_drop(tear['x'], tear['y'], tear['size'], tear['alpha'])
        
        # Draw floating hearts
        if animation_engine.hearts:
            for heart in animation_engine.hearts:
                glColor4f(*heart['color'], heart['life'] / 4.0)
                self.draw_heart_shape(heart['x'], heart['y'], heart['size'], heart['rotation'])
        
        # Draw sparkles
        if animation_engine.sparkles:
            for sparkle in animation_engine.sparkles:
                glColor4f(*sparkle['color'], sparkle['alpha'])
                self.draw_sparkle(sparkle['x'], sparkle['y'], sparkle['size'], sparkle['rotation'])
        
        # Add effect-specific animations
        if "broken_heart" in effects:
            self.draw_broken_heart_effect()
        
        if "zzz_bubbles" in effects:
            self.draw_zzz_bubbles()
        
        if "question_marks" in effects:
            self.draw_question_marks()

    def draw_tear_drop(self, x: float, y: float, size: float, alpha: float):
        """Draw realistic, asymmetric large tear drop with a more natural droplet shape"""
        glPushMatrix()
        glTranslatef(x, y, 0)
        
        # Make tears larger and more visible
        tear_size = size * 3.0
        
        # Draw the main tear body with a more realistic teardrop shape
        glColor4f(*self.tear_color[:3], alpha)
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0, -tear_size * 1.25)  # Bottom point (more pointed)
        segments = 48
        for i in range(segments + 1):
            t = i / segments
            angle = math.pi * t
            # Parametric teardrop: x = a * sin(t) * (1 + 0.2 * cos(t)), y = -b * (cos(t) - 1)
            # Add a slight horizontal offset for natural asymmetry
            offset = 0.12 * math.sin(2 * angle)
            drop_x = tear_size * 0.7 * math.sin(angle) * (1 + 0.18 * math.cos(angle)) + tear_size * offset
            drop_y = tear_size * 0.95 * (math.cos(angle) - 1.25)
            glVertex2f(drop_x, drop_y)
        glEnd()
        
        # Main highlight (oval, off-center)
        glColor4f(1.0, 1.0, 1.0, alpha * 0.7)
        highlight_size = tear_size * 0.38
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(-tear_size * 0.22, -tear_size * 0.25)
        for i in range(16):
            angle = 2.0 * math.pi * i / 16
            hx = highlight_size * 0.7 * math.cos(angle)
            hy = highlight_size * 0.45 * math.sin(angle)
            glVertex2f(-tear_size * 0.22 + hx, -tear_size * 0.25 + hy)
        glEnd()
        
        # Secondary smaller highlight
        glColor4f(1.0, 1.0, 1.0, alpha * 0.4)
        small_highlight = tear_size * 0.13
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(tear_size * 0.13, -tear_size * 0.55)
        for i in range(12):
            angle = 2.0 * math.pi * i / 12
            hx = small_highlight * 0.5 * math.cos(angle)
            hy = small_highlight * 0.3 * math.sin(angle)
            glVertex2f(tear_size * 0.13 + hx, -tear_size * 0.55 + hy)
        glEnd()
        
        glPopMatrix()

    def draw_sparkle(self, x: float, y: float, size: float, rotation: float):
        """Draw twinkling sparkle"""
        glPushMatrix()
        glTranslatef(x, y, 0)
        glRotatef(math.degrees(rotation), 0, 0, 1)
        
        glLineWidth(2.0)
        glBegin(GL_LINES)
        # Four-pointed star
        glVertex2f(-size, 0)
        glVertex2f(size, 0)
        glVertex2f(0, -size)
        glVertex2f(0, size)
        # Diagonal lines
        glVertex2f(-size * 0.7, -size * 0.7)
        glVertex2f(size * 0.7, size * 0.7)
        glVertex2f(-size * 0.7, size * 0.7)
        glVertex2f(size * 0.7, -size * 0.7)
        glEnd()
        
        glPopMatrix()

    def draw_broken_heart_effect(self):
        """Draw large broken heart in center of screen"""
        glColor4f(1.0, 0.2, 0.3, 0.8)  # More visible red
        break_offset = 15 * math.sin(time.time() * 3)  # Slower, more dramatic
        # Make the broken heart much larger
        self.draw_broken_heart(self.width // 2, self.height // 2 + 30, 50, break_offset)

    def draw_zzz_bubbles(self):
        """Draw floating Z's for sleepy expression"""
        glColor4f(0.8, 0.8, 1.0, 0.7)
        
        for i in range(3):
            z_x = self.width // 2 + 80 + i * 20
            z_y = self.height // 2 + 60 + 20 * math.sin(time.time() * 2 + i)
            z_size = 15 - i * 3
            self.draw_z_letter(z_x, z_y, z_size)

    def draw_z_letter(self, x: float, y: float, size: float):
        """Draw a Z letter"""
        glLineWidth(3.0)
        glBegin(GL_LINE_STRIP)
        glVertex2f(x - size, y + size)
        glVertex2f(x + size, y + size)
        glVertex2f(x - size, y - size)
        glVertex2f(x + size, y - size)
        glEnd()

    def draw_question_marks(self):
        """Draw floating question marks"""
        glColor4f(1.0, 1.0, 0.5, 0.8)
        
        for i in range(2):
            q_x = self.width // 2 + 60 + i * 40
            q_y = self.height // 2 + 80 + 15 * math.sin(time.time() * 3 + i * 2)
            self.draw_question_mark(q_x, q_y, 12)

    def draw_question_mark(self, x: float, y: float, size: float):
        """Draw question mark"""
        glLineWidth(3.0)
        
        # Question mark curve
        glBegin(GL_LINE_STRIP)
        segments = 10
        for i in range(segments):
            t = i / (segments - 1)
            angle = math.pi * t
            qx = x + size * 0.3 * math.cos(angle)
            qy = y + size * 0.8 + size * 0.3 * math.sin(angle)
            glVertex2f(qx, qy)
        glEnd()
        
        # Vertical line
        glBegin(GL_LINES)
        glVertex2f(x, y + size * 0.3)
        glVertex2f(x, y)
        glEnd()
        
        # Dot
        self.draw_circle(x, y - size * 0.3, size * 0.1)

    def render_enhanced_face(self, expression_data: Dict, vibration_pattern: str, animation_engine):
        """Render the complete enhanced robot face"""
        self.animation_time = time.time()
        
        # Calculate vibration offset
        vibration_offset = (0, 0)  # Simplified for now
        
        # Clear screen
        glClear(GL_COLOR_BUFFER_BIT)
        
        # Draw background effects
        self.draw_background_color(expression_data)
        
        # Draw main face components
        self.draw_enhanced_eyes(expression_data, vibration_offset, animation_engine)
        self.draw_eyebrows(expression_data, vibration_offset, animation_engine)
        self.draw_enhanced_mouth(expression_data, vibration_offset, animation_engine)
        
        # Draw special effects
        self.draw_special_effects(animation_engine, expression_data)

    def draw_background_color(self, expression_data: Dict):
        """Draw background color for centered coordinates"""
        bg_data = expression_data.get("background", {})
        color = bg_data.get("color", "none")
        
        if color != "none":
            # Simple color mapping
            colors = {
                "red": (0.3, 0.1, 0.1),
                "blue": (0.1, 0.2, 0.3),
                "yellow": (0.3, 0.3, 0.1),
                "green": (0.1, 0.3, 0.1),
                "pink": (0.3, 0.2, 0.2),
                "purple": (0.2, 0.1, 0.3),
                "orange": (0.3, 0.2, 0.1),
                "cyan": (0.1, 0.3, 0.3)
            }
            
            if color in colors:
                glColor3f(*colors[color])
                glBegin(GL_QUADS)
                glVertex2f(-2.5, -2.0)  # Bottom left for centered coordinates
                glVertex2f(2.5, -2.0)   # Bottom right
                glVertex2f(2.5, 2.0)    # Top right
                glVertex2f(-2.5, 2.0)   # Top left
                glEnd()

    def draw_eyebrows(self, expression_data: Dict, vibration_offset: Tuple[float, float], animation_engine):
        """Draw enhanced eyebrows with animation for anger"""
        eyebrows_data = expression_data.get("eyebrows", {})
        position = eyebrows_data.get("position", "normal")
        
        # Position mapping
        positions = {
            "very_low": -0.1, "low": -0.05, "normal": 0,
            "raised": 0.05, "high": 0.1, "very_high": 0.15,
            "angry": -0.08, "worried": 0.03
        }
        
        offset_y = positions.get(position, 0)
        eyebrow_y = 0.7 + offset_y + vibration_offset[1]/100 + animation_engine.breathing_offset/100 * 0.3
        
        # Add furious animation for angry eyebrows
        furious_offset = 0
        if position == "angry":
            # Animated furious eyebrows - bouncing effect
            furious_offset = math.sin(time.time() * 8) * 0.01
            eyebrow_y += furious_offset
        
        # Use centered coordinates for eyebrows
        eye_separation = 0.8  # Increased for larger face
        left_eyebrow_x = -eye_separation/2 + vibration_offset[0]/100
        right_eyebrow_x = eye_separation/2 + vibration_offset[0]/100
        
        glColor3f(*self.eyebrow_color)
        glLineWidth(6.0)  # Make eyebrows thicker/bigger
        
        eyebrow_width = 0.4  # Adjusted for centered coordinates
        
        # Left eyebrow
        glBegin(GL_LINE_STRIP)
        for i in range(21):
            t = i / 20.0
            x = left_eyebrow_x + (t - 0.5) * eyebrow_width
            y = eyebrow_y + 0.02 * math.sin(t * math.pi)  # Make eyebrow curve more prominent
            if position == "angry":
                y += (0.5 - t) * 0.05  # More angled down for anger
                # Add jagged effect for furiousness
                if i % 3 == 0:
                    y += random.uniform(-0.01, 0.01)
            glVertex2f(x, y)
        glEnd()
        
        # Right eyebrow
        glBegin(GL_LINE_STRIP)
        for i in range(21):
            t = i / 20.0
            x = right_eyebrow_x + (t - 0.5) * eyebrow_width
            y = eyebrow_y + 0.02 * math.sin(t * math.pi)  # Make eyebrow curve more prominent
            if position == "angry":
                y += (t - 0.5) * 0.05  # More angled down for anger
                # Add jagged effect for furiousness
                if i % 3 == 0:
                    y += random.uniform(-0.01, 0.01)
            glVertex2f(x, y)
        glEnd()
        
        # Draw eyelashes attached to eyebrows
        self.draw_eyebrow_eyelashes(left_eyebrow_x, eyebrow_y, eyebrow_width)
        self.draw_eyebrow_eyelashes(right_eyebrow_x, eyebrow_y, eyebrow_width)

    def draw_eyebrow_eyelashes(self, x: float, y: float, eyebrow_width: float):
        """Draw eyelashes attached to eyebrows"""
        glColor3f(0.0, 0.0, 0.0)  # Much darker (pure black) for eyelashes
        glLineWidth(2.0)  # Make eyelashes thicker too
        
        # Draw 4 eyelashes hanging down from each eyebrow
        for i in range(4):
            t = (i + 1) / 5.0  # Position along eyebrow
            lash_x = x + (t - 0.5) * eyebrow_width
            lash_y = y + 0.01 * math.sin(t * math.pi)  # Follow eyebrow curve
            
            # Draw eyelash hanging down from eyebrow
            lash_length = 0.03  # Adjusted for centered coordinates
            
            glBegin(GL_LINES)
            glVertex2f(lash_x, lash_y)
            glVertex2f(lash_x, lash_y - lash_length)
            glEnd()

    def draw_eyelashes(self, x: float, y: float, eye_radius: float):
        """Draw eyelashes that appear during blinks"""
        glColor3f(0.0, 0.0, 0.0)  # Much darker (pure black) for eyelashes
        glLineWidth(3.0)  # Make eyelashes thicker
        
        # Draw 5 eyelashes on top of each eye
        for i in range(5):
            angle_start = -math.pi * 0.6 + (i * math.pi * 0.3)
            lash_length = eye_radius * 0.5  # Make eyelashes longer
            
            # Start point on eye edge
            start_x = x + eye_radius * math.cos(angle_start)
            start_y = y + eye_radius * math.sin(angle_start)
            
            # End point of eyelash
            end_x = start_x + lash_length * math.cos(angle_start - math.pi * 0.2)
            end_y = start_y + lash_length * math.sin(angle_start - math.pi * 0.2)
            
            glBegin(GL_LINES)
            glVertex2f(start_x, start_y)
            glVertex2f(end_x, end_y)
            glEnd()

class EnhancedRobotFaceSystem:
    """Enhanced main system with all new features"""

    def __init__(self, width=480, height=320, api_url="http://localhost:8001", user_name="test_user"):
        self.loader = ExpressionLoader()
        self.expression_engine = ExpressionEngine(self.loader)
        
        # Get vibration patterns from JSON
        vibration_patterns = self.loader.parameter_maps.get("vibration_patterns", {})
        self.vibration_engine = VibrationEngine(vibration_patterns)
        
        # Set display dimensions
        self.width = width
        self.height = height
        self.fps = 60
        
        # Initialize voice assistant client
        self.voice_assistant = VoiceAssistantClient(api_url, user_name)
        
        self.face_renderer = EnhancedRobotFace(self.width, self.height, self.loader.settings)
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Initialize font system (will be set up after pygame.init)
        self.font = None
        self.font_large = None
        
        # Expression cycling
        self.expression_list = list(self.loader.expressions.keys())
        self.current_expression_index = 0
        
        # Auto conversation mode settings
        self.auto_conversation_mode = False  # Start with auto mode disabled
        self.is_sleeping = False
        self.conversation_active = False
        self.audio_thread = None
        self.min_input_length = 5  # Minimum characters to continue conversation
        
        # Button system
        self.buttons = []
        self.setup_buttons()
        
        # Text display system
        self.current_ai_text = ""
        self.display_text = True
        self.text_display_time = 0
        self.text_fade_duration = 10.0  # Show text for 10 seconds
        
        print("Enhanced Robot Face System with Voice Assistant initialized!")
        print("Available expressions:", self.expression_list)
        print("Auto conversation mode - use buttons to start/stop")

    def initialize(self):
        """Initialize the enhanced system"""
        pygame.init()
        pygame.display.set_mode((self.width, self.height), DOUBLEBUF | OPENGL)
        
        title = "GUNI Assistant - Auto Conversation Mode"
        pygame.display.set_caption(title)
        
        # Initialize OpenGL
        self.face_renderer.initialize_opengl()
        
        # Initialize fonts for text rendering
        try:
            # Try different font options for better text display
            font_options = [
                ('opensans', 24),  # Try OpenSans first
                ('cantarell', 24), # Try Cantarell
                (None, 24),        # Default pygame font
            ]
            
            self.font = None
            for font_name, size in font_options:
                try:
                    if font_name:
                        # Try to find the font by name
                        font_path = pygame.font.match_font(font_name)
                        if font_path:
                            self.font = pygame.font.Font(font_path, size)
                            print(f"Successfully loaded font: {font_name}")
                            break
                    else:
                        # Default font
                        self.font = pygame.font.Font(None, size)
                        print("Using default pygame font")
                        break
                except Exception as font_error:
                    print(f"Failed to load font {font_name}: {font_error}")
                    continue
            
            # Fallback if no font worked
            if not self.font:
                self.font = pygame.font.Font(None, 24)
                print("Using fallback default font")
            
            # Large font for headers
            self.font_large = pygame.font.Font(None, 32)
            print("Text rendering system initialized successfully")
            
        except Exception as e:
            print(f"Font initialization error: {e}")
            # Ultimate fallback
            self.font = pygame.font.Font(None, 24)
            self.font_large = pygame.font.Font(None, 32)
        
        print("Enhanced system initialized!")
        
        # Don't auto-start conversation - wait for button press
        print("Ready! Use Start button to begin auto conversation.")
        self.print_controls()

    def setup_buttons(self):
        """Setup visual buttons positioned around the robot face"""
        self.buttons = []
        # Left side button - Start Auto Conversation
        self.buttons.append({
            "id": "start_auto", "text": "🎤 START\nAuto Chat", "x": -2.2, "y": 0.4,
            "width": 1.0, "height": 0.8, "color": (0.2, 0.7, 0.2), "hover_color": (0.3, 0.9, 0.3),
            "text_color": (1.0, 1.0, 1.0), "action": self.start_conversation_mode, "enabled": True
        })
        # Right side button - Stop Auto Conversation
        self.buttons.append({
            "id": "stop_auto", "text": "⏹️ STOP\nAuto Chat", "x": 1.2, "y": 0.4,
            "width": 1.0, "height": 0.8, "color": (0.7, 0.2, 0.2), "hover_color": (0.9, 0.3, 0.3),
            "text_color": (1.0, 1.0, 1.0), "action": self.stop_conversation_mode, "enabled": True
        })

    def draw_button(self, button):
        """Draw a visual button using OpenGL"""
        x, y = button["x"], button["y"]
        width, height = button["width"], button["height"]
        color = button["color"]
        
        # Draw button background
        glColor3f(*color)
        glBegin(GL_QUADS)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()
        
        # Draw button border
        glColor3f(0.8, 0.8, 0.8)
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(x, y)
        glVertex2f(x + width, y)
        glVertex2f(x + width, y + height)
        glVertex2f(x, y + height)
        glEnd()

    def handle_mouse_click(self, mouse_pos):
        """Handle mouse clicks on buttons"""
        mouse_x, mouse_y = mouse_pos
        gl_x = (mouse_x / self.width) * 5.0 - 2.5
        gl_y = 2.0 - (mouse_y / self.height) * 4.0
        
        for button in self.buttons:
            bx, by = button["x"], button["y"]
            bw, bh = button["width"], button["height"]
            if bx <= gl_x <= bx + bw and by <= gl_y <= by + bh:
                if button["enabled"] and button["action"]:
                    button["action"]()
                return True
        return False

    def start_auto_conversation(self):
        """Start automatic conversation mode"""
        if not self.conversation_active and not self.is_sleeping:
            logger.info("Starting auto conversation mode")
            self.conversation_active = True
            self.set_expression("happy")  # Start with happy, not talking
            
            # Start the conversation thread
            self.audio_thread = threading.Thread(target=self.auto_conversation_worker)
            self.audio_thread.daemon = True
            self.audio_thread.start()

    def auto_conversation_worker(self):
        """Worker function for automatic continuous conversation"""
        try:
            while self.running and self.conversation_active and not self.is_sleeping:
                logger.info("Starting new conversation cycle...")
                
                # Set happy expression for listening/recording
                self.set_expression("happy")
                
                # Reset states
                self.voice_assistant.is_recording = True
                self.voice_assistant.is_processing = False
                self.voice_assistant.is_speaking = False
                
                # Step 1: Record audio
                logger.info("Listening for user input...")
                audio_path = self.voice_assistant.record_audio()
                self.voice_assistant.is_recording = False
                
                if not audio_path:
                    logger.error("Failed to record audio, continuing...")
                    self.set_expression("confused")
                    time.sleep(2)
                    continue
                
                # Step 2: Send to API and get transcription
                logger.info("Processing audio with API...")
                self.voice_assistant.is_processing = True
                self.set_expression("cute_neutral")  # Waiting expression
                response_data = self.voice_assistant.send_audio_to_api(audio_path)
                self.voice_assistant.is_processing = False
                
                if not response_data:
                    logger.error("Failed to get API response, continuing...")
                    self.set_expression("confused")
                    time.sleep(2)
                    continue
                
                # Step 3: Check transcription length
                user_input = response_data.get('user_input', '')
                text_response = response_data.get('text_response', '')
                
                logger.info(f"User input received: '{user_input}' (length: {len(user_input)})")
                
                # If input is too short, enter sleep mode
                if len(user_input.strip()) < self.min_input_length:
                    logger.info(f"Input too short ({len(user_input)} < {self.min_input_length}), entering sleep mode")
                    self.enter_sleep_mode()
                    break
                
                # Step 4: Store conversation
                language_used = response_data.get('language_used', 'english')
                self.voice_assistant.store_conversation(
                    user_input,
                    text_response,
                    language_used
                )
                
                # Step 4.5: Update text display
                # Convert non-ASCII text to ASCII-safe format for OpenGL rendering
                display_text = text_response
                try:
                    # For Unicode text (like Hindi), convert to transliterated form
                    display_text = text_response.encode('ascii', 'ignore').decode('ascii')
                    if not display_text.strip():
                        # If no ASCII chars, use a placeholder
                        display_text = f"[Response in {language_used}] - {len(text_response)} characters"
                except:
                    display_text = f"[Non-ASCII Response] - {len(text_response)} characters"
                
                self.current_ai_text = display_text
                self.text_display_time = time.time()
                logger.info(f"AI text response: {text_response}")
                logger.info(f"Display text: {display_text}")
                logger.info(f"Text display updated: text_length={len(display_text)}, display_enabled={self.display_text}, timestamp={self.text_display_time}")
                
                # Step 5: Set talking expression ONLY when playing audio
                logger.info("Playing AI response...")
                self.set_expression("talking")  # NOW set talking expression
                self.voice_assistant.is_speaking = True
                self.voice_assistant.play_audio_response(response_data)
                self.voice_assistant.is_speaking = False
                
                # Step 6: Update robot expression based on AI response after speaking
                robot_expression = response_data.get('robot_expression', 'happy')
                logger.info(f"Setting robot expression to: {robot_expression}")
                
                # Check if API wants robot to go to sleep
                if robot_expression == "sleepy":
                    logger.info("API requested sleep mode via 'sleepy' expression")
                    self.enter_sleep_mode()
                    break
                
                self.set_expression(robot_expression)
                
                # Brief pause before next cycle
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Auto conversation error: {e}")
            self.conversation_active = False
            self.set_expression("confused")

    def enter_sleep_mode(self):
        """Enter sleep mode when no meaningful input is detected"""
        logger.info("Entering sleep mode...")
        self.is_sleeping = True
        self.conversation_active = False
        self.set_expression("sleepy")
        
        # Reset voice assistant states
        self.voice_assistant.is_recording = False
        self.voice_assistant.is_processing = False
        self.voice_assistant.is_speaking = False
        
        # Show sleep message
        print("🤖 Robot is now sleeping. Press 'W' to wake up or use Start button.")

    def wake_up(self):
        """Wake up from sleep mode"""
        if self.is_sleeping:
            logger.info("Waking up from sleep mode...")
            self.is_sleeping = False
            self.set_expression("surprised")  # Wake up expression
            time.sleep(1)
            
            # Restart auto conversation
            self.start_conversation_mode()

    def run(self):
        """Run the system with auto conversation"""
        # Set initial expression to happy
        global expp
        if expp in self.expression_list:
            self.set_expression(expp)
        else:
            self.set_expression("happy")  # Default to happy expression
        
        last_wake_check = time.time()
        
        while self.running:
            self.handle_events()
            delta_time = self.clock.tick(self.fps) / 1000.0
            self.update(delta_time)
            self.render()
            
            # Check for auto-wake every 5 seconds when sleeping
            current_time = time.time()
            if self.is_sleeping and (current_time - last_wake_check) > 5.0:
                self.check_auto_wake()
                last_wake_check = current_time
        
        # Clean up
        self.cleanup()

    def check_auto_wake(self):
        """Check for loud sounds or activity to auto-wake"""
        try:
            # Quick audio check for loud sounds
            import pyaudio
            audio = pyaudio.PyAudio()
            
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=1024
            )
            
            # Read a small sample
            data = stream.read(1024, exception_on_overflow=False)
            
            # Calculate volume level
            import struct
            volume = max(struct.unpack('<' + ('h' * (len(data) // 2)), data))
            
            stream.stop_stream()
            stream.close()
            audio.terminate()
            
            # If volume is above threshold, wake up
            if volume > 5000:  # Adjust threshold as needed
                logger.info(f"Auto-wake triggered by sound level: {volume}")
                self.wake_up()
                
        except Exception as e:
            logger.debug(f"Auto-wake check failed: {e}")

    def handle_events(self):
        """Handle events with button controls and wake-up controls"""
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == MOUSEBUTTONDOWN:
                # Handle mouse clicks on buttons
                if event.button == 1:  # Left mouse button
                    self.handle_mouse_click(event.pos)
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                elif event.key == K_w:  # Wake up key
                    if self.is_sleeping:
                        self.wake_up()
                elif event.key == K_s:  # Force sleep key
                    if not self.is_sleeping:
                        self.enter_sleep_mode()
                elif event.key == K_r:  # Restart conversation
                    if not self.conversation_active and not self.is_sleeping:
                        self.start_conversation_mode()
                elif event.key == K_t:  # Toggle text display
                    self.display_text = not self.display_text
                    logger.info(f"Text display {'enabled' if self.display_text else 'disabled'}")
                elif event.key == K_x:  # Test text display
                    self.current_ai_text = "Test message: This is a test of the text display system!"
                    self.text_display_time = time.time()
                    logger.info("Test text display activated")
                # Button Controls
                elif event.key == K_1:  # Start Auto Conversation
                    self.start_conversation_mode()
                elif event.key == K_2:  # Stop Auto Conversation
                    self.stop_conversation_mode()

    def start_conversation_mode(self):
        """Start automatic conversation mode"""
        if not self.conversation_active and not self.is_sleeping:
            logger.info("Starting auto conversation mode")
            self.auto_conversation_mode = True
            self.conversation_active = True
            self.set_expression("happy")  # Start with happy, not talking
            
            # Start the conversation thread
            self.audio_thread = threading.Thread(target=self.auto_conversation_worker)
            self.audio_thread.daemon = True
            self.audio_thread.start()
            
            print("🔄 Auto-conversation mode activated! (Press 2 or Stop button to stop)")

    def stop_conversation_mode(self):
        """Stop conversation mode and return to standby"""
        logger.info("Stopping conversation mode")
        self.conversation_active = False
        self.auto_conversation_mode = False
        self.is_sleeping = False
        
        # Reset voice assistant states
        self.voice_assistant.is_recording = False
        self.voice_assistant.is_processing = False
        self.voice_assistant.is_speaking = False
        
        self.set_expression("cute_neutral")
        print("⏹️ Auto conversation stopped - ready to start again")

    def cleanup(self):
        """Clean up resources"""
        logger.info("Cleaning up...")
        
        # Stop conversation
        self.conversation_active = False
        self.is_sleeping = True
        
        # Stop any ongoing audio operations
        self.voice_assistant.is_recording = False
        self.voice_assistant.is_processing = False
        self.voice_assistant.is_speaking = False
        
        # Stop pygame mixer
        try:
            pygame.mixer.music.stop()
        except:
            pass
        
        # Wait for audio thread to finish
        if self.audio_thread and self.audio_thread.is_alive():
            self.audio_thread.join(timeout=2.0)
        
        pygame.quit()
        print("Enhanced Robot Face System shutting down...")

    def update(self, delta_time):
        """Update the system"""
        self.expression_engine.update(delta_time)

    def render(self):
        """Render the system with status overlay"""
        glClear(GL_COLOR_BUFFER_BIT)
        expression_data = self.expression_engine.calculate_expression_data()
        vibration_pattern = expression_data.get("vibration", {}).get("pattern", "none")
        
        self.face_renderer.render_enhanced_face(
            expression_data, 
            vibration_pattern, 
            self.expression_engine.animation_engine
        )
        
        # Draw visual buttons
        for button in self.buttons:
            self.draw_button(button)
        
        # Add status text overlay
        self.render_status_overlay()
        
        # Debug: Draw a simple test rectangle to verify overlay rendering works
        if self.current_ai_text:
            self.render_debug_indicator()
        
        pygame.display.flip()

    def render_status_overlay(self):
        """Render status overlay showing current mode and AI text response"""
        # Display AI text response if available and within fade duration
        if self.current_ai_text and self.display_text:
            current_time = time.time()
            elapsed_time = current_time - self.text_display_time
            
            # Debug logging
            logger.debug(f"Text display check: text='{self.current_ai_text[:50]}...', display_enabled={self.display_text}, elapsed={elapsed_time:.1f}s")
            
            if elapsed_time < self.text_fade_duration:
                # Calculate fade factor (1.0 = fully visible, 0.0 = invisible)
                fade_factor = max(0.0, 1.0 - (elapsed_time / self.text_fade_duration))
                logger.debug(f"Rendering text with fade factor: {fade_factor:.2f}")
                self.render_text_overlay(self.current_ai_text, fade_factor)
            else:
                logger.debug("Text display time expired")
        else:
            if not self.current_ai_text:
                logger.debug("No current AI text to display")
            if not self.display_text:
                logger.debug("Text display is disabled")
    
    def render_text_overlay(self, text, alpha=1.0):
        """Render text overlay using OpenGL primitive drawing"""
        logger.debug(f"render_text_overlay called: text_length={len(text) if text else 0}, alpha={alpha:.2f}")
        
        if not text or alpha <= 0:
            logger.debug("Skipping text render: no text or alpha <= 0")
            return
        
        logger.debug(f"Actually rendering text: '{text[:50]}...'")
        
        # Set up 2D rendering for text overlay
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw semi-transparent background box
        text_lines = self.wrap_text(text, 60)  # Wrap at 60 characters
        line_count = len(text_lines)
        
        # Background dimensions
        bg_height = max(80, line_count * 25 + 20)
        bg_width = min(self.width - 40, 600)
        bg_x = (self.width - bg_width) // 2
        bg_y = 20
        
        # Draw background rectangle
        glColor4f(0.0, 0.0, 0.0, 0.7 * alpha)  # Semi-transparent black
        glBegin(GL_QUADS)
        glVertex2f(bg_x, bg_y)
        glVertex2f(bg_x + bg_width, bg_y)
        glVertex2f(bg_x + bg_width, bg_y + bg_height)
        glVertex2f(bg_x, bg_y + bg_height)
        glEnd()
        
        # Draw border
        glColor4f(0.3, 0.6, 1.0, alpha)  # Light blue border
        glLineWidth(2.0)
        glBegin(GL_LINE_LOOP)
        glVertex2f(bg_x, bg_y)
        glVertex2f(bg_x + bg_width, bg_y)
        glVertex2f(bg_x + bg_width, bg_y + bg_height)
        glVertex2f(bg_x, bg_y + bg_height)
        glEnd()
        
        # Draw text using simple bitmap drawing (dots/lines for characters)
        # This is a basic implementation - you can enhance with proper font rendering
        text_x = bg_x + 10
        text_y = bg_y + bg_height - 30
        
        glColor4f(1.0, 1.0, 1.0, alpha)  # White text
        glPointSize(2.0)
        
        for i, line in enumerate(text_lines):
            y_pos = text_y - (i * 25)
            self.draw_simple_text(line, text_x, y_pos, alpha)
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
    
    def wrap_text(self, text, width):
        """Wrap text to specified width"""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + " " + word) <= width:
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def draw_simple_text(self, text, x, y, alpha=1.0):
        """Draw text using OpenGL textures from pygame font rendering"""
        if not self.font or not text.strip():
            return
            
        try:
            # Create text surface using pygame font
            text_color = (int(204 * alpha), int(229 * alpha), int(255 * alpha))  # Light blue
            text_surface = self.font.render(text, True, text_color)
            text_data = pygame.image.tostring(text_surface, "RGBA", True)
            
            # Get text dimensions
            text_width = text_surface.get_width()
            text_height = text_surface.get_height()
            
            # Enable texturing
            glEnable(GL_TEXTURE_2D)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # Generate and bind texture
            texture_id = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, texture_id)
            
            # Set texture parameters
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
            
            # Upload texture data
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, text_width, text_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, text_data)
            
            # Set color and alpha
            glColor4f(1.0, 1.0, 1.0, alpha)
            
            # Draw textured quad
            glBegin(GL_QUADS)
            glTexCoord2f(0, 0); glVertex2f(x, y + text_height)
            glTexCoord2f(1, 0); glVertex2f(x + text_width, y + text_height)
            glTexCoord2f(1, 1); glVertex2f(x + text_width, y)
            glTexCoord2f(0, 1); glVertex2f(x, y)
            glEnd()
            
            # Clean up
            glDeleteTextures([texture_id])
            glDisable(GL_TEXTURE_2D)
            glDisable(GL_BLEND)
            
        except Exception as e:
            print(f"Text rendering error: {e}")
            # Fallback to simple line if texture rendering fails
            glColor4f(0.8, 0.9, 1.0, alpha)
            glLineWidth(2.0)
            glBegin(GL_LINES)
            glVertex2f(x, y)
            glVertex2f(x + len(text) * 8, y)
            glEnd()

    def set_expression(self, expression_name):
        """Set expression"""
        if expression_name in self.expression_list:
            self.expression_engine.set_expression(expression_name)
            logger.info(f"Expression set to: {expression_name}")

    def print_controls(self):
        """Print enhanced controls"""
        print("\n" + "="*60)
        print("🎮 CONTROL BUTTONS:")
        print("  1: 🎤 START Auto Conversation Mode")
        print("  2: ⏹️  STOP Auto Conversation Mode")
        print()
        print("🎹 KEYBOARD CONTROLS:")
        print("  ESC: Quit application")
        print("  W: Wake up from sleep")
        print("  S: Force sleep mode")
        print("  R: Start conversation (when not active)")
        print("  T: Toggle text display on/off")
        print("  X: Test text display (debug)")
        print()
        print("🤖 AUTO CONVERSATION MODE:")
        print("  - Continuous conversation until stopped or sleeping")
        print("  - Auto-sleep when input < 5 characters")
        print("  - API can trigger sleep via 'sleepy' expression")
        print("  - Wake up with W key or loud sounds")
        print("="*60)

    def render_debug_indicator(self):
        """Render a simple debug indicator to test overlay rendering"""
        # Switch to 2D rendering
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width, 0, self.height, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        # Draw a simple red rectangle in top-right corner
        glColor3f(1.0, 0.0, 0.0)  # Red color
        glBegin(GL_QUADS)
        glVertex2f(self.width - 50, self.height - 50)
        glVertex2f(self.width - 10, self.height - 50)
        glVertex2f(self.width - 10, self.height - 10)
        glVertex2f(self.width - 50, self.height - 10)
        glEnd()
        
        # Restore matrices
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)

def main():
    """Main function to start the enhanced robot face system"""
    try:
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Enhanced Robot Face Expression System')
        parser.add_argument('--api-url', default='http://localhost:8001', 
                          help='API server URL (default: http://localhost:8001)')
        parser.add_argument('--user-name', default='test_user',
                          help='User name for the conversation (default: test_user)')
        parser.add_argument('--expression', default='cute_neutral',
                          help='Initial expression (default: cute_neutral)')
        parser.add_argument('--fullscreen', action='store_true',
                          help='Run in fullscreen mode')
        parser.add_argument('--width', type=int, default=800,
                          help='Window width (default: 800)')
        parser.add_argument('--height', type=int, default=600,
                          help='Window height (default: 600)')
        
        args = parser.parse_args()
        
        # Set global expression
        global expp
        expp = args.expression
        
        # Create and run the enhanced robot face system
        logger.info("Starting Enhanced Robot Face System...")
        logger.info(f"API URL: {args.api_url}")
        logger.info(f"User: {args.user_name}")
        logger.info(f"Initial Expression: {args.expression}")
        
        system = EnhancedRobotFaceSystem(
            api_url=args.api_url,
            user_name=args.user_name,
            width=args.width,
            height=args.height
        )
        
        system.initialize()
        system.run()
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Enhanced Robot Face System shutting down...")
        pygame.quit()

if __name__ == "__main__":
    main()