from dotenv import load_dotenv
from google import genai
import os

# Load environment variables
load_dotenv()

# Get API key from .env
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY not found in .env file")

# Create Gemini client
client = genai.Client(api_key=api_key)

try:
    print("Available Gemini Models:\n")

    for model in client.models.list():
        if "gemini" in model.name.lower():
            print(model.name)

except Exception as e:
    print(f"Error: {e}")