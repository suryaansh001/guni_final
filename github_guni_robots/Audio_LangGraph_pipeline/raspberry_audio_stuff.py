# #!/usr/bin/env python3
# """
# Raspberry Pi Audio Recording Client (Adapted for PC)
# Records audio continuously and sends to FastAPI server when silence detected
# """

# import pyaudio
# import wave
# import numpy as np
# import requests
# import time
# import os
# import pygame

# class AudioRecorder:
#     def __init__(self, api_url="http://localhost:8000", user_name="test_user", input_device_index=None):
#         # Audio configuration
#         self.CHUNK = 1024
#         self.FORMAT = pyaudio.paInt16
#         self.CHANNELS = 1
#         self.RATE = 16000
#         self.SILENCE_THRESHOLD = 500  # Adjust based on your environment
#         self.SILENCE_DURATION = 5.0  # 5 seconds of silence
#         self.MIN_RECORDING_DURATION = 1.0  # Minimum 1 second recording
        
#         # API configuration
#         self.api_url = api_url
#         self.process_endpoint = f"{api_url}/process-audio"
#         self.user_name = user_name
#         self.input_device_index = input_device_index
        
#         # Recording state
#         self.is_recording = False
#         self.silence_start = None
        
#         # Initialize PyAudio
#         self.audio = pyaudio.PyAudio()
        
#     def get_rms(self, data):
#         """Calculate RMS (Root Mean Square) of audio data"""
#         if len(data) == 0 or np.any(np.isnan(data)) or np.any(np.isinf(data)):
#             return 0.0
#         return np.sqrt(np.mean(np.square(data.astype(np.float64))))
    
#     def is_silent(self, data):
#         """Check if audio data is silent"""
#         rms = self.get_rms(data)
#         return rms < self.SILENCE_THRESHOLD
    
#     def save_audio_to_file(self, frames, filename="temp_recording.wav"):
#         """Save audio frames to WAV file"""
#         wf = wave.open(filename, 'wb')
#         wf.setnchannels(self.CHANNELS)
#         wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
#         wf.setframerate(self.RATE)
#         wf.writeframes(b''.join(frames))
#         wf.close()
#         return filename
    
#     def send_audio_to_api(self, audio_file):
#         """Send audio file to FastAPI server, print response text, and play audio"""
#         print(f"🌐 Sending audio to server: {audio_file}")
#         try:
#             with open(audio_file, 'rb') as f:
#                 files = {'audio': (audio_file, f, 'audio/wav')}
#                 data = {'user_name': self.user_name}
#                 response = requests.post(self.process_endpoint, files=files, data=data, timeout=120)
            
#             if response.status_code == 200:
#                 # Check content type of response
#                 content_type = response.headers.get('Content-Type', '')
                
#                 # Print response metadata from headers
#                 transcription = response.headers.get('X-Transcription', '')
#                 ai_response = response.headers.get('X-Response', '')
#                 emotion = response.headers.get('X-Emotion', '')
#                 session_id = response.headers.get('X-Session-ID', '')
                
#                 if transcription:
#                     print(f"📜 Transcription: {transcription}")
#                 if ai_response:
#                     print(f"📜 AI Response: {ai_response}")
#                 if emotion:
#                     print(f"😊 Emotion: {emotion}")
#                 if session_id:
#                     print(f"🔢 Session ID: {session_id}")
                
#                 # Handle audio/mpeg response
#                 if 'audio/mpeg' in content_type:
#                     response_audio = response.content
#                     response_file = f"response_{int(time.time())}.mp3"
                    
#                     # Save response audio
#                     with open(response_file, 'wb') as f:
#                         f.write(response_audio)
                    
#                     print(f"✅ Response audio received and saved as: {response_file}")
                    
#                     # Play the response audio
#                     self.play_audio(response_file)
                    
#                     # Clean up response file
#                     os.remove(response_file)
#                 else:
#                     print(f"❌ Unexpected response format: {content_type}")
#             else:
#                 print(f"❌ API Error: {response.status_code} - {response.text}")
                
#         except requests.exceptions.RequestException as e:
#             print(f"❌ Network Error: {e}")
#         except Exception as e:
#             print(f"❌ Error: {e}")
#         finally:
#             # Clean up temporary file
#             if os.path.exists(audio_file):
#                 os.remove(audio_file)
    
#     def play_audio(self, filename):
#         """Play audio file through speakers using pygame"""
#         print(f"🎵 Playing response audio: {filename}")
#         try:
#             if os.path.exists(filename) and os.path.getsize(filename) > 0:
#                 pygame.mixer.init()
#                 pygame.mixer.music.load(filename)
#                 pygame.mixer.music.play()
#                 while pygame.mixer.music.get_busy():
#                     time.sleep(0.1)
#                 pygame.mixer.quit()
#                 print("✅ Playback completed")
#             else:
#                 print("❌ Playback Error: Audio file is missing or empty")
#         except Exception as e:
#             print(f"❌ Playback Error: {e}")
    
