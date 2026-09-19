import os
from groq import Groq

def call_groq(system: str, user: str, model: str) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Please set GROQ_API_KEY.")
    
    if not model:
        raise ValueError("A valid model ID must be provided. No hardcoded fallbacks are allowed.")

    client = Groq(api_key=api_key)
    
    # Strictly call the requested model without silent fallbacks
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ]
    )
    return response.choices[0].message.content
