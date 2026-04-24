from google import genai
from google.genai import types
import json

class EnrichmentClient:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def run(self, prompt, model):
        response = self.client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)