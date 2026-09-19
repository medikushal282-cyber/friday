import os
from dotenv import load_dotenv
import requests
import json

load_dotenv()
api_key = os.environ.get("GROQ_API_KEY")
headers = {"Authorization": f"Bearer {api_key}"}
response = requests.get("https://api.groq.com/openai/v1/models", headers=headers)
print(json.dumps(response.json(), indent=2))
