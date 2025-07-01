# GUNI Robot System

## Overview

The GUNI Robot System is an intelligent, AI-powered robotic assistant designed for Ganpat University. It combines advanced voice interaction, expressive facial animations, and web-based management to create an engaging educational and interactive experience.

## System Components

### 🔥 Current Implementation (`new_stuff/`)
The production-ready robot system with all finalized features:

#### Raspberry Pi Robot Face (`raspberry_pi_side_code/`)
- **Main Script**: `talk.py` - Complete robot face with voice interaction
- **MQTT Client**: `mqtt_client.py` - IoT connectivity (placeholder)
- **Features**:
  - Real-time animated facial expressions (20+ emotions)
  - Voice recognition and AI conversation
  - Text-to-speech with multiple voice options
  - Interactive controls and sleep mode
  - OpenGL-based smooth animations

#### API Server (`server_side_api/`)
- **Main Server**: `server.py` - FastAPI-based voice processing server
- **Features**:
  - AI conversation with Groq language models
  - ElevenLabs text-to-speech integration
  - Local SQLite database for conversation storage
  - MQTT broker integration
  - User management and authentication
  - Expression management API

### 🔄 Legacy Code (`old_stuff/`)
Previous implementations and experimental features for reference:

- **Audio_LangGraph_pipeline/**: Alternative conversation processing
- **emotion_from_facial_expressions/**: Computer vision emotion detection
- **emotions_displayed_on_lcd/**: LCD-based emotion display system
- **raspberry_pi_side_code/**: Earlier Raspberry Pi implementations
- **remotly_control_streamlit/**: Streamlit-based remote control

### 🌐 Web Interface (`website/`)
Modern Next.js web application for robot management and monitoring:

- **Framework**: Next.js 15 with TypeScript
- **Authentication**: Clerk integration
- **Features**: Admin panel, user dashboard, robot control
- **Styling**: Tailwind CSS

## Quick Start Guide

### 1. API Server Setup
```bash
cd new_stuff/server_side_api/
# Windows: Run setup_and_run_server.bat
# Linux/Mac: Run setup_and_run_server.sh
# Or manually:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python server.py
```

### 2. Raspberry Pi Setup
```bash
cd new_stuff/raspberry_pi_side_code/
python -m venv robot_env
source robot_env/bin/activate
pip install pygame PyOpenGL pyaudio requests numpy Pillow opencv-python
python talk.py
```

### 3. Web Interface Setup
```bash
cd website/
npm install
npm run dev
```

## Architecture

```
    ┌─────────────────────────────────────────────────────────┐
    │                    GUNI Robot System                   │
    └─────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        │                           │                           │
┌───────▼────────┐         ┌────────▼────────┐         ┌────────▼────────┐
│  Web Interface │         │   API Server    │         │ Raspberry Pi    │
│   (Next.js)    │◄────────┤   (FastAPI)     │────────►│  Robot Face     │
│                │  HTTPS  │                 │  HTTP   │  (PyGame/GL)    │
│ • Admin Panel  │         │ • Voice AI      │         │ • Expressions   │
│ • User Dash    │         │ • TTS/STT       │         │ • Voice I/O     │
│ • Robot Control│         │ • User Mgmt     │         │ • Animations    │
└────────────────┘         │ • MQTT Broker   │         └─────────────────┘
                           └─────────────────┘
                                    │
                            ┌───────▼────────┐
                            │   External     │
                            │   Services     │
                            │ • Groq AI      │
                            │ • ElevenLabs   │
                            │ • SQLite DB    │
                            └────────────────┘
```

## Features Comparison

| Feature | New Stuff (Current) | Old Stuff (Legacy) |
|---------|--------------------|--------------------|
| Voice Interaction | ✅ Advanced AI with Groq | 🔄 Basic/Experimental |
| Facial Expressions | ✅ 20+ OpenGL animations | 🔄 LCD-based/Limited |
| Web Interface | ✅ Modern Next.js app | 🔄 Streamlit prototypes |
| User Management | ✅ Clerk authentication | ❌ Not implemented |
| Text-to-Speech | ✅ ElevenLabs integration | 🔄 Basic TTS |
| Conversation Memory | ✅ SQLite with context | 🔄 Limited/Experimental |
| MQTT Integration | ✅ Full IoT support | ❌ Not implemented |
| Auto-deployment | ✅ Setup scripts | ❌ Manual only |

## File Structure

```
github_guni_robots/
├── LICENSE                                 # Project license
├── README.md                              # This overview document
├── new_stuff/                             # 🔥 PRODUCTION CODE
│   ├── README.md                         # Current implementation docs
│   ├── raspberry_pi_side_code/           # Raspberry Pi client
│   │   ├── talk.py                       # Main robot face application
│   │   ├── mqtt_client.py                # MQTT connectivity
│   │   └── README_RASPBERRY_PI.md        # Setup and usage guide
│   └── server_side_api/                  # Voice processing server
│       ├── server.py                     # Main FastAPI server
│       ├── setup_and_run_server.bat      # Windows setup script
│       └── README_SERVER_SETUP.md        # Server configuration guide
├── old_stuff/                            # 🔄 LEGACY/EXPERIMENTAL
│   ├── README.md                         # Legacy code documentation
│   ├── Audio_LangGraph_pipeline/         # Alternative conversation AI
│   ├── emotion_from_facial_expressions/  # Computer vision emotions
│   ├── emotions_displayed_on_lcd/        # LCD emotion display
│   ├── raspberry_pi_side_code/           # Previous Pi implementations
│   └── remotly_control_streamlit/        # Streamlit control interfaces
└── website/                              # 🌐 WEB INTERFACE
    ├── README.md                         # Website documentation
    ├── package.json                      # Dependencies and scripts
    ├── next.config.ts                    # Next.js configuration
    ├── src/                              # Source code
    │   ├── app/                          # App router pages
    │   │   ├── (auth)/                   # Authentication pages
    │   │   ├── admin/                    # Admin dashboard
    │   │   └── user-dashboard/           # User interface
    │   └── components/                   # React components
    └── public/                           # Static assets
```

## Getting Started

1. **Choose Your Component**:
   - For the complete robot: Start with `new_stuff/`
   - For web interface: Go to `website/`
   - For research/reference: Check `old_stuff/`

2. **Follow Setup Guides**:
   - Server: [`new_stuff/server_side_api/README_SERVER_SETUP.md`](new_stuff/server_side_api/README_SERVER_SETUP.md)
   - Raspberry Pi: [`new_stuff/raspberry_pi_side_code/README_RASPBERRY_PI.md`](new_stuff/raspberry_pi_side_code/README_RASPBERRY_PI.md)
   - Website: [`website/README.md`](website/README.md)

3. **Environment Configuration**:
   - Set up API keys for Groq and ElevenLabs
   - Configure MQTT broker settings
   - Update server URLs and network settings

## Hardware Requirements

### Minimum Setup
- Raspberry Pi 4 (2GB RAM)
- USB microphone
- Speakers/headphones
- HDMI display
- Server machine (can be same as Pi for testing)

### Recommended Setup
- Raspberry Pi 4 (4GB+ RAM)
- High-quality USB microphone
- Good speakers with amplifier
- Touch display (7" or larger)
- Dedicated server machine
- Stable network connection

## Technology Stack

- **Backend**: FastAPI, SQLite, MQTT, Groq AI, ElevenLabs
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, Clerk
- **Embedded**: Python, PyGame, OpenGL, PyAudio, OpenCV
- **DevOps**: Virtual environments, automated setup scripts

## Contributing

When adding new features:
1. Develop in `new_stuff/` for production code
2. Keep experimental work in `old_stuff/` for reference
3. Update relevant README files
4. Test on actual hardware before committing
5. Document configuration and setup requirements

## Support

- Check component-specific README files for detailed setup
- Review troubleshooting sections for common issues
- Ensure all dependencies and hardware are properly configured
- Test individual components before full system integration

---

**Project Status**: Production Ready  
**Last Updated**: July 1, 2025  
**Institution**: Ganpat University (GUNI)  
**License**: See LICENSE file