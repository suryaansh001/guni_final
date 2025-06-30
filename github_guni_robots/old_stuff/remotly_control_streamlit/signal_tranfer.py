# cloud_fastapi_server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess

app = FastAPI()

# Allow CORS for all origins (adjust in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.get("/")
def root():
    return {"message": "Cloud FastAPI is live"}

@app.post("/send-command")
def send_command():
    try:
        result = subprocess.run([
            "ssh", "pi@192.168.23.225",  # Replace with your Pi's IP
            "python3 /home/pi/send_ard_pi.py"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            return {"status": "success", "output": result.stdout}
        else:
            return {"status": "error", "error": result.stderr}
    except Exception as e:
        return {"status": "failed", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)