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
    def __init__(self):
        super().__init__()

        self.initial_message = """
        Hi there! I'm Recipe Extractor bot. I can help you extract recipe details from a given URL.
        Just send me a URL and I'll do my best to provide a clean, organized Markdown format of the recipe.
        """
        self.last_url: Optional[str] = None
        self.last_recipe_text: Optional[str] = None
        self.initial_message_sent = False
        self.system_message = """
        ## Internal Context: You are Recipe Extractor bot, a helpful AI assistant.
        
        ### Instructions
        
        The recipe name, ingredients, instructions, and modifications should be returned as Markdown separated into three sections (four if returning a modification):
        
        1. Recipe name
        2. Ingredients
        3. Instructions
        4. Modifications (If applicable)
        """

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        # Check if a system message exists
        sysmsgexists = False
        for protmsg in request.query:
            if protmsg.role == "system":
                sysmsgexists = True

        # If no system message exists, add one
        if not sysmsgexists:
            request.query.insert(0, fp.ProtocolMessage(role="system", content=self.system_message))

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
            prompt = f"Extracted recipe text:\n\n{extracted_text}\n\n{self.system_message}"
            gpt4_request = fp.QueryRequest(
                query=[
                    fp.ProtocolMessage(role="system", content=self.system_message),
                    fp.ProtocolMessage(role="user", content=prompt)
                ],
                access_key=request.access_key,
                version="1.0",  # Example version, replace with the actual version
                type="query",  # Example type, replace with the correct type
                user_id=str(request.user_id),  # Ensure user_id is a string
                conversation_id=str(request.conversation_id),  # Ensure conversation_id is a string
                message_id=str(request.message_id) # Generate a unique message ID
            )

            async for msg in fp.stream_request(gpt4_request, "GPT-3.5-Turbo", request.access_key):
                yield msg
        else:
            if self.last_recipe_text:
                modification_response = f"Recipe: {self.last_recipe_text}\nModification: {user_input}"

                # Prepare the message to send to GPT-4 including the modification
                prompt = f"Extracted recipe text:\n\n{self.last_recipe_text}\n\nUser's modification request:\n\n{user_input}\n\n{self.system_message}"
                gpt4_request = fp.QueryRequest(
                    query=[
                        fp.ProtocolMessage(role="system", content=self.system_message),
                        fp.ProtocolMessage(role="user", content=prompt)
                    ],
                    access_key=request.access_key,
                    version="1.0",  # Example version, replace with the actual version
                    type="query",  # Example type, replace with the correct type
                    user_id=str(request.user_id),  # Ensure user_id is a string
                    conversation_id=str(request.conversation_id),  # Ensure conversation_id is a string
                    message_id=str(request.message_id)
                )

                async for msg in fp.stream_request(gpt4_request, "GPT-3.5-Turbo", request.access_key):
                    yield msg
            else:
                # If no URL has been provided yet and no last recipe is stored, prompt the user to enter a URL
                yield fp.PartialResponse(text="Please provide a URL to extract a recipe from.")

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            introduction_message="Hi there! I'm Recipe Extractor bot. I can help you extract recipe details from a given URL. Just send me a URL and I'll do my best to provide a clean, organized Markdown format of the recipe.",
            server_bot_dependencies={"GPT-3.5-Turbo": 1}, 
            enable_multi_bot_chat_prompting=True,
            allow_attachments=True,
            enable_image_comprehension=True,
        )

recipe_extractor_bot = RecipeExtractorBot()

if __name__ == "__main__":
    fp.run(recipe_extractor_bot, access_key=os.environ["POE_API_KEY"])
