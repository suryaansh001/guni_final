#!/bin/bash

# Robot Face API Server Setup Script for Linux/Mac
# This script automatically sets up the Python environment and runs the server

echo "🤖 GUNI Robot API Server Setup"
echo "================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Check if server.py exists
if [ ! -f "server.py" ]; then
    echo "❌ server.py not found in current directory."
    echo "Please place server.py in the same folder as this script."
    exit 1
fi

echo "✅ Python 3 found"
echo "✅ server.py found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Failed to create virtual environment"
        exit 1
    fi
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
python -m pip install --upgrade pip

# Install requirements
echo "📦 Installing dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    echo "⚠️ requirements.txt not found, installing basic dependencies..."
    pip install fastapi uvicorn python-multipart python-dotenv groq elevenlabs pyttsx3 requests paho-mqtt pydantic
fi

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

echo "✅ Dependencies installed successfully"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️ No .env file found. Creating template..."
    cat > .env << EOL
# AI Service API Keys (Required)
GROQ_API_KEY=your_groq_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
HUGGINGFACE_API_KEY=your_huggingface_api_key_here

# Admin Access
ADMIN_API_KEY=guni-admin-demo-key

# MQTT Configuration (Optional)
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
EOL
    echo "📝 Template .env file created. Please edit it with your API keys."
    echo "📖 You can also manage API keys through the web interface using admin key: guni-admin-demo-key"
fi

echo ""
echo "🚀 Starting GUNI Robot API Server..."
echo "📡 Server will be available at:"
echo "   - Local: http://localhost:8001"
echo "   - Network: http://$(hostname -I | awk '{print $1}'):8001"
echo ""
echo "🛑 Press Ctrl+C to stop the server"
echo "================================"

# Run the server
python server.py
