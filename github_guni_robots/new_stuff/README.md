# New Stuff - Current Implementation

## Overview

This folder contains the **production-ready** and **finalized** implementations of the GUNI Robot System. These are the components that should be used for deployment and further development.

## Components

### 🤖 Raspberry Pi Side Code (`raspberry_pi_side_code/`)

The complete robot face client that runs on Raspberry Pi hardware.

#### Main Files:
- **`talk.py`** - Complete robot face application with voice interaction
  - 20+ animated facial expressions using OpenGL
  - Real-time voice recognition and AI conversation
  - Text overlay system for displaying AI responses
  - Interactive controls (space, escape, mouse clicks)
  - Auto-conversation mode with sleep functionality
  - Breathing animations and smooth transitions
  
- **`mqtt_client.py`** - MQTT connectivity module (currently placeholder)
  - Designed for IoT integration
  - Future: Remote control and monitoring capabilities

- **`README_RASPBERRY_PI.md`** - Comprehensive setup and usage guide
  - Hardware requirements and system dependencies
  - Step-by-step installation instructions
  - Troubleshooting for audio, display, and network issues
  - Performance optimization tips
  - Auto-start configuration

#### Key Features:
✅ **Voice Interaction**: Real-time speech recognition and AI responses  
✅ **Expressive Face**: 20+ emotions with smooth OpenGL animations  
✅ **Text Display**: Word-wrapped text overlay with fade animations  
✅ **Audio Processing**: Voice activity detection and audio playback  
✅ **Sleep Mode**: Automatic power management  
✅ **Debug Mode**: Development and troubleshooting tools  

### 🖥️ Server Side API (`server_side_api/`)

The FastAPI-based server that powers the robot's AI capabilities.

#### Main Files:
- **`server.py`** - Complete API server (1830+ lines)
  - FastAPI web server with CORS support
  - Groq AI integration for intelligent conversations
  - ElevenLabs text-to-speech with multiple voice options
  - SQLite database for conversation history
  - User authentication and management
  - MQTT broker integration
  - File upload and audio processing
  - Expression management API
  
- **`setup_and_run_server.bat`** - Windows automated setup script
  - Creates virtual environment
  - Installs all dependencies
  - Runs the server automatically

- **`README_SERVER_SETUP.md`** - Server configuration guide
  - Quick setup instructions for Windows/Linux/Mac
  - Manual setup procedures
  - Dependency management
  - Environment variable configuration

#### Key Features:
✅ **AI Conversation**: Groq-powered intelligent responses with context  
✅ **Voice Synthesis**: ElevenLabs integration with multiple voice options  
✅ **Data Persistence**: SQLite database for conversation history  
✅ **User Management**: Authentication and user session handling  
✅ **MQTT Integration**: IoT messaging and device communication  
✅ **File Processing**: Audio upload and processing capabilities  
✅ **Expression API**: Robot emotion and animation control  
✅ **Easy Deployment**: Automated setup scripts for quick installation  

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        New Stuff Architecture                   │
└─────────────────────────────────────────────────────────────────┘

    Raspberry Pi Side                         Server Side
┌─────────────────────────┐              ┌─────────────────────────┐
│       talk.py           │◄─── HTTP ────►│       server.py         │
│                         │              │                         │
│ ┌─────────────────────┐ │              │ ┌─────────────────────┐ │
│ │   Voice Input       │ │              │ │   FastAPI Server    │ │
│ │   (PyAudio)         │ │              │ │   (Port 8001)       │ │
│ └─────────────────────┘ │              │ └─────────────────────┘ │
│                         │              │                         │
│ ┌─────────────────────┐ │              │ ┌─────────────────────┐ │
│ │   Robot Face        │ │              │ │   AI Processing     │ │
│ │   (OpenGL/PyGame)   │ │              │ │   (Groq)            │ │
│ └─────────────────────┘ │              │ └─────────────────────┘ │
│                         │              │                         │
│ ┌─────────────────────┐ │              │ ┌─────────────────────┐ │
│ │   Text Display      │ │              │ │   Text-to-Speech    │ │
│ │   (Word Wrapping)   │ │              │ │   (ElevenLabs)      │ │
│ └─────────────────────┘ │              │ └─────────────────────┘ │
│                         │              │                         │
│ ┌─────────────────────┐ │              │ ┌─────────────────────┐ │
│ │   Audio Output      │ │              │ │   SQLite Database   │ │
│ │   (Speakers)        │ │              │ │   (Conversations)   │ │
│ └─────────────────────┘ │              │ └─────────────────────┘ │
└─────────────────────────┘              └─────────────────────────┘
            │                                        │
            └──────────── MQTT (Future) ─────────────┘
