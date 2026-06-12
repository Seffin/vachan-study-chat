import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from api.index import app
from fastapi.testclient import TestClient

client = TestClient(app)

response = client.post("/api/transcribe", files={"file": ("test.webm", b"dummy audio data", "audio/webm")})
print("Response:", response.status_code, response.text)
