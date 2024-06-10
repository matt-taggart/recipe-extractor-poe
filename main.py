from __future__ import annotations

import os
from typing import AsyncIterable, Optional
import fastapi_poe as fp
import requests
from bs4 import BeautifulSoup
import re

from dotenv import load_dotenv
load_dotenv()

def is_valid_url(url: str) -> bool:
    # Regular expression to validate URLs
    regex = re.compile(
        r'^(https?://)?'  # http:// or https://
        r'(([A-Za-z0-9-]+\.)+[A-Za-z]{2,6})'  # domain
        r'(:[0-9]{1,5})?'  # optional port
        r'(/.*)?$'  # path
    )
    return re.match(regex, url) is not None

def fetch_and_extract_text_from_url(url: str) -> str:
    if not is_valid_url(url):
        return ""
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator="\n")
        return text.strip()
    except requests.RequestException as e:
        return f"Error fetching the URL: {e}"
    except Exception as e:
        return f"Error parsing the content: {e}"

def get_latest_user_input(messages):
    latest = ""

    for message in reversed(messages):
        if message.role == "user":
            latest = message.content
            break

    return latest

class RecipeExtractorBot(fp.PoeBot):

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        user_input = get_latest_user_input(request.query)

        # Check if the input contains a URL
        url_match = re.search(r'(https?://[^\s]+)', user_input)
        if url_match:
            url = url_match.group(0)
            self.last_url = url
            extracted_text = fetch_and_extract_text_from_url(url)
            if not extracted_text:
                yield fp.PartialResponse(text="This URL doesn't look like it's valid. Can you please try again?")
                return
            self.last_recipe_text = extracted_text

            # Prepare the message to send to GPT-4
            prompt = f"Extracted recipe text:\n\n{extracted_text}\n\n"
            gpt4_request = fp.QueryRequest(
                query=[
                    fp.ProtocolMessage(role="user", content=prompt)
                ],
                access_key=request.access_key,
                version="1.0",  # Example version, replace with the actual version
                type="query",  # Example type, replace with the correct type
                user_id=str(request.user_id),  # Ensure user_id is a string
                conversation_id=str(request.conversation_id),  # Ensure conversation_id is a string
                message_id=str(request.message_id) # Generate a unique message ID
            )

            async for msg in fp.stream_request(gpt4_request, "Claude-instant", request.access_key):
                 print("Received message:", msg)
                 yield msg.model_copy(update={"text": msg.text })
        else:
            yield fp.PartialResponse(text="Please provide a URL to extract a recipe from.")

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"Claude-instant": 1}
        )

recipe_extractor_bot = RecipeExtractorBot()

if __name__ == "__main__":
    fp.run(recipe_extractor_bot, access_key=os.environ["POE_API_KEY"])
