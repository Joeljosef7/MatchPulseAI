import requests

API_KEY = "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"

response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ],
    },
    timeout=30,
)

print(response.status_code)
print(response.text)
