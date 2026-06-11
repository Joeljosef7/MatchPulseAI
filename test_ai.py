import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = "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"

prompt = """
You are MatchPulse AI.

Create a football match preview for England vs France.

Rules:
- Maximum 80 words.
- Exactly 1 short paragraph.
- No headings.
- No bullet points.
- No introductions.
- No conclusions.
- Football only.
"""

response = requests.post(
    "https://api.groq.com/openai/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    },
    json={
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 100,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    },
    timeout=30
)

print("Status:", response.status_code)

if response.status_code == 200:
    data = response.json()
    print(data["choices"][0]["message"]["content"])
else:
    print(response.text)
