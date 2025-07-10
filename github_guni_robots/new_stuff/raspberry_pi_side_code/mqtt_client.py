import paho.mqtt.client as mqtt
import subprocess
import json
import time
import os
import requests

# MQTT Configuration (should match the FastAPI server)
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_COMMAND = "pi-controller/commands"
MQTT_TOPIC_RESPONSE = "pi-controller/responses"
MQTT_TOPIC_STATUS = "pi-controller/status"

# Allowed scripts directory and list
ALLOWED_SCRIPTS = {
    "walk_forward.py",
    "stop.py",
    "left_hand_up.py",
    "right_hand_up.py",
    "hello.py"
}

SCRIPT_PATH = "/home/pi/client_side_rasp/scripts"  # Update to the actual directory containing your scripts

def execute_script(script_name):
    """Run the allowed Python script and capture output"""
    full_path = os.path.join(SCRIPT_PATH, script_name)
    if not os.path.exists(full_path):
        return {"status": "error", "error": f"Script {script_name} not found"}

    try:
        result = subprocess.run(
            ["python3", full_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.stderr else None
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "error": "Script execution timed out"}

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT broker")
        client.subscribe(MQTT_TOPIC_COMMAND)
        print(f"📡 Subscribed to topic: {MQTT_TOPIC_COMMAND}")
        # Periodic status updates
        def ping_status():
            while True:
                status_payload = json.dumps({"status": "online", "timestamp": time.time()})
                client.publish(MQTT_TOPIC_STATUS, status_payload)
                time.sleep(30)
        import threading
        threading.Thread(target=ping_status, daemon=True).start()
    else:
        print(f"❌ MQTT connection failed with code {rc}")

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        command = payload.get("command")
        command_id = payload.get("command_id")

        print(f"📥 Received command: {command} (ID: {command_id})")

        if command.startswith("python3 "):
            script_name = command.split(" ", 1)[1].strip()
            if script_name not in ALLOWED_SCRIPTS:
                print(f"❌ Unauthorized script: {script_name}")
                response = {
                    "command_id": command_id,
                    "status": "unauthorized",
                    "error": f"Script '{script_name}' not allowed"
                }
            else:
                result = execute_script(script_name)
                response = {
                    "command_id": command_id,
                    **result
                }
        else:
            print(f"❌ Invalid command format: {command}")
            response = {
                "command_id": command_id,
                "status": "invalid",
                "error": "Only python3 script execution is supported"
            }

        client.publish(MQTT_TOPIC_RESPONSE, json.dumps(response))
        print(f"📤 Sent response for command ID {command_id}")

    except Exception as e:
        print(f"⚠️ Error processing message: {e}")

def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, 60)
        client.loop_forever()
    except Exception as e:
        print(f"❌ Failed to connect to MQTT broker: {e}")

if __name__ == "__main__":
    main()
