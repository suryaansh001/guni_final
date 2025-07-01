# GUNI Robot Project

## Overview

The GUNI Robot Project is a comprehensive AI-powered robotic system developed for Ganpat University (GUNI). This project combines voice interaction, facial expressions, web interfaces, and IoT capabilities to create an intelligent assistant robot for educational and interactive purposes.

## Project Structure

```
gunni/
├── LICENSE                           # Main project license
├── README.md                        # This file - main project documentation
└── github_guni_robots/             # Core robot system
    ├── LICENSE                      # Robot system license
    ├── README.md                   # Robot system overview
    ├── new_stuff/                  # ✅ CURRENT/FINAL IMPLEMENTATIONS
    │   ├── README.md               # New features documentation
    │   ├── raspberry_pi_side_code/ # Raspberry Pi client code
    │   └── server_side_api/        # API server for voice processing
    ├── old_stuff/                  # 🔄 PREVIOUS/EXPERIMENTAL WORK
    │   ├── README.md               # Legacy code documentation
    │   ├── Audio_LangGraph_pipeline/
    │   ├── emotion_from_facial_expressions/
    │   ├── emotions_displayed_on_lcd/
    │   ├── raspberry_pi_side_code/
    │   └── remotly_control_streamlit/
    └── website/                    # Next.js web interface
        ├── README.md               # Website documentation
        ├── package.json            # Dependencies
        └── src/                    # Source code
```

## Key Components

### 🤖 Robot Face System (`new_stuff/`)
- **Raspberry Pi Client**: Real-time animated robot face with expressions
- **API Server**: Voice processing, AI conversation, and expression management
- **Features**: Voice recognition, AI responses, animated expressions, MQTT integration

### 🌐 Web Interface (`website/`)
- **Next.js Application**: Modern web dashboard and control interface
- **Authentication**: Clerk-based user management
- **Features**: Admin panel, user dashboard, robot monitoring

### 📚 Legacy Code (`old_stuff/`)
- Previous implementations and experimental features
- Emotion detection systems
- Alternative audio processing pipelines
- LCD display experiments

## Quick Start

### 1. Set Up the API Server
```bash
cd github_guni_robots/new_stuff/server_side_api/
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python server.py
```

### 2. Set Up the Raspberry Pi Client
```bash
cd github_guni_robots/new_stuff/raspberry_pi_side_code/
python -m venv robot_env
source robot_env/bin/activate
pip install pygame PyOpenGL pyaudio requests numpy Pillow opencv-python
python talk.py
```

### 3. Set Up the Web Interface
```bash
cd github_guni_robots/website/
npm install
npm run dev
```

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Interface │    │   API Server     │    │ Raspberry Pi    │
│   (Next.js)     │◄──►│   (FastAPI)      │◄──►│ Robot Face      │
│                 │    │                  │    │ (PyGame/OpenGL) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
    ┌────▼────┐              ┌───▼────┐              ┌───▼────┐
    │ User    │              │ AI     │              │ Audio  │
    │ Auth    │              │ Models │              │ I/O    │
    │ (Clerk) │              │ (Groq) │              │ System │
    └─────────┘              └────────┘              └────────┘
```

## Features

### Current Implementation (`new_stuff/`)
- ✅ Real-time voice interaction
- ✅ AI-powered conversations with context memory
- ✅ 20+ animated facial expressions
- ✅ Text-to-speech with multiple voice options
- ✅ Web-based control interface
- ✅ MQTT integration for IoT connectivity
- ✅ User authentication and management

### Legacy Features (`old_stuff/`)
- 🔄 Emotion detection from facial expressions
- 🔄 LCD display animations
- 🔄 LangGraph-based conversation pipelines
- 🔄 Streamlit remote control interfaces
- 🔄 Alternative audio processing methods

## Technology Stack

### Backend
- **FastAPI**: High-performance API server
- **Groq**: AI language model integration
- **ElevenLabs**: Advanced text-to-speech
- **SQLite**: Local conversation storage
- **MQTT**: IoT messaging protocol

### Frontend
- **Next.js 15**: Modern React framework
- **Clerk**: Authentication and user management
- **Tailwind CSS**: Utility-first styling
- **TypeScript**: Type-safe development

### Hardware/Embedded
- **Raspberry Pi**: Main computing platform
- **PyGame/OpenGL**: Real-time graphics rendering
- **PyAudio**: Audio input/output handling
- **OpenCV**: Computer vision capabilities

## Documentation

- [`new_stuff/README.md`](github_guni_robots/new_stuff/README.md) - Current implementation details
- [`old_stuff/README.md`](github_guni_robots/old_stuff/README.md) - Legacy code documentation
- [`website/README.md`](github_guni_robots/website/README.md) - Web interface setup
- [`new_stuff/raspberry_pi_side_code/README_RASPBERRY_PI.md`](github_guni_robots/new_stuff/raspberry_pi_side_code/README_RASPBERRY_PI.md) - Raspberry Pi setup guide
- [`new_stuff/server_side_api/README_SERVER_SETUP.md`](github_guni_robots/new_stuff/server_side_api/README_SERVER_SETUP.md) - Server setup guide

## Getting Help

1. Check the specific README files for each component
2. Review the troubleshooting sections in component documentation
3. Ensure all dependencies are properly installed
4. Verify hardware connections and configurations

## License

This project is licensed under the terms specified in the LICENSE files.

## About GUNI

Ganpat University (GUNI) is a prestigious educational institution located in Gujarat, India, known for innovation in engineering, technology, and research. This robot project represents the university's commitment to advancing AI and robotics education.

---

**Project Status**: Active Development  
**Last Updated**: July 1, 2025  
**Maintained by**: GUNI Robotics Team