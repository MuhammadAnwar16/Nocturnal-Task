import os
import json
import time
import PIL.Image
from google import genai

def extract_register_data(image_paths: list) -> list:
    """Processes images of the register and returns a combined list of JSON objects."""
    client = genai.Client()
    
    prompt = """
    Extract the table from this goods receiving register into a JSON array.
    The JSON should have these exact keys: "GRN" (number), "Qty" (number).
    RULES:
    1. If a quantity is crossed out, use the new corrected number.
    2. If a field is completely obscured by an ink blot or unreadable, return null for that field. Do not guess.
    3. Output ONLY the raw JSON array. Do not include markdown tags like ```json.
    """
    
    combined_data = []
    for path in image_paths:
        img = PIL.Image.open(path)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-3.8-flash', 
                    contents=[img, prompt]
                )
                
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                page_data = json.loads(clean_text)
                combined_data.extend(page_data)
                
                break
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise Exception(f"Failed to process {path} after {max_retries} attempts. Last error: {e}")
        
    return combined_data