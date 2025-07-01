# Robot Face API Server Setup

## Quick Setup

### For Windows:
1. Place your `server.py` file in this folder
2. Double-click `setup_and_run_server.bat`
3. The script will automatically:
   - Create a virtual environment
   - Install dependencies
   - Run the server

### For Linux/Mac:
1. Place your `server.py` file in this folder
2. Run in terminal:
   ```bash
   ./setup_and_run_server.sh
   ```
3. The script will automatically:
   - Create a virtual environment
   - Install dependencies  
   - Run the server

## Manual Setup (Alternative)

If the automated scripts don't work, you can set up manually:

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python server.py
```

## Requirements

- Python 3.8 or higher
- Internet connection (for installing packages)
- Your `server.py` file in the same directory

## API Keys Setup

### Method 1: Environment Variables (.env file) - Recommended

Create a `.env` file in the same directory as `server.py`:

```env
# AI Service API Keys
GROQ_API_KEY=your_groq_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Admin Access
ADMIN_API_KEY=guni-admin-demo-key

# MQTT Configuration (optional)
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
```

### Method 2: Database Management

If you don't set up a `.env` file, you can manage API keys through the database:

1. **Access Admin Panel**: Use the web interface at the admin section
2. **Admin Key**: When prompted for admin access, enter: `guni-admin-demo-key`
3. **Add API Keys**: Navigate to API Keys section and add your keys:
   - **Groq API Key**: For AI conversation processing
   - **ElevenLabs API Key**: For text-to-speech generation
   - **Hugging Face API Key**: For speech-to-text processing

### Getting API Keys

#### Groq API Key:
1. Visit [console.groq.com](https://console.groq.com)
2. Create an account and get your API key
3. Free tier available with good limits

#### ElevenLabs API Key:
1. Visit [elevenlabs.io](https://elevenlabs.io)
2. Sign up for an account
3. Get your API key from the profile section
4. Free tier includes 10,000 characters/month

#### Hugging Face API Key:
1. Visit [huggingface.co](https://huggingface.co)
2. Create an account
3. Go to Settings → Access Tokens
4. Create a new token for API access
5. Free tier available for most models

## Server Access

Once running, the server will be available at:
- **Local**: http://localhost:8001
- **Network**: http://YOUR_IP_ADDRESS:8001

### API Endpoints
- **Health Check**: `GET /health`
- **Process Audio**: `POST /process_audio`
- **Available Expressions**: `GET /available_expressions`
- **Admin Panel**: Various `/admin/*` endpoints

### Admin Access for Website

When using the web interface admin panel:

1. **Admin API Key**: `guni-admin-demo-key`
2. **Access**: Use this key in the website's admin section
3. **Features**: Manage users, API keys, conversations, and robot control

**Important**: Change the default admin key in production by setting `ADMIN_API_KEY` environment variable.

## Stopping the Server

Press `Ctrl+C` in the terminal to stop the server.

## Troubleshooting

### Common Issues:

1. **Python not found**: Make sure Python is installed and added to PATH
2. **Permission denied**: On Linux/Mac, make sure the script is executable: `chmod +x setup_and_run_server.sh`
3. **Dependencies fail**: Try updating pip: `python -m pip install --upgrade pip`
4. **Server doesn't start**: Check that `server.py` exists in the same folder
5. **Port already in use**: Stop any other processes using port 8001

### API Key Issues:

6. **"API key missing" errors**: 
   - Check your `.env` file is in the same directory as `server.py`
   - Verify API key format (no extra spaces or quotes)
   - Use database method if `.env` file doesn't work

7. **Groq API errors**: 
   - Verify your Groq API key is valid
   - Check you haven't exceeded rate limits
   - Ensure internet connection is stable

8. **ElevenLabs TTS errors**: 
   - Verify your ElevenLabs API key
   - Check character usage limits
   - Server falls back to pyttsx3 if ElevenLabs fails

9. **Hugging Face STT errors**: 
   - Verify your Hugging Face API key
   - Check model availability
   - Ensure audio format is supported

### Admin Access Issues:

10. **"Invalid admin API key" error**: 
    - Use exactly: `guni-admin-demo-key`
    - Include in request header: `x-admin-api-key`
    - For production, set custom `ADMIN_API_KEY` environment variable

### Database Issues:

11. **Database connection errors**: 
    - Server automatically creates SQLite database
    - Check file permissions in server directory
    - Database file: `voice_assistant_enhanced.db`

## Files Included

- `setup_and_run_server.bat` - Windows setup script
- `setup_and_run_server.sh` - Linux/Mac setup script  
- `requirements.txt` - Python dependencies list
- `README_SERVER_SETUP.md` - This documentation

Place your `server.py` file alongside these files and run the appropriate setup script for your operating system.
