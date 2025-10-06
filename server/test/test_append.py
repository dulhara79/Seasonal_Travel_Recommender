import requests
import os

API_BASE = os.environ.get('API_BASE', 'http://localhost:8000/api')
TOKEN = os.environ.get('TEST_TOKEN')  # set to a valid JWT for authenticated endpoints

headers = {
    'Content-Type': 'application/json',
}
if TOKEN:
    headers['Authorization'] = f'Bearer {TOKEN}'

payload = {
    "conversation_id": "REPLACE_WITH_VALID_ID",
    "message": {
        "role": "user",
        "text": "Hello from test script",
        "metadata": {},
        "timestamp": "2025-10-02T12:00:00Z"
    }
}

resp = requests.post(f"{API_BASE}/conversations/append", json=payload, headers=headers)
print(resp.status_code)
print(resp.text)
