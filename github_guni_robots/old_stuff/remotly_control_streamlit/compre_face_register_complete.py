import streamlit as st
import requests
import json
import base64
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("FASTAPI_URL", "http://localhost:8001")
COMPRE_FACE_URL = os.getenv("COMPRE_FACE_URL", "http://localhost:8000")
COMPRE_FACE_API_KEY = os.getenv("COMPRE_FACE_API_KEY", "6f0a4c1c-18f0-4072-a5fe-59b8bfc433c0")

def encode_image_to_base64(image_path):
    try:
        with open(image_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            mime_type = "image/jpeg" if image_path.lower().endswith(('.jpg', '.jpeg')) else "image/png"
            return f"data:{mime_type};base64,{encoded}"
    except Exception as e:
        st.error(f"Error encoding image: {e}")
        return None

def register_face_with_compreface(subject_name, photo_file):
    try:
        files = {"file": (photo_file.name, photo_file.getvalue(), photo_file.type)}
        headers = {"x-api-key": COMPRE_FACE_API_KEY}
        response = requests.post(
            f"{COMPRE_FACE_URL}/api/v1/recognition/faces/?subject={subject_name}",
            headers=headers,
            files=files
        )
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    st.set_page_config(page_title="Voice Assistant Profile Upload", page_icon="🤖")
    st.title("Voice Assistant Profile Upload")
    st.write("Upload your profile information and face photo to personalize your assistant.")

    with st.form("profile_upload_form"):
        name = st.text_input("Your Name", placeholder="Enter your name")
        photo_file = st.file_uploader("Upload Face Photo (JPG/PNG)", type=["jpg", "jpeg", "png"])
        hobbies = st.text_input("Hobbies (comma-separated)", placeholder="e.g., coding, gaming")
        background = st.text_area("Background", placeholder="e.g., Computer Science student")
        preferences = st.text_area("Preferences", placeholder="e.g., Likes concise responses")
        submitted = st.form_submit_button("Submit Profile")

        if submitted:
            if not name or not photo_file:
                st.error("Name and face photo are required.")
            else:
                with open("temp_photo", "wb") as f:
                    f.write(photo_file.getvalue())
                face_photo = encode_image_to_base64("temp_photo")
                os.remove("temp_photo")

                # Step 1: Register face with CompreFace
                st.info("Registering your face...")
                compreface_result = register_face_with_compreface(name, photo_file)

                if "error" in compreface_result:
                    st.error(f"Face registration failed: {compreface_result['error']}")
                    return
                elif compreface_result.get("image_id"):
                    st.success(f"Face registered successfully with ID: {compreface_result['image_id']}")
                else:
                    st.warning("Unexpected response from CompreFace:")
                    st.json(compreface_result)

                # Step 2: Prepare and upload profile JSON
                profile_data = {
                    "name": name.strip(),
                    "face_photo": face_photo,
                    "info": {
                        "hobbies": [h.strip() for h in hobbies.split(",")] if hobbies else [],
                        "background": background.strip() if background else "",
                        "preferences": preferences.strip() if preferences else ""
                    }
                }

                temp_json_path = "temp_profile.json"
                with open(temp_json_path, "w") as f:
                    json.dump(profile_data, f, indent=2)

                try:
                    with open(temp_json_path, "rb") as f:
                        files = {"file": ("profile.json", f, "application/json")}
                        response = requests.post(f"{API_URL}/upload-profile", files=files)

                    os.remove(temp_json_path)

                    if response.status_code == 200:
                        st.success(response.json().get("message"))
                    else:
                        st.error(f"Upload failed: {response.json().get('detail')}")
                except Exception as e:
                    st.error(f"Error uploading profile: {e}")
                    if os.path.exists(temp_json_path):
                        os.remove(temp_json_path)

if __name__ == "__main__":
    main()
