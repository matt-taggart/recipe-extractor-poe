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
        self.initial_message = """
        Hi there! I'm Recipe Extractor bot. I can help you extract recipe details from a given URL.
        Just send me a URL and I'll do my best to provide a clean, organized Markdown format of the recipe.
        """
        self.last_url: Optional[str] = None
        self.last_recipe_text: Optional[str] = None
        self.initial_message_sent = False

    async def get_response(self, request: fp.QueryRequest) -> AsyncIterable[fp.PartialResponse]:
        if not self.initial_message_sent:
            self.initial_message_sent = True

        user_input = get_latest_user_input(request.query)
        
        # Define system message and instructions
        system_message = """
        ## Context: You are Recipe Extractor bot, a helpful AI assistant.
        
        ### Instructions
        
        The recipe name, ingredients, instructions, and modifications should be returned as Markdown separated into three sections (four if returning a modification):
        
        1. Recipe name
        2. Ingredients
        3. Instructions
        4. Modifications (If applicable)
        """
        
        # Check if the input contains a URL
        url_match = re.search(r'(https?://[^\s]+)', user_input)
        if url_match:
            url = url_match.group(0)
            self.last_url = url
            extracted_text = fetch_and_extract_text_from_url(url)
            if not extracted_text:
                yield fp.PartialResponse(text="This URL doesn't look like it's valid. Can you please try again?")
                return
            response_text = f"{system_message}\n{extracted_text}"
            self.last_recipe_text = extracted_text
            yield fp.PartialResponse(text=response_text)
        else:
            if self.last_recipe_text:
                # If there's a previously stored recipe, assume this is a modification request
                response_text = f"{system_message}\nRecipe: {self.last_recipe_text}\nModification: {user_input}"
                yield fp.PartialResponse(text=response_text)
            else:
                # If no URL has been provided yet and no last recipe is stored, prompt the user to enter a URL
                yield fp.PartialResponse(text="Please provide a URL to extract a recipe from.")

    async def get_settings(self, setting: fp.SettingsRequest) -> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies={"GPT-4-128k": 1},
            enable_multi_bot_chat_prompting=True,
            allow_attachments=True,
            enable_image_comprehension=True,
            enforce_author_role_alternation=True  # Optional, based on your needs
        )


if __name__ == "__main__":
    fp.run(RecipeExtractorBot(), access_key=os.environ["POE_API_KEY"])
