import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=key)

# Create a dummy tiny webm audio file bytes
audio_bytes = b"just some dummy bytes"

try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            "Transcribe this",
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/webm")
        ]
    )
    print("Success:", response.text)
except Exception as e:
    print("Error:", e)
