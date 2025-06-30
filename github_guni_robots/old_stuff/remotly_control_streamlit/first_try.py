import requests
import streamlit as st

st.title("Servo Control Panel")

if st.button("Send Move Command"):
    response = requests.post("http://0.0.0.0:8000//send-command")
    st.write(response.json())
