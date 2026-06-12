import requests

url = "http://127.0.0.1:8000/api/transcribe"
files = {'file': ('dummy.webm', b'dummy audio bytes', 'audio/webm')}

try:
    response = requests.post(url, files=files)
    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())
except Exception as e:
    print("Error:", e)