#     def start_recording(self):
#         """Start continuous audio recording"""
#         print("🎤 Starting audio recording...")
#         print("💡 Speak normally, I'll process your speech after 5 seconds of silence")
        
#         stream = self.audio.open(
#             format=self.FORMAT,
#             channels=self.CHANNELS,
#             rate=self.RATE,
#             input=True,
#             frames_per_buffer=self.CHUNK,
#             input_device_index=self.input_device_index
#         )
        
#         frames = []
#         recording_start = None
        
#         try:
#             while True:
#                 data = stream.read(self.CHUNK, exception_on_overflow=False)
#                 audio_data = np.frombuffer(data, dtype=np.int16)
                
#                 if not self.is_silent(audio_data):
#                     # Speech detected
#                     if not self.is_recording:
#                         print("🎙️ Recording started...")
#                         self.is_recording = True
#                         recording_start = time.time()
#                         frames = []
                    
#                     frames.append(data)
#                     self.silence_start = None
                    
#                 else:
#                     # Silence detected
#                     if self.is_recording:
#                         if self.silence_start is None:
#                             self.silence_start = time.time()
                        
#                         frames.append(data)  # Keep recording during silence
                        
#                         # Check if silence duration exceeded
#                         silence_duration = time.time() - self.silence_start
#                         if silence_duration >= self.SILENCE_DURATION:
#                             recording_duration = time.time() - recording_start
                            
#                             if recording_duration >= self.MIN_RECORDING_DURATION:
#                                 print("🔄 Processing audio...")
                                
#                                 # Save audio
#                                 audio_file = self.save_audio_to_file(frames)
                                
#                                 # Send to API
#                                 self.send_audio_to_api(audio_file)
                            
#                             # Reset recording state
#                             self.is_recording = False
#                             frames = []
#                             self.silence_start = None
#                             print("👂 Listening...")
                
#         except KeyboardInterrupt:
#             print("\n🛑 Recording stopped by user")
#         except Exception as e:
#             print(f"❌ Recording Error: {e}")
#         finally:
#             stream.stop_stream()
#             stream.close()
#             self.audio.terminate()

# def main():
#     # Configuration
#     API_URL = "http://localhost:8000"  # Server is on the same PC
#     USER_NAME = "test_user"  # Change to desired user name
#     INPUT_DEVICE_INDEX = None  # Set to your microphone's device index (e.g., 2)
    
#     # List audio devices to find microphone index
#     p = pyaudio.PyAudio()
#     print("Available audio devices:")
#     for i in range(p.get_device_count()):
#         print(p.get_device_info_by_index(i))
#     p.terminate()
    
#     recorder = AudioRecorder(api_url=API_URL, user_name=USER_NAME, input_device_index=INPUT_DEVICE_INDEX)
    
#     try:
#         recorder.start_recording()
#     except Exception as e:
#         print(f"❌ Error: {e}")

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
"""
Raspberry Pi Audio Recording Client
Records audio continuously and sends to FastAPI server when silence detected
"""
#!/usr/bin/env python3
"""
Raspberry Pi Audio Recording Client
Records audio continuously and sends to FastAPI server when silence detected
"""

import pyaudio
import wave
import numpy as np
import requests
import time
import os
import pygame
import shutil

