# Raspberry Pi Robot Face Client Setup

## Overview

The `talking.py` script runs the robot face client on Raspberry Pi, displaying animated expressions and text overlays while communicating with the API server for voice conversations.

## Hardware Requirements

- Raspberry Pi 4 (recommended) or Raspberry Pi 3B+
- Display/Monitor connected via HDMI
- USB Microphone
- Speakers or headphones
- SD Card (32GB+ recommended)
- Stable internet connection

## Software Requirements

### System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install system libraries for audio, graphics, and networking
sudo apt install -y \
    portaudio19-dev \
    pulseaudio \
    alsa-utils \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    freeglut3-dev \
    libglfw3-dev \
    libglew-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    pkg-config \
    libjpeg-dev \
    libpng-dev \
    libtiff-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libgtk-3-dev \
    libcanberra-gtk-module \
    libcanberra-gtk3-module
```

### Python Dependencies

Create a virtual environment and install Python packages:

```bash
# Create virtual environment
python3 -m venv robot_env

# Activate virtual environment
source robot_env/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install pygame
pip install PyOpenGL
pip install pyaudio
pip install requests
pip install numpy
pip install Pillow
pip install opencv-python
```

### Alternative: Install from requirements file

If you have a `requirements.txt` file:

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Audio Setup

Test microphone and speakers:

```bash
# Test microphone recording
arecord -l  # List audio devices
arecord -D hw:1,0 -f cd test.wav  # Record test (Ctrl+C to stop)
aplay test.wav  # Play back test

# Test speakers
speaker-test -t wav -c 2
```

### 2. Display Setup

Ensure your display is properly configured:

```bash
# Check display resolution
xrandr

# If needed, configure in /boot/config.txt:
sudo nano /boot/config.txt
# Add/modify: hdmi_force_hotplug=1, hdmi_group=2, hdmi_mode=82
```

### 3. Server Connection

Edit the server URL in `talking.py` (around line 20-30):

```python
SERVER_URL = "http://YOUR_SERVER_IP:8001"  # Replace with your server IP
```

### 4. Expression Files

Ensure `enhanced_expressions.json` is in the same directory as `talking.py`.

## Running the Robot Face Client

### Basic Usage

```bash
# Navigate to the directory containing talking.py
cd /path/to/your/robot/files

# Activate virtual environment
source robot_env/bin/activate

# Run the robot face client
python3 talking.py
```

### Auto-start on Boot (Optional)

To automatically start the robot face on boot:

1. Create a service file:
```bash
sudo nano /etc/systemd/system/robot-face.service
```

2. Add the following content:
```ini
[Unit]
Description=Robot Face Client
After=network.target sound.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/robot
Environment=DISPLAY=:0
ExecStart=/home/pi/robot/robot_env/bin/python /home/pi/robot/talking.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

3. Enable and start the service:
```bash
sudo systemctl enable robot-face.service
sudo systemctl start robot-face.service
```

## Controls

- **Enter/Space**: Start conversation
- **Escape/Q**: Quit application
- **S**: Toggle sleep mode
- **T**: Test text display
- **D**: Toggle debug mode
- **Mouse Click**: Start conversation

## Features

### Expression System
- 20+ animated facial expressions loaded from `enhanced_expressions.json`
- Smooth transitions between expressions
- Breathing animation during idle state

### Text Overlay
- Real-time display of AI responses
- Word wrapping for long text
- Fade-out animation
- Unicode text support (converted to ASCII for display)

### Audio Processing
- Real-time speech recognition
- Voice activity detection
- Audio playback of AI responses
- Automatic volume adjustment

### Auto-Conversation Mode
- Continuous listening when active
- Automatic sleep mode for short inputs
- Smart conversation flow management

## File Structure

```
new_stuff/raspberry_pi_side_code/
├── README_RASPBERRY_PI.md       # This comprehensive setup guide
├── talk.py                      # 🔥 MAIN: Complete robot face application (2400+ lines)
│   ├── VoiceAssistantClient     # Voice processing and API communication
│   ├── RobotFace               # OpenGL-based facial expression system
│   ├── TextOverlay             # Real-time text display with word wrapping
│   ├── ExpressionManager       # 20+ animated facial expressions
│   ├── AudioManager            # Voice input/output handling
│   └── ConversationManager     # AI conversation flow control
└── mqtt_client.py              # 🔄 PLACEHOLDER: MQTT IoT connectivity (future feature)

Required Files (auto-generated/downloaded):
├── enhanced_expressions.json   # Expression configurations (loaded from server)
├── robot_env/                  # Python virtual environment
│   ├── bin/activate           # Environment activation script
│   └── lib/python3.x/         # Installed packages
└── audio_cache/               # Cached audio responses (created automatically)
```

