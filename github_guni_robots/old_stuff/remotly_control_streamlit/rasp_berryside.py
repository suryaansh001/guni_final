#!/usr/bin/env python3
import requests
import time
import sounddevice as sd
import numpy as np
import wave
import os
import pygame
import cv2
import io
import json

# Configuration debug_temp_recording.wav
PC_IP = "<PC_IP>"  # Replace with your PC's IP address (e.g., "192.168.1.100")
COMPRE_FACE_URL = f"http://192.168.23.21:8000"
COMPRE_FACE_API_KEY = "your_compreface_key"  # Replace with your CompreFace API key
FASTAPI_URL = f"http://192.168.23.21:8001"
USER_NAME = "Unknown"  # Default user name
THREAD_ID = "dee5f5a9-0d14-49d6-a738-651ad6b1e869"
SAMPLE_RATE = 16000
DURATION = 5
CAMERA_INDEX = 0  # USB camera device index (usually 0 for /dev/video0)

def capture_face():
    """Capture an image using USB camera with OpenCV"""
    print("📸 Capturing face...")
    try:
        # Initialize USB camera
        cap = cv2.VideoCapture(CAMERA_INDEX)
        if not cap.isOpened():
            print("❌ Cannot open USB camera")
            return None

        # Set resolution (optional, adjust as needed)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Give camera time to warm up
        time.sleep(2)

        # Capture a single frame
        ret, frame = cap.read()
        if not ret:
            print("❌ Failed to capture image")
            cap.release()
            return None

        # Convert frame to JPEG
        ret, jpeg = cv2.imencode('.jpg', frame)
        if not ret:
            print("❌ Failed to encode image")
            cap.release()
            return None

        img_byte_arr = io.BytesIO(jpeg.tobytes())
        img_byte_arr.seek(0)

        # Release camera
        cap.release()
        print("✅ Face captured.")
        return img_byte_arr
    except Exception as e:
        print(f"❌ Camera error: {e}")
        return None

def recognize_face(image_data):
    """Send image to CompreFace for recognition"""
    if not image_data:
        return None
    files = {"file": ("image.jpg", image_data, "image/jpeg")}
    headers = {"x-api-key": COMPRE_FACE_API_KEY}
    try:
        response = requests.post(
            f"{COMPRE_FACE_URL}/api/v1/recognition/recognize",
            headers=headers,
            files=files
        )
        result = response.json()
        if not result.get("result"):
            print("⚠️ No face recognized.")
            return None
        subject_name = result["result"][0]["subjects"][0]["subject"]
        print(f"✅ Face recognized: {subject_name}")
        return subject_name
    except Exception as e:
        print(f"❌ CompreFace error: {e}")
        return None

def set_user_name(subject_name: str):
    """Send subject name to FastAPI"""
    try:
        response = requests.post(
            f"{FASTAPI_URL}/receive-subject",
            json={"subject": subject_name}
        )
        if response.status_code == 200:
            print(f"✅ Sent to FastAPI: {response.json()['message']}")
            return True
        else:
            print(f"❌ Failed to send to FastAPI: {response.text}")
            return False
    except Exception as e:
        print(f"❌ FastAPI error: {e}")
        return False

def generate_welcome_message(user_name: str):
    """Generate and save welcome message audio using FastAPI's TTS"""
    welcome_text = f"Hey {user_name}, welcome!"
    try:
        response = requests.get(
            f"{FASTAPI_URL}/test-tts",
            params={"text": welcome_text, "emotion": "positive"}
        )
        if response.status_code == 200:
            out_file = "welcome.wav"
            with open(out_file, "wb") as f:
                f.write(response.content)
            print(f"✅ Welcome message generated: {welcome_text}")
            return out_file
        else:
            print(f"❌ TTS error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ TTS generation error: {e}")
        return None

def play_audio(file_path):
    """Play audio file"""
    if not os.path.exists(file_path):
        print(f"❌ Audio file not found: {file_path}")
        return
    print("🔊 Playing audio...")
    pygame.mixer.init()
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    pygame.mixer.quit()

def record_audio(file_name="temp.wav", duration=DURATION, sample_rate=SAMPLE_RATE):
    """Record audio from microphone"""
    print("🎙️ Recording... (Speak your message, e.g., 'What all do you know about me?')")
    recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()
    with wave.open(file_name, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(recording.tobytes())
    print("✅ Audio recorded.")
    return file_name

def process_audio(audio_path, user_name, thread_id):
    """Send audio to FastAPI and process response"""
    with open(audio_path, "rb") as audio_file:
        try:
            response = requests.post(
                f"{FASTAPI_URL}/process-audio",
                files={"audio": ("audio.wav", audio_file, "audio/wav")},
                data={"user_name": user_name, "thread_id": thread_id}
            )
            if response.status_code == 200:
                print("✅ API Success")
                print(f"Transcription: {response.headers.get('X-Transcription', 'N/A')}")
                print(f"Emotion: {response.headers.get('X-Emotion', 'N/A')}")
                print(f"Response: {response.headers.get('X-Response', 'N/A')}")
                print(f"Summary: {response.headers.get('X-Summary', 'N/A')}")
                if "tts_error" not in response.headers:
                    out_file = f"response_{int(time.time())}.wav"
                    with open(out_file, "wb") as f:
                        f.write(response.content)
                    play_audio(out_file)
                    try:
                        os.unlink(out_file)
                        print(f"🗑️ Cleaned up response file: {out_file}")
                    except Exception as e:
                        print(f"❌ Cleanup error: {e}")
                else:
                    print(f"❌ TTS Error: {response.json().get('tts_error')}")
            else:
                print(f"❌ Request failed: {response.text}")
        except Exception as e:
            print(f"❌ Audio processing error: {e}")
        finally:
            try:
                os.unlink(audio_path)
                print(f"🗑️ Cleaned up temp file: {audio_path}")
            except Exception as e:
                print(f"❌ Cleanup error: {e}")

def main():
    """Main function to run the voice assistant on Raspberry Pi"""
    print("🚀 Starting Voice Assistant on Raspberry Pi")
    
    # Step 1: Capture and recognize face
    image_data = capture_face()
    user_name = recognize_face(image_data)
    if not user_name:
        print("🛑 No user recognized. Exiting.")
        return
    global USER_NAME
    USER_NAME = user_name

    # Step 2: Send user name to FastAPI
    if not set_user_name(user_name):
        print("🛑 Failed to set user name in FastAPI. Exiting.")
        return

    # Step 3: Play welcome message
    welcome_audio = generate_welcome_message(user_name)
    if welcome_audio:
        play_audio(welcome_audio)
        try:
            os.unlink(welcome_audio)
            print(f"🗑️ Cleaned up welcome file: {welcome_audio}")
        except Exception as e:
            print(f"❌ Cleanup error: {e}")

    # Step 4: Start voice interaction
    print("\n📢 Starting voice interaction")
    print(f"ℹ️ User: {user_name}, Thread ID: {THREAD_ID}")
    while True:
        input("Press ENTER to record your message...")
        wav_file = record_audio()
        process_audio(wav_file, user_name, THREAD_ID)
        print("\n---\n")
        continue_prompt = input("Continue interaction? (y/n): ").lower()
        if continue_prompt != 'y':
            print("🛑 Exiting.")
            break

if __name__ == "__main__":
    main()