```

## Installation Quick Start

### 1. Server Setup (Required First)
```bash
cd server_side_api/

# Windows
setup_and_run_server.bat

# Linux/Mac
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn groq elevenlabs python-dotenv paho-mqtt sqlite3 pyttsx3 requests
python server.py
```

### 2. Raspberry Pi Setup
```bash
cd raspberry_pi_side_code/

# Install system dependencies (see README_RASPBERRY_PI.md for full list)
sudo apt update && sudo apt install python3-pip python3-venv portaudio19-dev

# Create virtual environment
python3 -m venv robot_env
source robot_env/bin/activate

# Install Python packages
pip install pygame PyOpenGL pyaudio requests numpy Pillow opencv-python

# Configure server URL in talk.py (line ~30)
# SERVER_URL = "http://YOUR_SERVER_IP:8001"

# Run the robot face
python3 talk.py
```

## Configuration

### Environment Variables (.env file for server)
```env
GROQ_API_KEY=your_groq_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
DATABASE_PATH=voice_assistant_enhanced.db
```

### Key Configuration Points

1. **Server URL**: Update in `talk.py` to point to your server
2. **API Keys**: Set up Groq and ElevenLabs keys in server environment
3. **Audio Devices**: Configure microphone and speakers on Raspberry Pi
4. **Display Settings**: Adjust resolution and graphics settings for your display
5. **MQTT Settings**: Configure broker connection for IoT features

## Features Comparison with Old Stuff

| Feature | New Stuff Status | Old Stuff Status |
|---------|-----------------|------------------|
| Voice Recognition | ✅ Production Ready | 🔄 Experimental |
| AI Conversation | ✅ Groq Integration | 🔄 Basic/Limited |
| Facial Expressions | ✅ 20+ OpenGL Animations | 🔄 LCD/Static |
| Text-to-Speech | ✅ ElevenLabs Premium | 🔄 Basic TTS |
| User Interface | ✅ Interactive Controls | 🔄 Command Line |
| Database | ✅ SQLite with History | ❌ None |
| MQTT/IoT | ✅ Ready for Integration | ❌ Not Implemented |
| Setup Scripts | ✅ Automated Installation | ❌ Manual Only |
| Documentation | ✅ Comprehensive Guides | 🔄 Basic |
| Error Handling | ✅ Robust Error Management | 🔄 Limited |

## Next Steps for Development

### Immediate Priorities:
1. **MQTT Implementation**: Complete the `mqtt_client.py` functionality
2. **Web Integration**: Connect with the website component
3. **Expression Library**: Expand the facial expression system
4. **Voice Training**: Improve voice recognition accuracy

### Future Enhancements:
1. **Computer Vision**: Integrate face recognition and tracking
2. **Mobile App**: Develop companion mobile application
3. **Cloud Integration**: Add cloud-based conversation storage
4. **Multi-Robot**: Support for multiple robot instances

## Testing

### Unit Testing:
- Test individual components (voice, expressions, API endpoints)
- Verify audio input/output functionality
- Check network connectivity and API responses

### Integration Testing:
- Test full conversation flow
- Verify expression synchronization with speech
- Test error recovery and reconnection

### Hardware Testing:
- Test on actual Raspberry Pi hardware
- Verify performance with different audio devices
- Test display rendering on various screen sizes

## Performance Considerations

### Raspberry Pi Optimization:
- GPU memory split: 128MB or 256MB
- Audio buffer sizes: Adjust for latency vs. quality
- Network timeout settings: Balance responsiveness vs. reliability
- Expression animation frequency: Optimize for smooth playback

### Server Optimization:
- Database connection pooling
- API response caching
- Audio processing queue management
- Resource usage monitoring

## Troubleshooting

Common issues and solutions are documented in:
- `raspberry_pi_side_code/README_RASPBERRY_PI.md` - Pi-specific issues
- `server_side_api/README_SERVER_SETUP.md` - Server-specific issues

### Quick Fixes:
1. **No audio**: Check ALSA/PulseAudio configuration
2. **Display issues**: Verify OpenGL drivers and X11 setup
3. **Network errors**: Check server URL and firewall settings
4. **API failures**: Verify API keys and internet connectivity

## Contributing

When working with the new stuff:
1. **Test thoroughly** on actual hardware before committing
2. **Update documentation** for any configuration changes
3. **Maintain backwards compatibility** when possible
4. **Follow the existing code structure** and naming conventions
5. **Add comprehensive error handling** for production stability

---

**Status**: Production Ready  
**Last Updated**: July 1, 2025  
**Recommended for**: Deployment, Further Development, Production Use  
**Hardware Tested**: Raspberry Pi 4, Various Audio Devices, HDMI Displays
