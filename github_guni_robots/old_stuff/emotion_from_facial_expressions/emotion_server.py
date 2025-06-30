from fastapi import FastAPI, UploadFile, File
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.image import img_to_array
import numpy as np
import cv2

app = FastAPI()
model = load_model("models/mini_xception.h5", compile=False)
class_labels = {0: "Angry", 1: "Fear", 2: "Happy", 3: "Neutral", 4: "Sad", 5: "Surprise"}
@app.get("/")
async def root():
    return {"message": "Welcome to the Facial Emotion Detection API"}
@app.post("/emotion")
async def detect_emotion(file: UploadFile = File(...)):
    contents = await file.read()
    npimg = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(npimg, cv2.IMREAD_GRAYSCALE)
    img = cv2.resize(img, (64, 64))  # Match model input size
    img = img.astype("float32") / 255.0
    img = np.expand_dims(img, axis=-1)  # Shape: (64, 64, 1)
    img = np.expand_dims(img, axis=0)   # Shape: (1, 64, 64, 1)

    preds = model.predict(img)[0]
    label = class_labels[np.argmax(preds)]
    return {"emotion": label}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)