#!/usr/bin/env python3
"""
Test script for the Voice Assistant FastAPI with LangGraph
Tests /health, /process-audio, /user-summary, and /summarize-session endpoints
"""

import requests
import os
from datetime import datetime
import time

API_URL = "http://0.0.0.0:8000/process-audio"
HEALTH_URL = "http://0.0.0.0:8000/health"
USER_SUMMARY_URL = "http://0.0.0.0:8000/user-summary/{}"
SUMMARIZE_SESSION_URL = "http://0.0.0.0:8000/summarize-session/{}"
TEST_AUDIO_PATH = "trylang.wav"  # Test audio file
USER_NAME = "test_user"  # Used as thread_id for conversation tracking

def test_health_check():
    """Test the /health endpoint"""
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        if response.status_code == 200:
            print("\nHealth Check:")
            print(response.json())
        else:
            print(f"Health check failed with status code {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error during health check: {e}")

def test_process_audio():
    """Test the /process-audio endpoint with LangGraph conversation history"""
    if not os.path.exists(TEST_AUDIO_PATH):
        print(f"Error: Audio file {TEST_AUDIO_PATH} not found")
        return None

    files = {"audio": (TEST_AUDIO_PATH, open(TEST_AUDIO_PATH, "rb"), "audio/wav")}
    data = {"user_name": USER_NAME}
    session_id = None

    try:
        print(f"\nSending audio processing request to {API_URL} for user: {USER_NAME}...")
        response = requests.post(API_URL, files=files, data=data, stream=True, timeout=30)

        if response.status_code == 200:
            print("Audio processing request successful!")
            print("\nResponse Headers:")
            print(f"X-User: {response.headers.get('X-User')}")
            print(f"X-Transcription: {response.headers.get('X-Transcription')}")
            print(f"X-Emotion: {response.headers.get('X-Emotion')}")
            print(f"X-Response: {response.headers.get('X-Response')}")
            print(f"X-Session-ID: {response.headers.get('X-Session-ID')}")

            session_id = response.headers.get('X-Session-ID')
            output_file = f"response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"\nResponse audio saved to {output_file}")
        else:
            print(f"Error: Received status code {response.status_code}")
            print(f"Response: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"Error during audio processing request: {e}")
    finally:
        files["audio"][1].close()

    return session_id

def test_user_summary():
    """Test the /user-summary endpoint"""
    try:
        url = USER_SUMMARY_URL.format(USER_NAME)
        print(f"\nSending user summary request to {url}...")
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print("User Summary Request successful!")
            print(response.json())
        else:
            print(f"User summary failed with status code {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error during user summary request: {e}")

def test_summarize_session(session_id: str):
    """Test the /summarize-session endpoint"""
    if not session_id:
        print("\nSkipping summarize-session test: No valid session ID")
        return
    try:
        url = SUMMARIZE_SESSION_URL.format(session_id)
        print(f"\nSending summarize session request to {url}...")
        response = requests.post(url, timeout=10)
        if response.status_code == 200:
            print("Summarize Session Request successful!")
            print(response.json())
        else:
            print(f"Summarize session failed with status code {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error during summarize session request: {e}")

def test_tts():
    """Test the /test-tts endpoint"""
    try:
        url = "http://0.0.0.0:8000/test-tts"
        data = {
            "text": "Hello, this is a test of the text-to-speech functionality!",
            "emotion": "neutral"
        }
        print(f"\nSending TTS test request to {url}...")
        response = requests.post(url, data=data, stream=True, timeout=10)
        if response.status_code == 200:
            print("TTS Request successful!")
            output_file = f"tts_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"TTS audio saved to {output_file}")
        else:
            print(f"TTS test failed with status code {response.status_code}")
            print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Error during TTS test request: {e}")

if __name__ == "__main__":
    print("Starting Voice Assistant API tests...")
    test_health_check()
    time.sleep(1)  # Allow server to stabilize
    session_id = test_process_audio()
    time.sleep(1)
    test_user_summary()
    if session_id:
        test_summarize_session(session_id)
    time.sleep(1)
    test_tts()
    print("\nTests completed.")