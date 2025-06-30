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

Make sure to set up your API keys as environment variables or in a `.env` file:

```
GROQ_API_KEY=your_groq_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
HUGGINGFACE_API_KEY=your_huggingface_key_here
```

## Server Access

Once running, the server will be available at:
- **Local**: http://localhost:8001
- **Network**: http://YOUR_IP_ADDRESS:8001

## Stopping the Server

Press `Ctrl+C` in the terminal to stop the server.

## Troubleshooting

1. **Python not found**: Make sure Python is installed and added to PATH
2. **Permission denied**: On Linux/Mac, make sure the script is executable: `chmod +x setup_and_run_server.sh`
3. **Dependencies fail**: Try updating pip: `python -m pip install --upgrade pip`
4. **Server doesn't start**: Check that `server.py` exists in the same folder
5. **Port already in use**: Stop any other processes using port 8001

## Files Included

- `setup_and_run_server.bat` - Windows setup script
- `setup_and_run_server.sh` - Linux/Mac setup script  
- `requirements.txt` - Python dependencies list
- `README_SERVER_SETUP.md` - This documentation

Place your `server.py` file alongside these files and run the appropriate setup script for your operating system.