class AudioRecorder:
    def __init__(self, api_url="http://192.168.23.21:8000", user_name="test_user", input_device_index=None):
        # Audio configuration
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.SILENCE_THRESHOLD = 500
        self.SILENCE_DURATION = 5.0
        self.MIN_RECORDING_DURATION = 1.0
        
        # API configuration
        self.api_url = api_url
        self.process_endpoint = f"{api_url}/process-audio"
        self.user_name = user_name"
        self.input_device_index = input_device_index
        
        # Recording state
        self.is_recording = False
        self.silence_start = None
        
        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()
        
    def get_rms(self, data):
        """Calculate RMS (Root Mean Square) of audio data"""
        if len(data) == 0 or np.any(np.isnan(data)) or np.any(np.isinf(data)):
            return 0.0
        return np.sqrt(np.mean(np.square(data.astype(np.float64))))
    
    def is_silent(self, data):
        """Determine if audio data is silent"""
        rms = self.get_rms(data)
        return rms < self.SILENCE_THRESHOLD
    
    def save_audio_to_file(self, frames, filename="temp_recording.wav"):
        """Save audio frames to WAV file"""
        wf = wave.open(filename, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        return filename
    
    def send_audio_to_api(self, audio_file):
        """Send audio file to FastAPI server, print response text, and play audio"""
        print(f"🌟 Sending audio to server: {audio_file}")
        debug_file = f"debug_{audio_file}"  # Debugging: Save a copy
        shutil.copy2(audio_file, debug_file)
        print(f"📝 Saved debug copy: {debug_file}")
        
        try:
            with open(audio_file, 'rb') as f:
                files = {'audio': (audio_file, f, 'audio/wav')}
                data = {'user_name': self.user_name}
                response = requests.post(
                    self.process_endpoint,
                    files=files,
                    data=data,
                    timeout=120,
                    max_retries=2  # Retry twice
                )
            
            # Print full response details
            print(f"📩 Response status: {response.status_code}")
            print(f"� Headers: {response.headers}")
            print(f"📜 Response text: {response.text}")
            
            if response.status_code == 200:
                # Check content type
                content_type = response.headers.get('Content-Type', '')
                
                # Print response metadata from headers
                transcription = response.headers.get('X-Transcription', '')
                ai_response = response.headers.get('X-Response', '')
                emotion = response.headers.get('X-Emotion', '')
                session_id = response.headers.get('X-Session-ID', '')
                
                if transcription:
                    print(f"📜 Transcription: {transcription}")
                if ai_response:
                    print(f"📜 Response: {ai_response}")
                if emotion:
                    print(f"😄 Emotion: {emotion}")
                if session_id:
                    print(f"🔢 Session ID: {session_id}")
                
                # Handle audio/mpeg response
                if 'audio/mpeg' in content_type:
                    response_audio = response.content
                    response_file = f"response_{int(time.time())}.mp3"
                    
                    # Save response audio
                    with open(response_file, 'wb') as f:
                        f.write(response_audio)
                    
                    print(f"✅ Response audio received and saved as: {response_file}")
                    
                    # Play the response audio
                    self.play_audio(response_file)
                    
                    # Clean up response file
                    os.remove(response_file)
                else:
                    print(f"❌ Unexpected response format: {content_type}")
            else:
                print(f"❌ API Error: {response.status_code} - {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network Error: {e}")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            # Clean up temporary file (keep debug copy)
            if os.path.exists(audio_file):
                os.remove(audio_file)
    
    def play_audio(self, filename):
        """Play audio file through speakers using pygame"""
        print(f"🎵 Playing response audio: {filename}")
        try:
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                pygame.mixer.init()
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.quit()
                print("✅ Playback completed")
            else:
                print("❌ Playback Error: Audio file is missing or empty")
        except Exception as e:
            print(f"❌ Playback Error: {e}")
    
    def start_recording(self):
        """Start continuous audio recording"""
        print("🎤 Starting audio recording...")
        print("💡 Speak normally, I'll process your speech after 5 seconds of silence")
        
        try:
            stream = self.audio.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                input_device_index=self.input_device_index
            )
        except Exception as e:
            print(f"❌ Audio Input Error: {e}")
            self.audio.terminate()
            return
        
        frames = []
        recording_start = None
        
        try:
            while True:
                data = stream.read(self.CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                if not self.is_silent(audio_data):
                    # Speech detected
                    if not self.is_recording:
                        print("🎙️ Recording started...")
                        self.is_recording = True
                        recording_start = time.time()
                        frames = []
                    
                    frames.append(data)
                    self.silence_start = None
                    
                else:
                    # Silence detected
                    if self.is_recording:
                        if self.silence_start is None:
                            self.silence_start = time.time()
                        
                        frames.append(data)  # Keep recording during silence
                        
                        # Check if silence duration exceeded
                        silence_duration = time.time() - self.silence_start
                        if silence_duration >= self.SILENCE_DURATION:
                            recording_duration = time.time() - recording_start
                            
                            if recording_duration >= self.MIN_RECORDING_DURATION:
                                print("🔄 Processing audio...")
                                
                                # Save audio
                                audio_file = self.save_audio_to_file(frames)
                                
                                # Send to API
                                self.send_audio_to_api(audio_file)
                            
                            # Reset recording state
                            self.is_recording = False
                            frames = []
                            self.silence_start = None
                            print("👂 Listening...")
                
        except KeyboardInterrupt:
            print("\n🛑 Recording stopped by user")
        except Exception as e:
            print(f"❌ Recording Error: {e}")
        finally:
            stream.stop_stream()
            stream.close()
            self.audio.terminate()

def main():
    # Configuration
    API_URL = "http://192.168.23.21:8000"  # FastAPI server IP
    USER_NAME = "test_user"  # Change to desired user name
    INPUT_DEVICE_INDEX = None  # Set to your microphone's device index (e.g., 2)
    
    # List audio devices to find microphone index
    p = pyaudio.PyAudio()
    print("Available audio devices:")
    for i in range(p.get_device_count()):
        print(p.get_device_info_by_index(i))
    p.terminate()
    
    recorder = AudioRecorder(api_url=API_URL, user_name=USER_NAME, input_device_index=INPUT_DEVICE_INDEX)
    
    try:
        recorder.start_recording()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()