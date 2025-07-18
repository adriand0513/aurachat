import openai
import os
from dotenv import load_dotenv

load_dotenv()  # Only needed if you're using .env

openai.api_key = os.getenv("OPENAI_API_KEY")  # or hardcode it here

try:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say hello!"}
        ]
    )
    print("✅ API key works! Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print("❌ API key error:")
    print(e)