### Main Application Components (`talk.py`)

#### Core Classes:
1. **VoiceAssistantClient** - API communication and voice processing
2. **RobotFace** - OpenGL rendering and expression management  
3. **TextOverlay** - Real-time text display system
4. **ExpressionManager** - Animation and expression control
5. **AudioManager** - Audio input/output handling
6. **ConversationManager** - AI conversation flow

#### Key Features:
- ✅ **Real-time Voice Recognition**: Continuous audio monitoring
- ✅ **AI Conversations**: Groq-powered intelligent responses
- ✅ **Animated Expressions**: 20+ OpenGL-rendered facial expressions
- ✅ **Text Display**: Word-wrapped, real-time text overlay
- ✅ **Audio Playback**: High-quality text-to-speech output
- ✅ **Interactive Controls**: Keyboard and mouse input handling
- ✅ **Sleep Mode**: Power-saving idle state with breathing animation
- ✅ **Debug Mode**: Development and troubleshooting tools

### Integration with Server

```
Raspberry Pi (talk.py) ←→ API Server (server.py) ←→ External Services
        │                       │                      │
    ┌───▼────┐              ┌───▼────┐              ┌───▼────┐
    │ Audio  │              │ Voice  │              │ Groq   │
    │ I/O    │              │ AI     │              │ AI     │
    └────────┘              │ API    │              └────────┘
        │                   └───▲────┘              ┌────────┐
    ┌───▼────┐                  │                   │Eleven  │
    │OpenGL  │              ┌───▼────┐              │Labs    │
    │Display │              │SQLite  │              │TTS     │
    └────────┘              │Database│              └────────┘
                           └────────┘
```

## Troubleshooting

### Audio Issues

1. **No microphone detected**:
   ```bash
   # List audio devices
   arecord -l
   # Set default device in ~/.asoundrc
   ```

2. **Audio permissions**:
   ```bash
   # Add user to audio group
   sudo usermod -a -G audio $USER
   # Logout and login again
   ```

3. **PulseAudio problems**:
   ```bash
   # Restart PulseAudio
   pulseaudio -k
   pulseaudio --start
   ```

### Display Issues

1. **OpenGL errors**:
   ```bash
   # Install additional graphics drivers
   sudo apt install mesa-utils
   glxinfo | grep OpenGL
   ```

2. **Display not showing**:
   ```bash
   # Check X11 forwarding (if using SSH)
   echo $DISPLAY
   xhost +local:
   ```

### Network Issues

1. **Cannot connect to server**:
   - Check server IP address in `talking.py`
   - Verify server is running: `curl http://SERVER_IP:8001/health`
   - Check firewall settings

2. **Slow response**:
   - Check internet connectivity
   - Verify server performance
   - Consider local server deployment

### Performance Issues

1. **Lag or stuttering**:
   ```bash
   # Increase GPU memory split
   sudo raspi-config
   # Advanced Options > Memory Split > 128 or 256
   ```

2. **High CPU usage**:
   - Lower display resolution
   - Reduce expression animation complexity
   - Close unnecessary background processes

### Python/Dependency Issues

1. **Import errors**:
   ```bash
   # Reinstall problematic packages
   pip uninstall package_name
   pip install package_name
   ```

2. **OpenGL issues**:
   ```bash
   # Install OpenGL development packages
   sudo apt install libgl1-mesa-dev libglu1-mesa-dev
   ```

3. **Audio library issues**:
   ```bash
   # Reinstall PyAudio with system dependencies
   sudo apt install portaudio19-dev
   pip uninstall pyaudio
   pip install pyaudio
   ```

## Performance Optimization

### For Raspberry Pi 4:
- Enable GPU acceleration
- Use faster SD card (Class 10, A2)
- Ensure adequate cooling
- Use external power supply (3A+)

### For Raspberry Pi 3:
- Reduce expression complexity
- Lower audio sample rate
- Use lightweight desktop environment

## Logs and Debugging

1. **Enable debug mode**: Press 'D' during runtime
2. **View system logs**: `journalctl -u robot-face.service -f`
3. **Check audio logs**: `pactl info`
4. **Monitor resources**: `htop` or `top`

## API Server Requirements

The Raspberry Pi client requires a compatible API server running with:
- Voice conversation endpoints
- Expression management
- Audio processing capabilities
- See `README_SERVER_SETUP.md` for server setup

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all dependencies are installed
3. Test individual components (audio, display, network)
4. Check server connectivity and logs

## Version Requirements

- Raspberry Pi OS: Bullseye or later
- Python: 3.8 or higher
- OpenGL: 2.1 or higher
- Audio: ALSA/PulseAudio support

Last updated: June 30, 2025
