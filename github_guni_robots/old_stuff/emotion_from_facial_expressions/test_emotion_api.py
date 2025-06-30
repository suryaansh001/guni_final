import requests

# Replace this with the path to your test image
image_path = "test.png"

# Endpoint URL
url = "http://localhost:8000/emotion"

# Open the image file in binary mode
with open(image_path, "rb") as image_file:
    files = {"file": (image_path, image_file, "image/jpeg")}
    response = requests.post(url, files=files)

# Output the response
print("Status Code:", response.status_code)
print("Response JSON:", response.json())
